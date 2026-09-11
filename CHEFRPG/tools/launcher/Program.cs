using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;

ApplicationConfiguration.Initialize();
Application.Run(new LauncherForm());

internal sealed class LauncherForm : Form
{
    private readonly Button playButton = new() { Text = "Atualizar e jogar", AutoSize = false, Size = new Size(210, 42) };
    private readonly Label status = new() { AutoSize = false, Height = 48, TextAlign = ContentAlignment.MiddleLeft };
    private readonly string root = AppContext.BaseDirectory;

    public LauncherForm()
    {
        Text = "Chef RPG — Tradução PT-BR";
        ClientSize = new Size(760, 470);
        MinimumSize = new Size(760, 470);
        MaximumSize = new Size(760, 470);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(38, 28, 38);
        Font = new Font("Segoe UI", 10);

        var heroPath = Path.Combine(root, "assets", "hero.png");
        if (File.Exists(heroPath))
        {
            var hero = new PictureBox
            {
                Image = Image.FromFile(heroPath),
                SizeMode = PictureBoxSizeMode.Zoom,
                Dock = DockStyle.Top,
                Height = 300
            };
            Controls.Add(hero);
        }

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

        playButton.BackColor = Color.FromArgb(196, 106, 82);
        playButton.ForeColor = Color.White;
        playButton.FlatStyle = FlatStyle.Flat;
        playButton.FlatAppearance.BorderSize = 0;
        playButton.Location = new Point(522, 366);
        playButton.Click += async (_, _) => await UpdateAndPlayAsync();
        Controls.Add(playButton);
    }

    private async Task UpdateAndPlayAsync()
    {
        try
        {
            playButton.Enabled = false;
            status.Text = "Localizando o jogo...";
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

            var currentHash = Sha256(gameAsset);
            if (state?.TranslatedSha256 != currentHash)
            {
                status.Text = "Atualização detectada. Reconstruindo a tradução...";
                var pipeline = Path.Combine(root, "bin", "ChefRpg.AssetPipeline.exe");
                var classData = Path.Combine(root, "bin", "classdata.tpk");
                var memory = Path.Combine(root, "memoria.json");
                var staging = Path.Combine(root, "staging");
                if (!File.Exists(pipeline) || !File.Exists(classData) || !File.Exists(memory))
                    throw new InvalidOperationException("O pacote está incompleto. Extraia o ZIP inteiro antes de usar.");

                await RunPipeline(pipeline, "build-fallback", gamePath, root, classData, staging);
                status.Text = "Validando os arquivos...";
                await RunPipeline(pipeline, "verify", gamePath, root, classData, staging);

                var rebuiltAsset = Path.Combine(staging, "resources.assets");
                if (!File.Exists(rebuiltAsset))
                    throw new InvalidOperationException("O arquivo traduzido não foi gerado.");
                var backup = Path.Combine(root, "backups", DateTime.Now.ToString("yyyyMMdd-HHmmss"));
                Directory.CreateDirectory(backup);
                File.Copy(gameAsset, Path.Combine(backup, "resources.assets"), true);
                try
                {
                    File.Copy(rebuiltAsset, gameAsset, true);
                }
                catch
                {
                    File.Copy(Path.Combine(backup, "resources.assets"), gameAsset, true);
                    throw;
                }
                WriteState(new LauncherState(gamePath, currentHash, Sha256(gameAsset), DateTimeOffset.UtcNow));
                status.Text = "Tradução atualizada. Abrindo o jogo...";
            }
            else
            {
                status.Text = "Tradução já está atualizada. Abrindo o jogo...";
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
            playButton.Enabled = true;
        }
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
        var output = await process.StandardOutput.ReadToEndAsync();
        var error = await process.StandardError.ReadToEndAsync();
        await process.WaitForExitAsync();
        if (process.ExitCode is not (0 or 3))
            throw new InvalidOperationException(string.IsNullOrWhiteSpace(error) ? output : error);
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
}

internal sealed record LauncherState(string GamePath, string SourceSha256, string TranslatedSha256, DateTimeOffset UpdatedAt);
