using System.Text;
using System.Text.Json;
using AssetsTools.NET;
using AssetsTools.NET.Extra;
using Microsoft.VisualBasic.FileIO;

internal enum ProcessingMode
{
    Scan,
    Build,
    Verify
}

internal sealed record PipelinePaths(
    string GameRoot,
    string GameData,
    string Managed,
    string Project,
    string ClassData,
    string Output,
    string Reports,
    string Report,
    string MissingMemory)
{
    public static PipelinePaths Create(string gameRoot, string project, string classData, string output)
    {
        gameRoot = Path.GetFullPath(gameRoot);
        project = Path.GetFullPath(project);
        var reports = Path.Combine(project, "relatorios");
        var gameData = Path.Combine(gameRoot, "Chef RPG_Data");
        return new PipelinePaths(
            gameRoot,
            gameData,
            Path.Combine(gameData, "Managed"),
            project,
            Path.GetFullPath(classData),
            Path.GetFullPath(output),
            reports,
            Path.Combine(reports, "chef_rpg_pipeline.json"),
            Path.Combine(reports, "faltantes_memoria.json"));
    }
}

internal sealed record MissingText(string Table, string Key, string Source, int Row);

internal sealed class TableReport
{
    public required string Table { get; init; }
    public required long PathId { get; init; }
    public int Rows { get; set; }
    public int English { get; set; }
    public int ExistingBr { get; set; }
    public int FromMemory { get; set; }
    public int Conflicts { get; set; }
    public List<MissingText> Missing { get; } = [];
    public int MissingOccurrences => Missing.Count;
    public int MissingUnique => Missing.Select(item => item.Source).Distinct(StringComparer.Ordinal).Count();
}

internal sealed class PipelineReport
{
    public required DateTimeOffset GeneratedAt { get; init; }
    public required string Mode { get; init; }
    public required string UnityVersion { get; init; }
    public required List<TableReport> Tables { get; init; }
    public required List<string> Outputs { get; init; }
    public int TargetAssets => Tables.Count;
    public int MissingOccurrences => Tables.Sum(table => table.MissingOccurrences);
    public int MissingUnique => Tables.SelectMany(table => table.Missing)
        .Select(item => item.Source).Distinct(StringComparer.Ordinal).Count();
    public bool Ready => TargetAssets == 5 && MissingUnique == 0;
}

internal sealed class ChefRpgPipeline
{
    private const string ResourcesName = "resources.assets";
    private static readonly HashSet<string> ExpectedTables = new(StringComparer.Ordinal)
    {
        "Romance Localization",
        "Localization",
        "UI Localization",
        "Festivals Localization",
        "Item Localization"
    };

    private readonly PipelinePaths paths;
    private readonly Dictionary<string, string> memory;

    public ChefRpgPipeline(PipelinePaths paths)
    {
        this.paths = paths;
        ValidateInputs();
        memory = JsonSerializer.Deserialize<Dictionary<string, string>>(
            File.ReadAllText(Path.Combine(paths.Project, "memoria.json")))
            ?? throw new InvalidDataException("memoria.json invalido.");
    }

    public PipelineReport Run(ProcessingMode mode)
    {
        if (mode == ProcessingMode.Build)
        {
            if (Directory.Exists(paths.Output))
                Directory.Delete(paths.Output, recursive: true);
            Directory.CreateDirectory(paths.Output);
        }

        var source = Path.Combine(mode == ProcessingMode.Verify ? paths.Output : paths.GameData, ResourcesName);
        if (!File.Exists(source))
            throw new FileNotFoundException("resources.assets nao encontrado.", source);

        var manager = CreateManager();
        var assets = manager.LoadAssetsFile(source, false);
        manager.LoadClassDatabaseFromPackage(assets.file.Metadata.UnityVersion);
        var tables = new List<TableReport>();

        foreach (var info in assets.file.GetAssetsOfType(AssetClassID.TextAsset))
        {
            var root = manager.GetBaseField(assets, info);
            var name = root["m_Name"].AsString;
            if (!ExpectedTables.Contains(name))
                continue;

            var document = CsvDocument.Parse(root["m_Script"].AsString, name);
            var report = ProcessTable(document, name, info.PathId, mode);
            tables.Add(report);
            if (mode == ProcessingMode.Build)
            {
                root["m_Script"].AsString = document.Serialize();
                info.SetNewData(root);
            }
        }

        var actualNames = tables.Select(table => table.Table).ToHashSet(StringComparer.Ordinal);
        if (!actualNames.SetEquals(ExpectedTables))
            throw new InvalidDataException(
                $"Tabelas divergentes. Esperadas: {string.Join(", ", ExpectedTables)}. " +
                $"Encontradas: {string.Join(", ", actualNames)}.");

        var outputs = new List<string>();
        var reportResult = new PipelineReport
        {
            GeneratedAt = DateTimeOffset.UtcNow,
            Mode = mode.ToString().ToLowerInvariant(),
            UnityVersion = assets.file.Metadata.UnityVersion,
            Tables = tables.OrderBy(table => table.PathId).ToList(),
            Outputs = outputs
        };

        if (mode == ProcessingMode.Build && !reportResult.Ready)
        {
            manager.UnloadAll();
            Directory.Delete(paths.Output, recursive: true);
            return reportResult;
        }

        if (mode == ProcessingMode.Build)
        {
            var output = Path.Combine(paths.Output, ResourcesName);
            using (var writer = new AssetsFileWriter(output))
                assets.file.Write(writer);
            outputs.Add(output);
        }

        manager.UnloadAll();
        return reportResult;
    }

    private TableReport ProcessTable(CsvDocument document, string table, long pathId, ProcessingMode mode)
    {
        var report = new TableReport { Table = table, PathId = pathId, Rows = document.Rows.Count };
        for (var rowIndex = 1; rowIndex < document.Rows.Count; rowIndex++)
        {
            var row = document.Rows[rowIndex];
            if (row.Length <= document.MaxRequiredIndex)
                continue;
            var source = row[document.EnglishIndex];
            if (string.IsNullOrWhiteSpace(source))
                continue;

            report.English++;
            var br = row[document.BrIndex];
            var hasMemory = memory.TryGetValue(source, out var remembered) && !string.IsNullOrWhiteSpace(remembered);
            string? translation = null;
            if (!string.IsNullOrWhiteSpace(br))
            {
                report.ExistingBr++;
                translation = br;
                if (hasMemory && !string.Equals(br, remembered, StringComparison.Ordinal))
                    report.Conflicts++;
            }
            else if (hasMemory)
            {
                report.FromMemory++;
                translation = remembered;
            }

            if (translation is null)
            {
                report.Missing.Add(new MissingText(
                    table,
                    row[document.KeyIndex],
                    source,
                    rowIndex + 1));
                continue;
            }

            if (mode == ProcessingMode.Build)
            {
                row[document.EnglishIndex] = translation;
                row[document.BrIndex] = translation;
            }
            else if (mode == ProcessingMode.Verify && !string.Equals(source, translation, StringComparison.Ordinal))
                throw new InvalidDataException($"Verificacao falhou em {table}, linha {rowIndex + 1}.");
        }
        return report;
    }

    private AssetsManager CreateManager()
    {
        var manager = new AssetsManager();
        manager.LoadClassPackage(paths.ClassData);
        return manager;
    }

    private void ValidateInputs()
    {
        foreach (var directory in new[] { paths.GameRoot, paths.GameData, paths.Managed, paths.Project })
            if (!Directory.Exists(directory))
                throw new DirectoryNotFoundException(directory);
        if (!File.Exists(paths.ClassData))
            throw new FileNotFoundException("classdata.tpk nao encontrado.", paths.ClassData);
        if (!File.Exists(Path.Combine(paths.Project, "memoria.json")))
            throw new FileNotFoundException("memoria.json nao encontrado.");
    }
}

internal sealed class CsvDocument
{
    public required List<string[]> Rows { get; init; }
    public required int KeyIndex { get; init; }
    public required int EnglishIndex { get; init; }
    public required int BrIndex { get; init; }
    public int MaxRequiredIndex => Math.Max(KeyIndex, Math.Max(EnglishIndex, BrIndex));

    public static CsvDocument Parse(string text, string table)
    {
        var rows = new List<string[]>();
        using var reader = new StringReader(text);
        using var parser = new TextFieldParser(reader)
        {
            HasFieldsEnclosedInQuotes = true,
            TrimWhiteSpace = false
        };
        parser.SetDelimiters(",");
        while (!parser.EndOfData)
            rows.Add(parser.ReadFields() ?? []);
        if (rows.Count == 0)
            throw new InvalidDataException($"CSV vazio: {table}.");
        var header = rows[0];
        var key = Array.IndexOf(header, "key");
        var english = Array.IndexOf(header, "en");
        var br = Array.IndexOf(header, "br");
        if (key < 0 || english < 0 || br < 0)
            throw new InvalidDataException($"Cabecalho key/en/br invalido: {table}.");
        return new CsvDocument { Rows = rows, KeyIndex = key, EnglishIndex = english, BrIndex = br };
    }

    public string Serialize()
    {
        var output = new StringBuilder();
        foreach (var row in Rows)
        {
            output.AppendJoin(',', row.Select(Escape));
            output.Append('\n');
        }
        return output.ToString();
    }

    private static string Escape(string value)
    {
        if (value.Length == 0)
            return string.Empty;
        return $"\"{value.Replace("\"", "\"\"", StringComparison.Ordinal)}\"";
    }
}
