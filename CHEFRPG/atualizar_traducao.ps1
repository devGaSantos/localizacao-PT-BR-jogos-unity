param(
    [ValidateSet("status", "analisar", "automatico", "pacote", "instalar")]
    [string]$Etapa = "status",
    [string]$Jogo = "C:\Program Files (x86)\Steam\steamapps\common\Chef RPG",
    [switch]$ConfirmarInstalacao
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Raiz = $PSScriptRoot
$GameData = Join-Path $Jogo "Chef RPG_Data"
$ResourcesJogo = Join-Path $GameData "resources.assets"
$Staging = Join-Path $Raiz "atualizacao\staging"
$PacoteMerlin = Join-Path $Raiz "atualizacao\pacote_merlin"
$SharedTools = Join-Path (Split-Path -Parent $Raiz) "LW\.tools"
$LocalClassData = Join-Path $Raiz ".tools\uabea\classdata.tpk"
$BundledClassData = Join-Path $Raiz "tools\asset-pipeline\lib\classdata.tpk"
$SharedClassData = Join-Path $SharedTools "uabea\classdata.tpk"
$ClassData = if (Test-Path -LiteralPath $BundledClassData) {
    $BundledClassData
} elseif (Test-Path -LiteralPath $LocalClassData) {
    $LocalClassData
} else {
    $SharedClassData
}
$Project = Join-Path $Raiz "tools\asset-pipeline\ChefRpg.AssetPipeline.csproj"
$ProjectAssets = Join-Path $Raiz "tools\asset-pipeline\obj\project.assets.json"
$PipelineDll = Join-Path $Raiz "tools\asset-pipeline\bin\Release\net8.0\ChefRpg.AssetPipeline.dll"
$MissingTranslator = Join-Path $Raiz "traduzir_faltantes.py"
$SceneUiPatcher = Join-Path $Raiz "patch_scene_ui.py"

function Resolve-DotNetSdk {
    $local = Join-Path $Raiz ".tools\dotnet\dotnet.exe"
    if (Test-Path -LiteralPath $local) { return $local }
    $recovered = Join-Path $SharedTools "dotnet-recovered\dotnet.exe"
    if (Test-Path -LiteralPath $recovered) { return $recovered }
    $shared = Join-Path $SharedTools "dotnet\dotnet.exe"
    if (Test-Path -LiteralPath $shared) { return $shared }
    $command = Get-Command dotnet -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    throw "SDK do .NET nao encontrado. Execute .\preparar_pipeline_assets.ps1 uma vez."
}

function Invoke-Checked([string]$Executable, [string[]]$Arguments) {
    & $Executable @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Comando falhou ($LASTEXITCODE): $Executable $($Arguments -join ' ')"
    }
}

function Initialize-Pipeline {
    if (-not (Test-Path -LiteralPath $ClassData)) {
        throw "classdata.tpk nao encontrado. Execute .\preparar_pipeline_assets.ps1 uma vez."
    }
    $dotnet = Resolve-DotNetSdk
    if (-not (Test-Path -LiteralPath $ProjectAssets)) {
        $nuget = Join-Path $Raiz "tools\asset-pipeline\NuGet.Config"
        Invoke-Checked $dotnet @("restore", $Project, "--configfile", $nuget)
    }
    Invoke-Checked $dotnet @("build", $Project, "--configuration", "Release", "--no-restore")
    $bundledAssetsTools = Join-Path $Raiz "tools\asset-pipeline\lib\AssetsTools.NET.dll"
    $runtimeAssetsTools = Join-Path $Raiz "tools\asset-pipeline\bin\Release\net8.0\AssetsTools.NET.dll"
    if (Test-Path -LiteralPath $bundledAssetsTools) {
        Copy-Item -LiteralPath $bundledAssetsTools -Destination $runtimeAssetsTools -Force
    }
}

function Invoke-Pipeline([string]$Mode, [switch]$AllowMissing) {
    $dotnet = Resolve-DotNetSdk
    & $dotnet $PipelineDll $Mode $Jogo $Raiz $ClassData $Staging | Out-Host
    $exitCode = $LASTEXITCODE
    if ($exitCode -eq 3 -and $AllowMissing) { return $false }
    if ($exitCode -ne 0) { throw "Pipeline de assets falhou com codigo $exitCode." }
    return $true
}

function Show-Status {
    if (-not (Test-Path -LiteralPath $ResourcesJogo)) {
        throw "resources.assets nao encontrado: $ResourcesJogo"
    }
    $file = Get-Item -LiteralPath $ResourcesJogo
    [pscustomobject]@{
        jogo = $Jogo
        arquivo = $ResourcesJogo
        bytes = $file.Length
        modificadoUtc = $file.LastWriteTimeUtc.ToString("o")
        sha256 = (Get-FileHash -LiteralPath $ResourcesJogo -Algorithm SHA256).Hash
    } | Format-List | Out-Host
}

function Analyze-CurrentGame {
    Initialize-Pipeline
    $ready = Invoke-Pipeline "scan" -AllowMissing
    Write-Host "Relatorio completo: $Raiz\relatorios\chef_rpg_pipeline.json"
    Write-Host "Memoria dos faltantes: $Raiz\relatorios\faltantes_memoria.json"
    if (-not $ready) {
        Write-Warning "Existem textos sem traducao. Preencha-os em memoria.json antes de gerar o pacote."
    }
}

function Update-MissingTranslations {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python -or $python.Source -match '\\WindowsApps\\') {
        $fallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        if (Test-Path -LiteralPath $fallback) { $python = Get-Item $fallback }
    }
    if (-not $python) { throw "Python nao encontrado para traduzir os faltantes." }
    if (-not (Test-Path -LiteralPath $MissingTranslator)) {
        throw "Tradutor de faltantes nao encontrado: $MissingTranslator"
    }
    $pythonPath = if ($python -is [System.IO.FileInfo]) { $python.FullName } else { $python.Source }
    Invoke-Checked $pythonPath @(
        $MissingTranslator,
        "--report", (Join-Path $Raiz "relatorios\chef_rpg_pipeline.json"),
        "--memory", (Join-Path $Raiz "memoria.json")
    )
}

function Resolve-Python {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python -or $python.Source -match '\\WindowsApps\\') {
        $fallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
        if (Test-Path -LiteralPath $fallback) { $python = Get-Item $fallback }
    }
    if (-not $python) { throw "Python nao encontrado." }
    if ($python -is [System.IO.FileInfo]) { return $python.FullName }
    return $python.Source
}

function Patch-SceneUi {
    if (-not (Test-Path -LiteralPath $SceneUiPatcher)) {
        throw "Patcher de cenas nao encontrado: $SceneUiPatcher"
    }
    $pythonPath = Resolve-Python
    Invoke-Checked $pythonPath @(
        $SceneUiPatcher,
        "--game-data", $GameData,
        "--output", $Staging,
        "--report", (Join-Path $Raiz "relatorios\chef_rpg_scene_ui.json")
    )
}

function Get-RequiredPackageFiles {
    # A traducao publicada usa somente as cinco tabelas dentro de resources.assets.
    # Os level* sao uma experiencia separada de UI e nao podem entrar no pacote
    # automaticamente: a substituicao binaria ampla ja causou telas em branco.
    return @("resources.assets")
}

function Export-MerlinPackage {
    $destinationDirectory = Join-Path $PacoteMerlin "Chef RPG_Data"
    $required = Get-RequiredPackageFiles
    foreach ($file in $required) {
        $source = Join-Path $Staging $file
        if (-not (Test-Path -LiteralPath $source)) { throw "Staging validado nao encontrado: $source" }
    }
    if (Test-Path -LiteralPath $destinationDirectory) {
        Remove-Item -LiteralPath $destinationDirectory -Recurse -Force
    }
    New-Item -ItemType Directory -Path $destinationDirectory -Force | Out-Null
    foreach ($file in $required) {
        $source = Join-Path $Staging $file
        $destination = Join-Path $destinationDirectory $file
        Copy-Item -LiteralPath $source -Destination $destination -Force
        if ((Get-FileHash $source -Algorithm SHA256).Hash -ne (Get-FileHash $destination -Algorithm SHA256).Hash) {
            throw "O arquivo $file do pacote nao corresponde ao staging."
        }
    }
    Write-Host "PACOTE MERLIN PRONTO: $PacoteMerlin"
    Write-Host "Arraste Chef RPG_Data para a raiz do jogo e confirme a substituicao."
}

function Build-AutomaticPackage {
    Initialize-Pipeline
    Write-Host "`n[1/3] Analisando as cinco tabelas e a memoria"
    if (-not (Invoke-Pipeline "scan" -AllowMissing)) {
        Write-Host "Textos novos encontrados. Traduzindo e atualizando memoria.json..."
        Update-MissingTranslations
        Write-Host "`n[1/3] Reanalisando depois da traducao automatica"
        if (-not (Invoke-Pipeline "scan" -AllowMissing)) {
            throw "Ainda existem textos sem traducao. Consulte relatorios\faltantes_memoria.json."
        }
    }
    Write-Host "`n[2/3] Reconstruindo resources.assets no staging"
    Invoke-Pipeline "build" | Out-Null
    Write-Host "`n[3/3] Reabrindo e validando o asset reconstruido"
    Invoke-Pipeline "verify" | Out-Null
    Export-MerlinPackage
    Write-Host "O jogo ainda nao foi modificado."
}

function Build-PackageFromStaging {
    Initialize-Pipeline
    Invoke-Pipeline "verify" | Out-Null
    Export-MerlinPackage
}

function Install-Package {
    if (-not $ConfirmarInstalacao) {
        throw "Instalacao cancelada. Repita com -Etapa instalar -ConfirmarInstalacao."
    }
    if (Get-Process -Name "Chef RPG" -ErrorAction SilentlyContinue) {
        throw "Feche Chef RPG antes de instalar a traducao."
    }
    Initialize-Pipeline
    Invoke-Pipeline "verify" | Out-Null
    $required = Get-RequiredPackageFiles
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = Join-Path $Raiz "atualizacao\backups\$timestamp"
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($file in $required) {
        Copy-Item -LiteralPath (Join-Path $GameData $file) -Destination (Join-Path $backup $file) -Force
    }
    try {
        foreach ($file in $required) {
            Copy-Item -LiteralPath (Join-Path $Staging $file) -Destination (Join-Path $GameData $file) -Force
        }
    } catch {
        foreach ($file in $required) {
            Copy-Item -LiteralPath (Join-Path $backup $file) -Destination (Join-Path $GameData $file) -Force
        }
        throw "Instalacao falhou e o backup foi restaurado: $($_.Exception.Message)"
    }
    Write-Host "Traducao instalada. Backup original: $backup"
}

switch ($Etapa) {
    "status" { Show-Status }
    "analisar" { Analyze-CurrentGame }
    "automatico" { Build-AutomaticPackage }
    "pacote" { Build-PackageFromStaging }
    "instalar" { Install-Package }
}
