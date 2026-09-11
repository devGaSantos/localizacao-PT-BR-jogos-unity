using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

ApplicationConfiguration.Initialize();
Application.Run(new LauncherForm());

internal sealed class LauncherForm : Form
{
    private readonly string root = AppContext.BaseDirectory;
    private readonly Label status = new() { AutoSize = false, Height = 46, TextAlign = ContentAlignment.MiddleLeft };
    private readonly Button play = new() { Text = "Atualizar e jogar", Size = new Size(210, 42), FlatStyle = FlatStyle.Flat };

    public LauncherForm()
    {
        Text = "Little Witch in the Woods — Tradução PT-BR";
        ClientSize = new Size(760, 470);
        MinimumSize = MaximumSize = Size;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(30, 22, 37);
        var heroPath = Path.Combine(root, "assets", "hero.png");
        if (File.Exists(heroPath))
            Controls.Add(new PictureBox { Image = Image.FromFile(heroPath), SizeMode = PictureBoxSizeMode.Zoom, Dock = DockStyle.Top, Height = 300 });
        Controls.Add(new Label { Text = "LITTLE WITCH IN THE WOODS  •  TRADUÇÃO PT-BR", ForeColor = Color.FromArgb(229, 204, 255), Font = new Font("Segoe UI Semibold", 14), Location = new Point(25, 318), AutoSize = true });
        status.Text = "Pronto para verificar a tradução.";
        status.ForeColor = Color.White;
        status.Location = new Point(25, 352);
        status.Width = 475;
        Controls.Add(status);
        play.BackColor = Color.FromArgb(116, 75, 161);
        play.ForeColor = Color.White;
        play.FlatAppearance.BorderSize = 0;
        play.Location = new Point(522, 366);
        play.Click += async (_, _) => await UpdateAndPlayAsync();
        Controls.Add(play);
    }

    private async Task UpdateAndPlayAsync()
    {
        try
        {
            play.Enabled = false;
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
            var before = Hash(resources);
            if (state?.TranslatedSha256 != before)
            {
                status.Text = "Atualização detectada. Reconstruindo a tradução...";
                var pipeline = Path.Combine(root, "bin", "LittleWitch.AssetPipeline.exe");
                var project = Path.Combine(root, "LW");
                var classData = Path.Combine(root, "bin", "classdata.tpk");
                var staging = Path.Combine(root, "staging");
                await Run(pipeline, "build-fallback", game, project, classData, staging);
                status.Text = "Validando os arquivos...";
                await Run(pipeline, "verify", game, project, classData, staging);
                var targets = new[]
                {
                    "localization-string-tables-english(en)_assets_all.bundle",
                    "dialoguedb_assets_all.bundle", "defaultlocalgroup_assets_all.bundle", "resources.assets"
                };
                var backup = Path.Combine(root, "backups", DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.CreateDirectory(backup);
                foreach (var name in targets)
                {
                    var destination = name == "resources.assets" ? resources : Path.Combine(data, "StreamingAssets", "aa", "StandaloneWindows64", name);
                    var source = Path.Combine(staging, name);
                    if (!File.Exists(source)) throw new InvalidOperationException($"Asset não gerado: {name}");
                    File.Copy(destination, Path.Combine(backup, name), true);
                    File.Copy(source, destination, true);
                }
                WriteState(new State(game, before, Hash(resources), DateTimeOffset.UtcNow));
                status.Text = "Tradução atualizada. Abrindo o jogo...";
            }
            else status.Text = "Tradução já está atualizada. Abrindo o jogo...";
            Process.Start(new ProcessStartInfo(exe) { WorkingDirectory = game, UseShellExecute = true });
            Close();
        }
        catch (Exception error)
        {
            status.Text = "Não foi possível atualizar a tradução.";
            MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally { play.Enabled = true; }
    }

    private static async Task Run(string executable, params string[] arguments)
    {
        if (!File.Exists(executable)) throw new InvalidOperationException("Atualizador incompleto. Extraia todo o ZIP.");
        var info = new ProcessStartInfo(executable) { UseShellExecute = false, RedirectStandardError = true, RedirectStandardOutput = true, CreateNoWindow = true };
        foreach (var argument in arguments) info.ArgumentList.Add(argument);
        using var process = Process.Start(info) ?? throw new InvalidOperationException("Não foi possível iniciar o atualizador.");
        var stdout = await process.StandardOutput.ReadToEndAsync();
        var stderr = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode is not (0 or 3)) throw new InvalidOperationException(string.IsNullOrWhiteSpace(stderr) ? stdout : stderr);
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
}
internal sealed record State(string GamePath, string SourceSha256, string TranslatedSha256, DateTimeOffset UpdatedAt);
