Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Raiz = $PSScriptRoot
$Projeto = Split-Path -Parent $Raiz
$dotnet = Join-Path $Raiz ".tools\dotnet-recovered\dotnet.exe"
if (-not (Test-Path -LiteralPath $dotnet)) { $dotnet = Join-Path $Raiz ".tools\dotnet\dotnet.exe" }
if (-not (Test-Path -LiteralPath $dotnet)) { throw "O .NET SDK e necessario apenas para publicar o pacote." }

$destination = Join-Path $Raiz "dist\Little_Witch_in_the_Woods_PT-BR_AutoUpdater"
if (Test-Path -LiteralPath $destination) { Remove-Item -LiteralPath $destination -Recurse -Force }
New-Item -ItemType Directory -Path $destination -Force | Out-Null
$launcher = Join-Path $destination "ATUALIZADOR"
New-Item -ItemType Directory -Path (Join-Path $launcher "bin"), (Join-Path $launcher "LW\dialogos\memory"), (Join-Path $launcher "missoes"), (Join-Path $launcher "assets") -Force | Out-Null

function Publish-Standalone([string]$Project, [string]$Output) {
    & $dotnet publish $Project --configuration Release --runtime win-x64 --self-contained true `
        -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true --output $Output
    if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar: $Project" }
}

Publish-Standalone (Join-Path $Raiz "tools\asset-pipeline\LittleWitch.AssetPipeline.csproj") (Join-Path $launcher "bin")
Copy-Item -LiteralPath (Join-Path $Raiz ".tools\uabea\classdata.tpk") -Destination (Join-Path $launcher "bin\classdata.tpk") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "tools\launcher\assets\hero.png") -Destination (Join-Path $launcher "assets\hero.png") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "memoria_revisado.json") -Destination (Join-Path $launcher "LW\memoria_revisado.json") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "dialogos\memory\memoria.json") -Destination (Join-Path $launcher "LW\dialogos\memory\memoria.json") -Force
Copy-Item -LiteralPath (Join-Path $Projeto "missoes\memoria_missoes.json") -Destination (Join-Path $launcher "missoes\memoria_missoes.json") -Force
Publish-Standalone (Join-Path $Raiz "tools\launcher\LittleWitch.Launcher.csproj") $launcher
Remove-Item -LiteralPath (Join-Path $launcher "LittleWitch.Launcher.pdb") -Force -ErrorAction SilentlyContinue

$manual = Join-Path $destination "INSTALACAO_MANUAL"
$manualBundles = Join-Path $manual "LWIW_Data\StreamingAssets\aa\StandaloneWindows64"
New-Item -ItemType Directory -Path $manualBundles -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Raiz "atualizacao\staging\resources.assets") -Destination (Join-Path $manual "LWIW_Data\resources.assets") -Force
foreach ($bundle in @("localization-string-tables-english(en)_assets_all.bundle", "dialoguedb_assets_all.bundle", "defaultlocalgroup_assets_all.bundle")) {
    Copy-Item -LiteralPath (Join-Path $Raiz "atualizacao\staging\$bundle") -Destination (Join-Path $manualBundles $bundle) -Force
}
@'
INSTALACAO MANUAL — LITTLE WITCH IN THE WOODS PT-BR

Feche o jogo e a Steam. Copie TODO o conteudo desta pasta para a pasta raiz do jogo
(a que contem LWIW_Data) e confirme a substituicao. Estes arquivos so valem para a
versao atual do jogo usada nesta publicacao. Depois de uma atualizacao da Steam,
nao reutilize este ZIP: baixe uma nova versao ou use o Launcher.exe.

Para desfazer, use "Verificar integridade dos arquivos" na Steam.
'@ | Set-Content -LiteralPath (Join-Path $manual "LEIA-ME - INSTALACAO MANUAL.txt") -Encoding utf8
@'
LITTLE WITCH IN THE WOODS — TRADUCAO PT-BR

Este ZIP oferece duas formas de instalar:

1. RECOMENDADO: abra ATUALIZADOR\LittleWitch.Launcher.exe. Mantenha todos os
   arquivos dessa pasta juntos; ele mostra imagem/loading, cria backup e se adapta
   a atualizacoes do jogo.
2. SEM EXE: leia INSTALACAO_MANUAL\LEIA-ME - INSTALACAO MANUAL.txt e copie os
   arquivos dessa pasta para o jogo. Ela vale somente para a versao atual.

Quando surgirem textos novos, o launcher oferece manter em ingles (mais fiel ate
a revisao) ou traducao automatica provisoria, com progresso e estimativa. A opcao
automatica usa internet somente depois da sua confirmacao.
'@ | Set-Content -LiteralPath (Join-Path $destination "LEIA-ME.txt") -Encoding utf8
Get-ChildItem -LiteralPath $destination -Filter "*.pdb" -File -Recurse | Remove-Item -Force
$zip = Join-Path $Raiz "dist\Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $destination -DestinationPath $zip -Force
Write-Host "Pacote Nexus pronto: $zip"
