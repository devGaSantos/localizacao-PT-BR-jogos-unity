Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Raiz = $PSScriptRoot
$recoveredDotnet = Join-Path (Split-Path -Parent $Raiz) "LW\.tools\dotnet-recovered\dotnet.exe"
$dotnet = Get-Command dotnet -ErrorAction SilentlyContinue
$dotnetPath = if (Test-Path -LiteralPath $recoveredDotnet) {
    $recoveredDotnet
} elseif ($dotnet) {
    $dotnet.Source
} else {
    $null
}
if (-not (Test-Path -LiteralPath $dotnetPath)) { throw "O .NET SDK e necessario apenas para publicar o pacote." }

$destino = Join-Path $Raiz "dist\Chef_RPG_PT-BR_AutoUpdater"
if (Test-Path -LiteralPath $destino) { Remove-Item -LiteralPath $destino -Recurse -Force }
New-Item -ItemType Directory -Path $destino -Force | Out-Null
$payload = Join-Path $Raiz "tools\launcher\payload"
if (Test-Path -LiteralPath $payload) { Remove-Item -LiteralPath $payload -Recurse -Force }
New-Item -ItemType Directory -Path (Join-Path $payload "bin") -Force | Out-Null

& $dotnetPath publish (Join-Path $Raiz "tools\asset-pipeline\ChefRpg.AssetPipeline.csproj") `
    --configuration Release --runtime win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
    --output (Join-Path $payload "bin")
if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar o atualizador." }

Copy-Item -LiteralPath (Join-Path $Raiz "tools\asset-pipeline\lib\classdata.tpk") -Destination (Join-Path $payload "bin\classdata.tpk") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "memoria.json") -Destination (Join-Path $payload "memoria.json") -Force
Set-Content -LiteralPath (Join-Path $payload "version.txt") -Value ("chef-" + (Get-Date -Format "yyyyMMddHHmmss")) -Encoding utf8

& $dotnetPath publish (Join-Path $Raiz "tools\launcher\ChefRpg.Launcher.csproj") `
    --configuration Release --runtime win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
    --output $destino
if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar a interface do atualizador." }

Get-ChildItem -LiteralPath $destino -Force | Where-Object { $_.Name -ne "ChefRpg.Launcher.exe" } | Remove-Item -Force -Recurse

$zip = Join-Path $Raiz "dist\Chef_RPG_PT-BR_AutoUpdater.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $destino -DestinationPath $zip -Force
Write-Host "Pacote Nexus pronto: $zip"

$manual = Join-Path $Raiz "dist\Chef_RPG_PT-BR_Instalacao_Manual"
if (Test-Path -LiteralPath $manual) { Remove-Item -LiteralPath $manual -Recurse -Force }
$manualData = Join-Path $manual "Chef RPG_Data"
New-Item -ItemType Directory -Path $manualData -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Raiz "atualizacao\staging\resources.assets") -Destination (Join-Path $manualData "resources.assets") -Force
@'
INSTALACAO MANUAL — CHEF RPG PT-BR

Feche o jogo e a Steam. Copie TODO o conteudo desta pasta para a pasta raiz do jogo
(a que contem Chef RPG_Data) e confirme a substituicao. Este arquivo so vale para a
versao atual do jogo usada nesta publicacao. Depois de uma atualizacao da Steam,
nao reutilize este ZIP: baixe uma nova versao ou use o Launcher.exe.

Para desfazer, use "Verificar integridade dos arquivos" na Steam.
'@ | Set-Content -LiteralPath (Join-Path $manual "LEIA-ME - INSTALACAO MANUAL.txt") -Encoding utf8
$manualZip = Join-Path $Raiz "dist\Chef_RPG_PT-BR_Instalacao_Manual.zip"
if (Test-Path -LiteralPath $manualZip) { Remove-Item -LiteralPath $manualZip -Force }
Compress-Archive -Path $manual -DestinationPath $manualZip -Force
Write-Host "Pacote manual pronto: $manualZip"
