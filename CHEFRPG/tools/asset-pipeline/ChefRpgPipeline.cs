using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using AssetsTools.NET;
using AssetsTools.NET.Extra;

internal enum ProcessingMode
{
    Scan,
    Export,
    Build,
    BuildFallback,
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
        var loadedMemory = JsonSerializer.Deserialize<Dictionary<string, string>>(
            File.ReadAllText(Path.Combine(paths.Project, "memoria.json")))
            ?? throw new InvalidDataException("memoria.json invalido.");
        memory = loadedMemory
            .Where(entry => IsUsableTranslation(entry.Value))
            .ToDictionary(entry => entry.Key, entry => entry.Value, StringComparer.Ordinal);
    }

    public PipelineReport Run(ProcessingMode mode)
    {
        if (mode is ProcessingMode.Build or ProcessingMode.BuildFallback)
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
        var replacers = new List<AssetsReplacer>();
        var exports = new Dictionary<string, string>(StringComparer.Ordinal);

        foreach (var info in assets.file.GetAssetsOfType(AssetClassID.TextAsset))
        {
            var root = manager.GetBaseField(assets, info);
            var name = root["m_Name"].AsString;
            if (!ExpectedTables.Contains(name))
                continue;

            var document = CsvDocument.Parse(root["m_Script"].AsString, name);
            var report = ProcessTable(document, name, info.PathId, mode);
            tables.Add(report);
            if (mode == ProcessingMode.Export)
                exports[name] = root["m_Script"].AsString;
            if (mode is ProcessingMode.Build or ProcessingMode.BuildFallback)
            {
                root["m_Script"].AsString = document.Serialize();
                replacers.Add(new AssetsReplacerFromMemory(assets.file, info, root));
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

        if (mode is ProcessingMode.Build or ProcessingMode.BuildFallback)
        {
            var output = Path.Combine(paths.Output, ResourcesName);
            using (var writer = new AssetsFileWriter(output))
                assets.file.Write(writer, 0, replacers, null);
            SaveMemory();
            outputs.Add(output);
        }
        else if (mode == ProcessingMode.Export)
        {
            // Export mode is read-only with respect to the installed game. The same
            // directory is used by the manual translator, keeping both workflows in
            // sync.
            var exportDirectory = Path.Combine(paths.Project, "exportados");
            Directory.CreateDirectory(exportDirectory);
            foreach (var table in tables)
            {
                var filename = $"{table.Table}-resources.assets-{table.PathId}.txt";
                var output = Path.Combine(exportDirectory, filename);
                File.WriteAllText(output, exports[table.Table], new UTF8Encoding(false));
                outputs.Add(output);
            }
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
            // Some upstream CSV cells use a fixed run of '#' characters as a
            // sentinel for unavailable text. It is not a Portuguese translation.
            var hasBrTranslation = IsUsableTranslation(br);
            var hasMemory = memory.TryGetValue(source, out var remembered) && IsUsableTranslation(remembered);
            string? translation = null;
            if (hasBrTranslation)
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
                if (mode != ProcessingMode.BuildFallback)
                    continue;
                // Preserve genuinely new text in English until a reviewed PT-BR
                // translation is shipped, rather than copying an old asset or
                // failing the player-facing updater.
                translation = source;
            }

            if (mode is ProcessingMode.Build or ProcessingMode.BuildFallback)
            {
                row[document.EnglishIndex] = translation;
                row[document.BrIndex] = translation;
                memory[source] = translation;
            }
            else if (mode == ProcessingMode.Verify && !string.Equals(source, translation, StringComparison.Ordinal))
                throw new InvalidDataException($"Verificacao falhou em {table}, linha {rowIndex + 1}.");
        }
        return report;
    }

    private static bool IsUsableTranslation(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
            return false;
        return value.Any(character => character != '#');
    }

    private AssetsManager CreateManager()
    {
        var manager = new AssetsManager();
        manager.LoadClassPackage(paths.ClassData);
        return manager;
    }

    private void SaveMemory()
    {
        var path = Path.Combine(paths.Project, "memoria.json");
        var temporary = path + ".tmp";
        var options = new JsonSerializerOptions
        {
            Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
            WriteIndented = true
        };
        File.WriteAllText(temporary, JsonSerializer.Serialize(memory, options) + Environment.NewLine);
        File.Move(temporary, path, overwrite: true);
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
        var rows = ParseRows(text);
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

    private static List<string[]> ParseRows(string text)
    {
        var rows = new List<string[]>();
        var row = new List<string>();
        var field = new StringBuilder();
        var quoted = false;

        void CompleteField()
        {
            row.Add(field.ToString());
            field.Clear();
        }

        void CompleteRow()
        {
            CompleteField();
            rows.Add(row.ToArray());
            row.Clear();
        }

        for (var index = 0; index < text.Length; index++)
        {
            var character = text[index];
            if (quoted)
            {
                if (character == '"')
                {
                    if (index + 1 < text.Length && text[index + 1] == '"')
                    {
                        field.Append('"');
                        index++;
                    }
                    else
                    {
                        quoted = false;
                    }
                }
                else
                {
                    field.Append(character);
                }
                continue;
            }

            if (character == '"' && field.Length == 0)
            {
                quoted = true;
            }
            else if (character == ',')
            {
                CompleteField();
            }
            else if (character == '\r' || character == '\n')
            {
                if (character == '\r' && index + 1 < text.Length && text[index + 1] == '\n')
                    index++;
                CompleteRow();
            }
            else
            {
                field.Append(character);
            }
        }

        if (quoted)
            throw new InvalidDataException("CSV com aspas nao fechadas.");
        if (field.Length > 0 || row.Count > 0)
            CompleteRow();
        return rows;
    }

    public string Serialize()
    {
        var output = new StringBuilder();
        foreach (var row in Rows)
        {
            output.AppendJoin(',', row.Select(Escape));
            // O parser do Chef RPG separa registros por CRLF. Usar apenas LF
            // faz a tabela inteira parecer uma única linha e deixa a UI vazia.
            output.Append("\r\n");
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
