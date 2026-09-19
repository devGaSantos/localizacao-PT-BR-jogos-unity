using System.Diagnostics;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;

ApplicationConfiguration.Initialize();
if (args.Contains("--verify-payload", StringComparer.Ordinal))
    Environment.Exit(LauncherForm.HasBundledPayload() ? 0 : 1);
Application.Run(new LauncherForm());

internal sealed class LauncherForm : Form
{
    public static bool HasBundledPayload()
    {
        var payload = Path.Combine(AppContext.BaseDirectory, "payload");
        return File.Exists(Path.Combine(payload, "version.txt")) &&
               File.Exists(Path.Combine(payload, "bin", "ChefRpg.AssetPipeline.exe")) &&
               File.Exists(Path.Combine(payload, "bin", "classdata.tpk"));
    }
    private readonly Button playButton = new() { Text = "Atualizar e jogar", AutoSize = false, Size = new Size(210, 42) };
    private readonly Label status = new() { AutoSize = false, Height = 48, TextAlign = ContentAlignment.MiddleLeft };
    private readonly ProgressBar progress = new() { Minimum = 0, Maximum = 100, Size = new Size(470, 15) };
    private readonly string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerlinTraducoes", "ChefRpg");
    private readonly string payloadRoot = AppContext.BaseDirectory;

    public LauncherForm()
    {
        Text = "Chef RPG — Tradução PT-BR";
        ClientSize = new Size(760, 470);
        MinimumSize = new Size(760, 470);
        MaximumSize = new Size(760, 470);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(38, 28, 38);
        Font = new Font("Segoe UI", 10);

        Controls.Add(new PictureBox { Image = LoadHero(), SizeMode = PictureBoxSizeMode.Zoom, Dock = DockStyle.Top, Height = 300 });

        var title = new Label
        {
            Text = "CHEF RPG  •  TRADUÇÃO PT-BR",
            ForeColor = Color.FromArgb(255, 221, 145),
            Font = new Font("Segoe UI Semibold", 15),
            Location = new Point(28, 318),
            AutoSize = true
        };
        Controls.Add(title);

        status.ForeColor = Color.FromArgb(235, 225, 235);
        status.Text = "Pronto para verificar a tradução.";
        status.Location = new Point(28, 352);
        status.Width = 470;
        Controls.Add(status);
        progress.Location = new Point(28, 399);
        Controls.Add(progress);

        playButton.BackColor = Color.FromArgb(196, 106, 82);
        playButton.ForeColor = Color.White;
        playButton.FlatStyle = FlatStyle.Flat;
        playButton.FlatAppearance.BorderSize = 0;
        playButton.Location = new Point(522, 366);
        playButton.Click += async (_, _) => await StartUpdateAsync();
        Controls.Add(playButton);
    }

    private async Task StartUpdateAsync()
    {
        playButton.Enabled = false;
        SetProgress("Preparando a verificacao...", 1);
        await Task.Yield();
        var installerProgress = new Progress<(string Text, int Value)>(update => SetProgress(update.Text, update.Value));
        try { await Task.Run(() => EnsurePayload(installerProgress)); }
        catch (Exception error)
        {
            playButton.Enabled = true;
            MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }
        await UpdateAndPlayAsync();
    }

    private async Task UpdateAndPlayAsync()
    {
        try
        {
            SetProgress("Localizando o jogo...", 2);
            await Task.Yield();
            var state = ReadState();
            var gamePath = FindGamePath(state?.GamePath);
            if (gamePath is null)
            {
                using var dialog = new FolderBrowserDialog { Description = "Selecione a pasta onde fica Chef RPG.exe" };
                if (dialog.ShowDialog(this) != DialogResult.OK)
                    return;
                gamePath = dialog.SelectedPath;
            }

            var gameAsset = Path.Combine(gamePath, "Chef RPG_Data", "resources.assets");
            var gameExe = Path.Combine(gamePath, "Chef RPG.exe");
            if (!File.Exists(gameAsset) || !File.Exists(gameExe))
                throw new InvalidOperationException("A pasta selecionada não contém Chef RPG.exe e Chef RPG_Data\\resources.assets.");
            if (Process.GetProcessesByName("Chef RPG").Length > 0)
                throw new InvalidOperationException("Feche Chef RPG antes de atualizar a tradução.");

            var currentHash = await Task.Run(() => Sha256(gameAsset));
            if (state?.TranslatedSha256 != currentHash)
            {
                var pipeline = Path.Combine(payloadRoot, "payload", "bin", "ChefRpg.AssetPipeline.exe");
                var classData = Path.Combine(payloadRoot, "payload", "bin", "classdata.tpk");
                var memory = Path.Combine(root, "memoria.json");
                var staging = Path.Combine(root, "staging");
                if (!File.Exists(pipeline) || !File.Exists(classData) || !File.Exists(memory))
                    throw new InvalidOperationException("O pacote está incompleto. Extraia o ZIP inteiro antes de usar.");

                SetProgress("Verificando textos novos...", 5);
                await RunPipeline(pipeline, "scan", gamePath, root, classData, staging);
                var missing = CountMissing(Path.Combine(root, "relatorios", "faltantes_memoria.json"));
                var fallback = false;
                if (missing > 0)
                {
                    var choice = AskTranslationMode(missing);
                    if (choice == TranslationMode.Cancel) return;
                    fallback = choice == TranslationMode.KeepEnglish;
                    if (!fallback) await TranslateMissingAsync(memory, missing);
                }
                SetProgress(fallback ? "Mantendo textos novos em inglês e reconstruindo (estimativa: 1 min)..." : "Reconstruindo a tradução (estimativa: 1 min)...", 50);
                await RunPipeline(pipeline, fallback ? "build-fallback" : "build", gamePath, root, classData, staging);
                SetProgress("Validando os arquivos (estimativa: menos de 1 min)...", 85);
                await RunPipeline(pipeline, "verify", gamePath, root, classData, staging);

                var rebuiltAsset = Path.Combine(staging, "resources.assets");
                if (!File.Exists(rebuiltAsset))
                    throw new InvalidOperationException("O arquivo traduzido não foi gerado.");
                var backup = Path.Combine(root, "backups", DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.CreateDirectory(backup);
                await Task.Run(() =>
                {
                    File.Copy(gameAsset, Path.Combine(backup, "resources.assets"), true);
                    try { File.Copy(rebuiltAsset, gameAsset, true); }
                    catch
                    {
                        File.Copy(Path.Combine(backup, "resources.assets"), gameAsset, true);
                        throw;
                    }
                });
                WriteState(new LauncherState(gamePath, currentHash, await Task.Run(() => Sha256(gameAsset)), DateTimeOffset.UtcNow));
                SetProgress("Tradução atualizada. Abrindo o jogo...", 100);
            }
            else
            {
                SetProgress("Tradução já está atualizada. Abrindo o jogo...", 100);
            }

            Process.Start(new ProcessStartInfo(gameExe) { WorkingDirectory = gamePath, UseShellExecute = true });
            Close();
        }
        catch (Exception error)
        {
            status.Text = "Não foi possível atualizar a tradução.";
            MessageBox.Show(this, error.Message, "Chef RPG — Tradução PT-BR", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            if (!IsDisposed) playButton.Enabled = true;
        }
    }

    private void SetProgress(string text, int value)
    {
        if (InvokeRequired)
        {
            BeginInvoke(() => SetProgress(text, value));
            return;
        }
        status.Text = text;
        progress.Value = Math.Clamp(value, progress.Minimum, progress.Maximum);
    }

    private static async Task RunPipeline(string pipeline, params string[] arguments)
    {
        var startInfo = new ProcessStartInfo(pipeline)
        {
            UseShellExecute = false,
            RedirectStandardError = true,
            RedirectStandardOutput = true,
            CreateNoWindow = true
        };
        foreach (var argument in arguments)
            startInfo.ArgumentList.Add(argument);
        using var process = Process.Start(startInfo) ?? throw new InvalidOperationException("Não foi possível iniciar o atualizador.");
        var outputTask = process.StandardOutput.ReadToEndAsync();
        var errorTask = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        var output = await outputTask;
        var error = await errorTask;
        if (process.ExitCode is not (0 or 3))
            throw new InvalidOperationException(string.IsNullOrWhiteSpace(error) ? output : error);
    }

    private TranslationMode AskTranslationMode(int missing)
    {
        using var dialog = new Form { Text = "Textos novos encontrados", StartPosition = FormStartPosition.CenterParent, ClientSize = new Size(570, 205), FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false, MinimizeBox = false, BackColor = BackColor };
        dialog.Controls.Add(new Label { Text = $"Existem {missing:N0} entradas ainda não traduzidas nesta atualização.\n\nVocê prefere manter esses textos em inglês até uma tradução oficial, ou tentar traduzi-los automaticamente? A tradução automática pode levar alguns minutos.", ForeColor = Color.White, Location = new Point(18, 16), Size = new Size(535, 90) });
        dialog.Controls.Add(new Button { Text = "Manter em inglês\ne aguardar versão oficial", DialogResult = DialogResult.No, Size = new Size(230, 54), Location = new Point(18, 125) });
        dialog.Controls.Add(new Button { Text = "Tentar traduzir\nautomaticamente", DialogResult = DialogResult.Yes, Size = new Size(230, 54), Location = new Point(322, 125) });
        return dialog.ShowDialog(this) switch { DialogResult.Yes => TranslationMode.Automatic, DialogResult.No => TranslationMode.KeepEnglish, _ => TranslationMode.Cancel };
    }

    private async Task TranslateMissingAsync(string memoryPath, int total)
    {
        var missingPath = Path.Combine(root, "relatorios", "faltantes_memoria.json");
        var missing = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(missingPath), JsonOptions) ?? [];
        var memory = JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(memoryPath), JsonOptions) ?? [];
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(25) };
        var sources = missing.Keys.Where(source => !memory.TryGetValue(source, out var translation) || string.IsNullOrWhiteSpace(translation)).ToList();
        for (var index = 0; index < sources.Count; index++)
        {
            memory[sources[index]] = await TranslateAsync(client, sources[index]);
            SetProgress($"Traduzindo automaticamente {index + 1:N0}/{total:N0} (estimativa: {Math.Max(1, (total - index) / 8)} min)...", 8 + (int)Math.Round(35d * (index + 1) / Math.Max(1, total)));
            await Task.Delay(120);
        }
        File.WriteAllText(memoryPath, JsonSerializer.Serialize(memory, new JsonSerializerOptions(JsonOptions) { WriteIndented = true }) + Environment.NewLine);
    }

    private static int CountMissing(string path) => JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(path), JsonOptions)?.Count ?? 0;
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };
    private static readonly Regex ProtectedToken = new(@"(\r\n|\r|\n|\[[^\]]+\]|<[^>]+>|\{[^{}]+\}|\([a-z_][a-z0-9_]*\)|_)", RegexOptions.Singleline);
    private static async Task<string> TranslateAsync(HttpClient client, string source)
    {
        var tokens = new List<string>();
        var protectedText = ProtectedToken.Replace(source, match => { tokens.Add(match.Value); return $"CHEF_TOKEN_{tokens.Count - 1}_END"; });
        var json = await client.GetStringAsync("https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=pt&dt=t&q=" + Uri.EscapeDataString(protectedText));
        using var document = JsonDocument.Parse(json);
        var translated = string.Concat(document.RootElement[0].EnumerateArray().Select(part => part[0].GetString()));
        if (string.IsNullOrWhiteSpace(translated)) throw new InvalidOperationException("O serviço de tradução não retornou texto.");
        for (var index = 0; index < tokens.Count; index++)
        {
            var marker = $"CHEF_TOKEN_{index}_END";
            if (!translated.Contains(marker, StringComparison.Ordinal)) throw new InvalidOperationException("O serviço de tradução alterou uma marcação do jogo.");
            translated = translated.Replace(marker, tokens[index], StringComparison.Ordinal);
        }
        return translated;
    }

    private LauncherState? ReadState()
    {
        var path = Path.Combine(root, "estado.json");
        try { return File.Exists(path) ? JsonSerializer.Deserialize<LauncherState>(File.ReadAllText(path)) : null; }
        catch (JsonException) { return null; }
    }

    private void WriteState(LauncherState state) => File.WriteAllText(Path.Combine(root, "estado.json"), JsonSerializer.Serialize(state));

    private static string? FindGamePath(string? savedPath)
    {
        var candidates = new List<string?> { savedPath, @"C:\Program Files (x86)\Steam\steamapps\common\Chef RPG" };
        try
        {
            using var steam = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam");
            candidates.Add(Path.Combine(steam?.GetValue("SteamPath")?.ToString() ?? string.Empty, "steamapps", "common", "Chef RPG"));
        }
        catch (IOException) { }
        return candidates.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(Path.Combine(path, "Chef RPG.exe")));
    }

    private static string Sha256(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

    private void EnsurePayload(IProgress<(string Text, int Value)> progressReporter)
    {
        var sourceRoot = Path.Combine(payloadRoot, "payload");
        var sourceVersion = Path.Combine(sourceRoot, "version.txt");
        if (!File.Exists(sourceVersion)) throw new InvalidOperationException("O pacote interno do launcher não foi encontrado. Baixe o Launcher.exe novamente.");
        var targetVersion = Path.Combine(root, "version.txt");
        if (File.Exists(targetVersion) && File.ReadAllText(targetVersion) == File.ReadAllText(sourceVersion)) return;
        // O pipeline e o classdata ja estao disponiveis na extracao interna do
        // single-file. Copiar esse executavel grande novamente para LocalAppData
        // deixa o primeiro clique lento sem beneficio. So a memoria mutavel vai
        // para o diretorio local.
        var files = Directory.EnumerateFiles(sourceRoot, "*", SearchOption.AllDirectories)
            .Where(path =>
            {
                var relative = Path.GetRelativePath(sourceRoot, path);
                return !relative.StartsWith($"bin{Path.DirectorySeparatorChar}", StringComparison.OrdinalIgnoreCase) && !string.Equals(relative, "version.txt", StringComparison.OrdinalIgnoreCase);
            })
            .ToList();
        var totalBytes = files.Sum(path => new FileInfo(path).Length);
        long copiedBytes = 0;
        var lastReportedProgress = -1;
        void ReportProgress(long done, int fileIndex)
        {
            var value = Math.Clamp(2 + (int)(18d * done / Math.Max(1, totalBytes)), 2, 20);
            if (value == lastReportedProgress && done != totalBytes) return;
            lastReportedProgress = value;
            progressReporter.Report(($"Preparando componentes internos {fileIndex + 1}/{files.Count} ({FormatSize(done)}/{FormatSize(totalBytes)})...", value));
        }
        for (var index = 0; index < files.Count; index++)
        {
            var source = files[index];
            var relative = Path.GetRelativePath(sourceRoot, source);
            var target = Path.Combine(root, relative);
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            var sourceLength = new FileInfo(source).Length;
            ReportProgress(copiedBytes, index);
            CopyFileWithProgress(source, target, bytesThisFile => ReportProgress(copiedBytes + bytesThisFile, index));
            copiedBytes += sourceLength;
        }
        ReportProgress(totalBytes, files.Count - 1);
        Directory.CreateDirectory(root);
        File.Copy(sourceVersion, targetVersion, true);
    }

    private static void CopyFileWithProgress(string source, string destination, Action<long> report)
    {
        const int bufferSize = 1024 * 1024;
        using var input = new FileStream(source, FileMode.Open, FileAccess.Read, FileShare.Read, bufferSize, FileOptions.SequentialScan);
        using var output = new FileStream(destination, FileMode.Create, FileAccess.Write, FileShare.None, bufferSize, FileOptions.SequentialScan);
        var buffer = new byte[bufferSize];
        long copied = 0;
        int read;
        while ((read = input.Read(buffer, 0, buffer.Length)) > 0)
        {
            output.Write(buffer, 0, read);
            copied += read;
            report(copied);
        }
    }

    private static string FormatSize(long bytes) => $"{bytes / 1024d / 1024d:F0} MB";

    private static Image? LoadHero()
    {
        var embedded = typeof(LauncherForm).Assembly.GetManifestResourceNames().FirstOrDefault(name => name.EndsWith(".assets.hero.png", StringComparison.OrdinalIgnoreCase));
        if (embedded is not null)
        {
            using var stream = typeof(LauncherForm).Assembly.GetManifestResourceStream(embedded);
            if (stream is not null) return new Bitmap(stream);
        }
        var heroPath = Path.Combine(AppContext.BaseDirectory, "assets", "hero.png");
        return File.Exists(heroPath) ? Image.FromFile(heroPath) : null;
    }
}

internal sealed record LauncherState(string GamePath, string SourceSha256, string TranslatedSha256, DateTimeOffset UpdatedAt);
internal enum TranslationMode { KeepEnglish, Automatic, Cancel }
