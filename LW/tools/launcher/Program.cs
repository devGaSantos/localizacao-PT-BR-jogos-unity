using System.Diagnostics;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
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
               File.Exists(Path.Combine(payload, "bin", "LittleWitch.AssetPipeline.exe")) &&
               File.Exists(Path.Combine(payload, "bin", "classdata.tpk"));
    }
    private readonly string root = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MerlinTraducoes", "LittleWitch");
    private readonly string payloadRoot = AppContext.BaseDirectory;
    private readonly Label status = new() { AutoSize = false, Height = 46, TextAlign = ContentAlignment.MiddleLeft };
    private readonly ProgressBar progress = new() { Minimum = 0, Maximum = 100, Value = 0, Size = new Size(475, 15) };
    private readonly Button play = new() { Text = "Atualizar e jogar", Size = new Size(210, 42), FlatStyle = FlatStyle.Flat };

    public LauncherForm()
    {
        Text = "Little Witch in the Woods — Tradução PT-BR";
        ClientSize = new Size(760, 470);
        MinimumSize = MaximumSize = Size;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(30, 22, 37);
        Controls.Add(new PictureBox { Image = LoadHero(), SizeMode = PictureBoxSizeMode.Zoom, Dock = DockStyle.Top, Height = 300 });
        Controls.Add(new Label { Text = "LITTLE WITCH IN THE WOODS  •  TRADUÇÃO PT-BR", ForeColor = Color.FromArgb(229, 204, 255), Font = new Font("Segoe UI Semibold", 14), Location = new Point(25, 318), AutoSize = true });
        status.Text = "Pronto para verificar a tradução.";
        status.ForeColor = Color.White;
        status.Location = new Point(25, 352);
        status.Width = 475;
        Controls.Add(status);
        progress.Location = new Point(25, 399);
        Controls.Add(progress);
        play.BackColor = Color.FromArgb(116, 75, 161);
        play.ForeColor = Color.White;
        play.FlatAppearance.BorderSize = 0;
        play.Location = new Point(522, 366);
        play.Click += async (_, _) => await StartUpdateAsync();
        Controls.Add(play);
    }

    private async Task StartUpdateAsync()
    {
        play.Enabled = false;
        SetProgress("Preparando a verificacao...", 1);
        await Task.Yield();
        var installerProgress = new Progress<(string Text, int Value)>(update => SetProgress(update.Text, update.Value));
        try { await Task.Run(() => EnsurePayload(installerProgress)); }
        catch (Exception error)
        {
            play.Enabled = true;
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
            var game = FindGame(state?.GamePath);
            if (game is null)
            {
                using var picker = new FolderBrowserDialog { Description = "Selecione a pasta que contém Little Witch in the Woods.exe" };
                if (picker.ShowDialog(this) != DialogResult.OK) return;
                game = picker.SelectedPath;
            }
            var exe = Path.Combine(game, "Little Witch in the Woods.exe");
            var data = Path.Combine(game, "LWIW_Data");
            var resources = Path.Combine(data, "resources.assets");
            if (!File.Exists(exe) || !File.Exists(resources)) throw new InvalidOperationException("A pasta selecionada não contém o jogo.");
            if (Process.GetProcesses().Any(process => process.ProcessName.Contains("Little Witch", StringComparison.OrdinalIgnoreCase) || process.ProcessName == "LWIW")) throw new InvalidOperationException("Feche o jogo antes de atualizar a tradução.");
            var before = await Task.Run(() => Hash(resources));
            if (state?.TranslatedSha256 != before)
            {
                var pipeline = Path.Combine(payloadRoot, "payload", "bin", "LittleWitch.AssetPipeline.exe");
                var project = Path.Combine(root, "LW");
                var classData = Path.Combine(payloadRoot, "payload", "bin", "classdata.tpk");
                var staging = Path.Combine(root, "staging");
                SetProgress("Verificando textos novos...", 5);
                await Run(pipeline, "scan", game, project, classData, staging);
                var missing = CountMissing(Path.Combine(project, "relatorios", "asset_pipeline_automatico.json"));
                var fallback = false;
                if (missing > 0)
                {
                    var choice = AskTranslationMode(missing);
                    if (choice == TranslationMode.Cancel) return;
                    fallback = choice == TranslationMode.KeepEnglish;
                    if (!fallback)
                        await TranslateMissingAsync(project, missing);
                }
                SetProgress(
                    fallback ? "Mantendo novos textos em inglês e reconstruindo (estimativa: 1–2 min)..." : "Reconstruindo a tradução (estimativa: 1–2 min)...",
                    45);
                await Run(pipeline, fallback ? "build-fallback" : "build", game, project, classData, staging);
                SetProgress("Validando os arquivos (estimativa: menos de 1 min)...", 80);
                await Run(pipeline, "verify", game, project, classData, staging);
                var targets = new[]
                {
                    "localization-string-tables-english(en)_assets_all.bundle",
                    "dialoguedb_assets_all.bundle", "defaultlocalgroup_assets_all.bundle", "resources.assets"
                };
                var backup = Path.Combine(root, "backups", DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.CreateDirectory(backup);
                await Task.Run(() =>
                {
                    foreach (var name in targets)
                    {
                        var destination = name == "resources.assets" ? resources : Path.Combine(data, "StreamingAssets", "aa", "StandaloneWindows64", name);
                        var source = Path.Combine(staging, name);
                        if (!File.Exists(source)) throw new InvalidOperationException($"Asset não gerado: {name}");
                        File.Copy(destination, Path.Combine(backup, name), true);
                        File.Copy(source, destination, true);
                    }
                });
                WriteState(new State(game, before, await Task.Run(() => Hash(resources)), DateTimeOffset.UtcNow));
                SetProgress("Tradução atualizada. Abrindo o jogo...", 100);
            }
            else SetProgress("Tradução já está atualizada. Abrindo o jogo...", 100);
            Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = game, UseShellExecute = true });
            Close();
        }
        catch (Exception error)
        {
            status.Text = "Não foi possível atualizar a tradução.";
            MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally { if (!IsDisposed) play.Enabled = true; }
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

    private static async Task Run(string executable, params string[] arguments)
    {
        if (!File.Exists(executable)) throw new InvalidOperationException("Atualizador incompleto. Extraia todo o ZIP.");
        var info = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardError = true, RedirectStandardOutput = true, CreateNoWindow = true };
        foreach (var argument in arguments) info.ArgumentList.Add(argument);
        using var process = Process.Start(info) ?? throw new InvalidOperationException("Não foi possível iniciar o atualizador.");
        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        if (process.ExitCode is not (0 or 3)) throw new InvalidOperationException(string.IsNullOrWhiteSpace(stderr) ? stdout : stderr);
    }

    private TranslationMode AskTranslationMode(int missing)
    {
        using var dialog = new Form
        {
            Text = "Textos novos encontrados",
            StartPosition = FormStartPosition.CenterParent,
            ClientSize = new Size(570, 205),
            FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false,
            MinimizeBox = false,
            BackColor = BackColor
        };
        dialog.Controls.Add(new Label
        {
            Text = $"Existem {missing:N0} entradas ainda não traduzidas nesta atualização.\n\n" +
                   "Você prefere manter esses textos em inglês até uma tradução oficial, ou tentar traduzi-los automaticamente? A tradução automática pode levar alguns minutos.",
            ForeColor = Color.White, Location = new Point(18, 16), Size = new Size(535, 90)
        });
        var keep = new Button { Text = "Manter em inglês\ne aguardar versão oficial", DialogResult = DialogResult.No, Size = new Size(230, 54), Location = new Point(18, 125) };
        var automatic = new Button { Text = "Tentar traduzir\nautomaticamente", DialogResult = DialogResult.Yes, Size = new Size(230, 54), Location = new Point(322, 125) };
        dialog.Controls.AddRange([keep, automatic]);
        dialog.CancelButton = new Button { DialogResult = DialogResult.Cancel, Visible = false };
        return dialog.ShowDialog(this) switch { DialogResult.Yes => TranslationMode.Automatic, DialogResult.No => TranslationMode.KeepEnglish, _ => TranslationMode.Cancel };
    }

    private async Task TranslateMissingAsync(string project, int total)
    {
        var report = JsonSerializer.Deserialize<PipelineReport>(File.ReadAllText(Path.Combine(project, "relatorios", "asset_pipeline_automatico.json")), JsonOptions)
            ?? throw new InvalidOperationException("Não foi possível ler o relatório de textos novos.");
        var jobs = report.Flows.SelectMany(flow => flow.Missing.Select(item => new TranslationJob(flow.Flow, item.Source))).Distinct().ToList();
        var general = LoadMemory(Path.Combine(project, "memoria_revisado.json"));
        var dialogues = LoadMemory(Path.Combine(project, "dialogos", "memory", "memoria.json"));
        var missionsPath = Path.Combine(Directory.GetParent(project)!.FullName, "missoes", "memoria_missoes.json");
        var missions = LoadMemory(missionsPath);
        using var client = new HttpClient { Timeout = TimeSpan.FromSeconds(25) };
        for (var index = 0; index < jobs.Count; index++)
        {
            var job = jobs[index];
            var translated = await TranslateAsync(client, job.Source);
            var target = job.Flow switch
            {
                "localization-string-tables-english(en)_assets_all" => general,
                "dialoguedb_assets_all" => dialogues,
                _ => missions
            };
            var key = job.Flow == "dialoguedb_assets_all" ? EscapeUnity(job.Source) : job.Source;
            var value = job.Flow == "dialoguedb_assets_all" ? EscapeUnity(translated) : translated;
            target.TryAdd(key, value);
            var percent = 8 + (int)Math.Round(32d * (index + 1) / Math.Max(1, total));
            SetProgress($"Traduzindo automaticamente {index + 1:N0}/{total:N0} (estimativa: {Math.Max(1, (total - index) / 8)} min)...", percent);
            await Task.Delay(120);
        }
        SaveMemory(Path.Combine(project, "memoria_revisado.json"), general);
        SaveMemory(Path.Combine(project, "dialogos", "memory", "memoria.json"), dialogues);
        SaveMemory(missionsPath, missions);
    }

    private static Dictionary<string, string> LoadMemory(string path) => JsonSerializer.Deserialize<Dictionary<string, string>>(File.ReadAllText(path), JsonOptions) ?? [];
    private static void SaveMemory(string path, Dictionary<string, string> memory) => File.WriteAllText(path, JsonSerializer.Serialize(memory, new JsonSerializerOptions(JsonOptions) { WriteIndented = true }) + Environment.NewLine);
    private static int CountMissing(string path) => JsonSerializer.Deserialize<PipelineReport>(File.ReadAllText(path), JsonOptions)?.Flows.Sum(flow => flow.Missing.Count) ?? 0;
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNameCaseInsensitive = true };
    private static readonly Regex ProtectedToken = new(@"(\r\n|\r|\n|\[lua\(.*?\)\]|\[[^\]]+\]|<[^>]+>|\{[^{}]+\})", RegexOptions.Singleline);
    private static string EscapeUnity(string value) => value.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "\\r").Replace("\n", "\\n").Replace("\t", "\\t");
    private static async Task<string> TranslateAsync(HttpClient client, string source)
    {
        var tokens = new List<string>();
        var protectedText = ProtectedToken.Replace(source, match => { tokens.Add(match.Value); return $"LW_TOKEN_{tokens.Count - 1}_END"; });
        var url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=pt&dt=t&q=" + Uri.EscapeDataString(protectedText);
        var json = await client.GetStringAsync(url);
        using var document = JsonDocument.Parse(json);
        var translated = string.Concat(document.RootElement[0].EnumerateArray().Select(part => part[0].GetString()));
        if (string.IsNullOrWhiteSpace(translated)) throw new InvalidOperationException("O serviço de tradução não retornou texto.");
        for (var index = 0; index < tokens.Count; index++)
        {
            var marker = $"LW_TOKEN_{index}_END";
            if (!translated.Contains(marker, StringComparison.Ordinal)) throw new InvalidOperationException("O serviço de tradução alterou uma marcação do jogo.");
            translated = translated.Replace(marker, tokens[index], StringComparison.Ordinal);
        }
        return translated;
    }

    private State? ReadState()
    {
        try { var path = Path.Combine(root, "estado.json"); return File.Exists(path) ? JsonSerializer.Deserialize<State>(File.ReadAllText(path)) : null; }
        catch (JsonException) { return null; }
    }
    private void WriteState(State value) => File.WriteAllText(Path.Combine(root, "estado.json"), JsonSerializer.Serialize(value));
    private static string? FindGame(string? saved)
    {
        var paths = new List<string?> { saved, @"C:\Program Files (x86)\Steam\steamapps\common\Little Witch in the Woods" };
        try { using var key = Microsoft.Win32.Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"); paths.Add(Path.Combine(key?.GetValue("SteamPath")?.ToString() ?? string.Empty, "steamapps", "common", "Little Witch in the Woods")); } catch (IOException) { }
        return paths.FirstOrDefault(path => !string.IsNullOrWhiteSpace(path) && File.Exists(Path.Combine(path, "Little Witch in the Woods.exe")));
    }
    private static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));

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
internal sealed record State(string GamePath, string SourceSha256, string TranslatedSha256, DateTimeOffset UpdatedAt);
internal sealed record MissingItem(string Source);
internal sealed record PipelineFlow(string Flow, List<MissingItem> Missing);
internal sealed record PipelineReport(List<PipelineFlow> Flows);
internal sealed record TranslationJob(string Flow, string Source);
internal enum TranslationMode { KeepEnglish, Automatic, Cancel }
