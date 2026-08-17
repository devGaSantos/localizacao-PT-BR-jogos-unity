using System.Text.Encodings.Web;
using System.Text.Json;
using AssetsTools.NET;
using AssetsTools.NET.Extra;

internal static class JsonOptions
{
    public static readonly JsonSerializerOptions Pretty = new()
    {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
        WriteIndented = true
    };
}

internal enum ProcessingMode
{
    Scan,
    Build,
    Verify
}

internal sealed record PipelinePaths(
    string GameRoot,
    string GameData,
    string Bundles,
    string Managed,
    string Project,
    string ClassData,
    string Output,
    string ReportPath)
{
    public static PipelinePaths Create(string gameRoot, string project, string classData, string output)
    {
        gameRoot = Path.GetFullPath(gameRoot);
        project = Path.GetFullPath(project);
        output = Path.GetFullPath(output);
        var data = Path.Combine(gameRoot, "LWIW_Data");
        return new PipelinePaths(
            gameRoot,
            data,
            Path.Combine(data, "StreamingAssets", "aa", "StandaloneWindows64"),
            Path.Combine(data, "Managed"),
            project,
            Path.GetFullPath(classData),
            output,
            Path.Combine(project, "relatorios", "asset_pipeline_automatico.json")
        );
    }
}

internal sealed record MissingText(string Asset, string Source, int Count);

internal sealed class FlowReport
{
    public required string Flow { get; init; }
    public int TargetAssets { get; set; }
    public int Occurrences { get; set; }
    public int Translated { get; set; }
    public int Empty { get; set; }
    public List<string> Assets { get; } = [];
    public List<MissingText> Missing { get; } = [];
    public int MissingUnique => Missing.Count;
}

internal sealed class PipelineReport
{
    public required DateTimeOffset GeneratedAt { get; init; }
    public required string Mode { get; init; }
    public required string UnityVersion { get; set; }
    public required List<FlowReport> Flows { get; init; }
    public required List<string> Outputs { get; init; }
    public bool Ready => Flows.All(flow => flow.MissingUnique == 0);
}

internal sealed class TranslationMemory
{
    private readonly IReadOnlyDictionary<string, string> entries;
    private readonly bool dumpEscaped;
    private readonly HashSet<string> translations;

    private TranslationMemory(IReadOnlyDictionary<string, string> entries, bool dumpEscaped)
    {
        this.entries = entries;
        this.dumpEscaped = dumpEscaped;
        translations = entries.Values
            .Where(value => !string.IsNullOrWhiteSpace(value))
            .Select(value => dumpEscaped ? UnityDumpText.Unescape(value) : value)
            .ToHashSet(StringComparer.Ordinal);
    }

    public static TranslationMemory Load(string path, bool dumpEscaped = false)
    {
        var entries = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(path))
            ?? throw new InvalidDataException($"Memoria JSON invalida: {path}");
        return new TranslationMemory(entries, dumpEscaped);
    }

    public bool TryTranslate(string source, out string translation)
    {
        var escaped = UnityDumpText.Escape(source);
        var escapedControls = UnityDumpText.EscapeControls(source);
        foreach (var key in new[]
                 {
                     source,
                     source.Trim(),
                     escapedControls,
                     escapedControls.Trim(),
                     escaped,
                     escaped.Trim()
                 }.Distinct())
        {
            if (!entries.TryGetValue(key, out var value) || string.IsNullOrWhiteSpace(value))
                continue;

            translation = dumpEscaped ? UnityDumpText.Unescape(value) : value;
            return true;
        }

        translation = string.Empty;
        return false;
    }

    public bool IsKnownTranslation(string value) => translations.Contains(value);
}

internal static class UnityDumpText
{
    public static string EscapeControls(string value) => value
        .Replace("\r", "\\r", StringComparison.Ordinal)
        .Replace("\n", "\\n", StringComparison.Ordinal)
        .Replace("\t", "\\t", StringComparison.Ordinal);

    public static string Escape(string value) => value
        .Replace("\\", "\\\\", StringComparison.Ordinal)
        .Replace("\"", "\\\"", StringComparison.Ordinal)
        .Replace("\r", "\\r", StringComparison.Ordinal)
        .Replace("\n", "\\n", StringComparison.Ordinal)
        .Replace("\t", "\\t", StringComparison.Ordinal);

    public static string Unescape(string value)
    {
        var result = new System.Text.StringBuilder(value.Length);
        for (var index = 0; index < value.Length; index++)
        {
            if (value[index] != '\\' || index + 1 >= value.Length)
            {
                result.Append(value[index]);
                continue;
            }

            var next = value[++index];
            result.Append(next switch
            {
                'n' => '\n',
                'r' => '\r',
                't' => '\t',
                '\\' => '\\',
                '"' => '"',
                _ => $"\\{next}"
            });
        }
        return result.ToString();
    }
}

internal sealed class AssetTranslationPipeline
{
    private const string GeneralBundleName = "localization-string-tables-english(en)_assets_all.bundle";
    private const string DialogueBundleName = "dialoguedb_assets_all.bundle";
    private const string MissionBundleName = "defaultlocalgroup_assets_all.bundle";
    private const string ResourcesName = "resources.assets";

    private readonly PipelinePaths paths;
    private string unityVersion = string.Empty;

    public AssetTranslationPipeline(PipelinePaths paths)
    {
        this.paths = paths;
    }

    public PipelineReport Run(ProcessingMode mode)
    {
        ValidateInputs();
        if (mode == ProcessingMode.Build)
        {
            if (Directory.Exists(paths.Output))
                Directory.Delete(paths.Output, recursive: true);
            Directory.CreateDirectory(paths.Output);
        }

        var reports = new List<FlowReport>();
        var outputs = new List<string>();
        var dependencyLinks = mode == ProcessingMode.Verify ? PrepareResourceDependencyLinks() : [];

        try
        {

        var general = ProcessBundle(
            GeneralBundleName,
            TranslationMemory.Load(Path.Combine(paths.Project, "memoria_revisado.json")),
            PatchGeneral,
            expectedTargets: 25,
            mode);
        reports.Add(general.Report);
        AddOutput(general.Output, outputs);

        var dialogue = ProcessBundle(
            DialogueBundleName,
            TranslationMemory.Load(Path.Combine(paths.Project, "dialogos", "memory", "memoria.json"), dumpEscaped: true),
            PatchDialogue,
            expectedTargets: 1,
            mode);
        reports.Add(dialogue.Report);
        AddOutput(dialogue.Output, outputs);

        var missionBundle = ProcessBundle(
            MissionBundleName,
            TranslationMemory.Load(Path.Combine(Directory.GetParent(paths.Project)!.FullName, "missoes", "memoria_missoes.json")),
            PatchMissionTables,
            expectedTargets: 10,
            mode,
            excludeAssetName: "base");
        reports.Add(missionBundle.Report);
        AddOutput(missionBundle.Output, outputs);

        var resources = ProcessResources(
            TranslationMemory.Load(Path.Combine(Directory.GetParent(paths.Project)!.FullName, "missoes", "memoria_missoes.json")),
            mode);
        reports.Add(resources.Report);
        AddOutput(resources.Output, outputs);

        var report = new PipelineReport
        {
            GeneratedAt = DateTimeOffset.UtcNow,
            Mode = mode.ToString().ToLowerInvariant(),
            UnityVersion = unityVersion,
            Flows = reports,
            Outputs = outputs
        };

        if (mode == ProcessingMode.Build && !report.Ready)
        {
            Directory.Delete(paths.Output, recursive: true);
            report.Outputs.Clear();
            throw new InvalidOperationException("Build cancelado: existem traducoes ausentes. Rode scan e atualize as memorias.");
        }

            return report;
        }
        finally
        {
            foreach (var link in dependencyLinks)
                File.Delete(link);
        }
    }

    private (FlowReport Report, string? Output) ProcessBundle(
        string bundleName,
        TranslationMemory memory,
        Func<AssetTypeValueField, string, TranslationMemory, ProcessingMode, FlowReport, bool> patcher,
        int expectedTargets,
        ProcessingMode mode,
        string? excludeAssetName = null)
    {
        var source = Path.Combine(mode == ProcessingMode.Verify ? paths.Output : paths.Bundles, bundleName);
        var manager = CreateManager();
        var bundle = manager.LoadBundleFile(source, true);
        var assets = manager.LoadAssetsFileFromBundle(bundle, 0, false);
        LoadTypes(manager, assets);

        var report = new FlowReport { Flow = Path.GetFileNameWithoutExtension(bundleName) };
        foreach (var info in assets.file.GetAssetsOfType(AssetClassID.MonoBehaviour))
        {
            AssetTypeValueField root;
            try
            {
                root = manager.GetBaseField(assets, info);
            }
            catch
            {
                continue;
            }
            var nameField = root["m_Name"];
            var name = nameField.IsDummy ? string.Empty : nameField.AsString;
            if (excludeAssetName is not null && name.Equals(excludeAssetName, StringComparison.OrdinalIgnoreCase))
                continue;
            if (!patcher(root, name, memory, mode, report))
                continue;

            report.TargetAssets++;
            report.Assets.Add(name);
            if (mode == ProcessingMode.Build)
                info.SetNewData(root);
        }

        AssertCount(report, expectedTargets);
        var output = mode == ProcessingMode.Build ? Path.Combine(paths.Output, bundleName) : null;
        if (mode == ProcessingMode.Build)
            WriteBundle(bundle.file, assets.file, output!);
        return (report, output);
    }

    private (FlowReport Report, string? Output) ProcessResources(TranslationMemory memory, ProcessingMode mode)
    {
        var source = Path.Combine(mode == ProcessingMode.Verify ? paths.Output : paths.GameData, ResourcesName);
        var manager = CreateManager();
        var assets = manager.LoadAssetsFile(source, true);
        LoadTypes(manager, assets);
        var report = new FlowReport { Flow = "missoes_resources_assets" };

        foreach (var info in assets.file.GetAssetsOfType(AssetClassID.MonoBehaviour))
        {
            AssetTypeValueField root;
            try
            {
                root = manager.GetBaseField(assets, info);
            }
            catch
            {
                continue;
            }
            var nameField = root["m_Name"];
            var name = nameField.IsDummy ? string.Empty : nameField.AsString;
            if (name.Equals("base", StringComparison.OrdinalIgnoreCase))
                continue;
            if (!PatchMissionTables(root, name, memory, mode, report))
                continue;

            report.TargetAssets++;
            report.Assets.Add(name);
            if (mode == ProcessingMode.Build)
                info.SetNewData(root);
        }

        AssertCount(report, 18);
        var output = mode == ProcessingMode.Build ? Path.Combine(paths.Output, ResourcesName) : null;
        if (mode == ProcessingMode.Build)
        {
            using (var writer = new AssetsFileWriter(output!))
                assets.file.Write(writer);
        }
        manager.UnloadAll();
        return (report, output);
    }

    private AssetsManager CreateManager()
    {
        var manager = new AssetsManager();
        manager.LoadClassPackage(paths.ClassData);
        manager.MonoTempGenerator = new MonoCecilTempGenerator(paths.Managed);
        return manager;
    }

    private void LoadTypes(AssetsManager manager, AssetsFileInstance assets)
    {
        manager.LoadClassDatabaseFromPackage(assets.file.Metadata.UnityVersion);
        if (string.IsNullOrEmpty(unityVersion))
            unityVersion = assets.file.Metadata.UnityVersion;
        else if (!unityVersion.Equals(assets.file.Metadata.UnityVersion, StringComparison.Ordinal))
            throw new InvalidDataException($"Versoes Unity divergentes: {unityVersion} e {assets.file.Metadata.UnityVersion}.");
    }

    private static bool PatchGeneral(
        AssetTypeValueField root,
        string assetName,
        TranslationMemory memory,
        ProcessingMode mode,
        FlowReport report)
    {
        var tableData = root["m_TableData"];
        if (tableData.IsDummy)
            return false;

        foreach (var field in Descendants(root).Where(field => field.FieldName == "m_Localized"))
            Apply(field, assetName, memory, mode, report);
        return true;
    }

    private static bool PatchDialogue(
        AssetTypeValueField root,
        string assetName,
        TranslationMemory memory,
        ProcessingMode mode,
        FlowReport report)
    {
        if (!assetName.Equals("DialogueDB_en", StringComparison.Ordinal))
            return false;

        foreach (var field in Descendants(root))
        {
            var title = field["title"];
            var value = field["value"];
            if (title.IsDummy || value.IsDummy || title.AsString != "en")
                continue;
            Apply(value, assetName, memory, mode, report);
        }
        return true;
    }

    private static bool PatchMissionTables(
        AssetTypeValueField root,
        string assetName,
        TranslationMemory memory,
        ProcessingMode mode,
        FlowReport report)
    {
        var languageKeys = ArrayChildren(root["m_languageKeys"]);
        var languageValues = ArrayChildren(root["m_languageValues"]);
        var fieldValues = ArrayChildren(root["m_fieldValues"]);
        if (languageKeys.Count == 0 || languageValues.Count == 0 || fieldValues.Count == 0)
            return false;

        var englishIndex = languageKeys.FindIndex(field => field.AsString == "en");
        if (englishIndex < 0 || englishIndex >= languageValues.Count)
            throw new InvalidDataException($"Idioma en nao encontrado na tabela {assetName}.");
        var englishId = languageValues[englishIndex].AsInt;

        foreach (var row in fieldValues)
        {
            var keys = ArrayChildren(row["m_keys"]);
            var values = ArrayChildren(row["m_values"]);
            var count = Math.Min(keys.Count, values.Count);
            for (var index = 0; index < count; index++)
            {
                if (keys[index].AsInt == englishId)
                    Apply(values[index], assetName, memory, mode, report);
            }
        }
        return true;
    }

    private static void Apply(
        AssetTypeValueField field,
        string assetName,
        TranslationMemory memory,
        ProcessingMode mode,
        FlowReport report)
    {
        report.Occurrences++;
        var source = field.AsString;
        if (string.IsNullOrWhiteSpace(source))
        {
            report.Empty++;
            return;
        }

        if (mode == ProcessingMode.Verify)
        {
            if (memory.IsKnownTranslation(source))
            {
                report.Translated++;
                return;
            }
        }
        else if (memory.TryTranslate(source, out var translation))
        {
            report.Translated++;
            if (mode == ProcessingMode.Build)
                field.AsString = translation;
            return;
        }

        var existing = report.Missing.FindIndex(item => item.Asset == assetName && item.Source == source);
        if (existing >= 0)
        {
            var item = report.Missing[existing];
            report.Missing[existing] = item with { Count = item.Count + 1 };
        }
        else
        {
            report.Missing.Add(new MissingText(assetName, source, 1));
        }
    }

    private static IEnumerable<AssetTypeValueField> Descendants(AssetTypeValueField root)
    {
        yield return root;
        foreach (var child in root.Children)
        foreach (var descendant in Descendants(child))
            yield return descendant;
    }

    private static List<AssetTypeValueField> ArrayChildren(AssetTypeValueField field)
    {
        if (field.IsDummy)
            return [];
        var array = field["Array"];
        return array.IsDummy ? [] : array.Children.ToList();
    }

    private static void WriteBundle(AssetBundleFile bundle, AssetsFile assets, string output)
    {
        var uncompressed = output + ".uncompressed";
        bundle.BlockAndDirInfo.DirectoryInfos[0].SetNewData(assets);
        using (var writer = new AssetsFileWriter(uncompressed))
            bundle.Write(writer);

        var rebuilt = new AssetBundleFile();
        rebuilt.Read(new AssetsFileReader(uncompressed));
        using (var writer = new AssetsFileWriter(output))
            rebuilt.Pack(writer, AssetBundleCompressionType.LZ4);
        rebuilt.Close();
        File.Delete(uncompressed);
    }

    private void ValidateInputs()
    {
        foreach (var path in new[] { paths.GameRoot, paths.GameData, paths.Bundles, paths.Managed, paths.Project })
            if (!Directory.Exists(path))
                throw new DirectoryNotFoundException(path);
        if (!File.Exists(paths.ClassData))
            throw new FileNotFoundException("classdata.tpk nao encontrado.", paths.ClassData);
    }

    private List<string> PrepareResourceDependencyLinks()
    {
        if (!Directory.Exists(paths.Output))
            throw new DirectoryNotFoundException($"Staging nao encontrado: {paths.Output}");

        var stagedResources = Path.Combine(paths.Output, ResourcesName);
        var manager = CreateManager();
        var assets = manager.LoadAssetsFile(stagedResources, false);
        var dependencyNames = assets.file.Metadata.Externals
            .Select(external => Path.GetFileName(external.PathName))
            .Where(name => !string.IsNullOrWhiteSpace(name))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        manager.UnloadAll();

        var links = new List<string>();
        try
        {
            foreach (var name in dependencyNames)
            {
                var source = Path.Combine(paths.GameData, name);
                if (!File.Exists(source))
                {
                    if (name.Equals("unity default resources", StringComparison.OrdinalIgnoreCase) ||
                        name.Equals("unity_builtin_extra", StringComparison.OrdinalIgnoreCase))
                        continue;
                    throw new FileNotFoundException($"Dependencia de resources.assets nao encontrada: {name}", source);
                }
                var destination = Path.Combine(paths.Output, name);
                if (File.Exists(destination))
                    continue;
                File.Copy(source, destination);
                links.Add(destination);
            }
            return links;
        }
        catch
        {
            foreach (var link in links)
                File.Delete(link);
            throw;
        }
    }

    private static void AssertCount(FlowReport report, int expected)
    {
        if (report.TargetAssets != expected)
            throw new InvalidDataException(
                $"{report.Flow}: esperados {expected} assets alvo; encontrados {report.TargetAssets}: " +
                string.Join(", ", report.Assets));
    }

    private static void AddOutput(string? output, List<string> outputs)
    {
        if (output is not null)
            outputs.Add(output);
    }
}
