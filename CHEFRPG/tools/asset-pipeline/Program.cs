using System.Text.Encodings.Web;
using System.Text.Json;

if (args.Length != 5 || args[0] is not ("scan" or "build" or "verify"))
{
    Console.Error.WriteLine("Uso: <scan|build|verify> <jogo> <projeto-CHEFRPG> <classdata.tpk> <saida>");
    return 2;
}

var jsonOptions = new JsonSerializerOptions
{
    Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    WriteIndented = true
};

try
{
    var mode = Enum.Parse<ProcessingMode>(args[0], ignoreCase: true);
    var paths = PipelinePaths.Create(args[1], args[2], args[3], args[4]);
    var report = new ChefRpgPipeline(paths).Run(mode);
    Directory.CreateDirectory(paths.Reports);
    var reportJson = JsonSerializer.Serialize(report, jsonOptions) + Environment.NewLine;
    File.WriteAllText(paths.Report, reportJson);
    File.WriteAllText(
        paths.MissingMemory,
        JsonSerializer.Serialize(
            report.Tables.SelectMany(table => table.Missing)
                .GroupBy(item => item.Source, StringComparer.Ordinal)
                .OrderBy(group => group.Key, StringComparer.Ordinal)
                .ToDictionary(group => group.Key, _ => string.Empty, StringComparer.Ordinal),
            jsonOptions) + Environment.NewLine);
    foreach (var table in report.Tables)
    {
        Console.WriteLine(
            $"{table.Table}: {table.English} textos, {table.ExistingBr} em br, " +
            $"{table.FromMemory} da memoria, {table.MissingOccurrences} faltantes, " +
            $"{table.Conflicts} conflitos");
    }
    Console.WriteLine(
        $"TOTAL: {report.TargetAssets} tabelas, {report.MissingOccurrences} ocorrencias faltantes, " +
        $"{report.MissingUnique} textos unicos faltantes, Ready={report.Ready}");
    Console.WriteLine($"Relatorio: {paths.Report}");
    return report.Ready ? 0 : 3;
}
catch (Exception ex)
{
    Console.Error.WriteLine($"ERRO: {ex.Message}");
    Console.Error.WriteLine(ex.StackTrace);
    return 1;
}
