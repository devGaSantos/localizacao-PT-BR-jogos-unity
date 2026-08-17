using System.Text.Json;

if (args.Length != 5 || args[0] is not ("scan" or "build" or "verify"))
{
    Console.Error.WriteLine("Uso: <scan|build|verify> <jogo> <projeto-LW> <classdata.tpk> <saida>");
    return 2;
}

try
{
    var mode = Enum.Parse<ProcessingMode>(args[0], ignoreCase: true);
    var paths = PipelinePaths.Create(args[1], args[2], args[3], args[4]);
    var pipeline = new AssetTranslationPipeline(paths);
    var report = pipeline.Run(mode);

    Directory.CreateDirectory(Path.GetDirectoryName(paths.ReportPath)!);
    File.WriteAllText(
        paths.ReportPath,
        JsonSerializer.Serialize(report, JsonOptions.Pretty) + Environment.NewLine
    );
    Console.WriteLine(JsonSerializer.Serialize(report, JsonOptions.Pretty));
    return report.Ready ? 0 : 3;
}
catch (Exception ex)
{
    Console.Error.WriteLine($"ERRO: {ex.Message}");
    Console.Error.WriteLine(ex.StackTrace);
    return 1;
}
