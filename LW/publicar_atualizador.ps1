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

function Publish-Standalone([string]$Project, [string]$Output) {
    & $dotnet publish $Project --configuration Release --runtime win-x64 --self-contained true `
        -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true --output $Output
    if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar: $Project" }
}

Publish-Standalone (Join-Path $Raiz "tools\asset-pipeline\LittleWitch.AssetPipeline.csproj") (Join-Path $destination "bin")
Publish-Standalone (Join-Path $Raiz "tools\launcher\LittleWitch.Launcher.csproj") $destination

New-Item -ItemType Directory -Path (Join-Path $destination "assets"), (Join-Path $destination "LW\dialogos\memory"), (Join-Path $destination "missoes") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Raiz ".tools\uabea\classdata.tpk") -Destination (Join-Path $destination "bin\classdata.tpk") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "tools\launcher\assets\hero.png") -Destination (Join-Path $destination "assets\hero.png") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "memoria_revisado.json") -Destination (Join-Path $destination "LW\memoria_revisado.json") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "dialogos\memory\memoria.json") -Destination (Join-Path $destination "LW\dialogos\memory\memoria.json") -Force
Copy-Item -LiteralPath (Join-Path $Projeto "missoes\memoria_missoes.json") -Destination (Join-Path $destination "missoes\memoria_missoes.json") -Force

# Alternativa transparente para quem prefere nao executar o launcher. Estes sao os
# mesmos assets PT-BR gerados para a versao atual do jogo no momento da publicacao.
$manualData = Join-Path $destination "INSTALACAO_MANUAL\LWIW_Data"
$manualBundles = Join-Path $manualData "StreamingAssets\aa\StandaloneWindows64"
New-Item -ItemType Directory -Path $manualBundles -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Raiz "atualizacao\staging\resources.assets") -Destination (Join-Path $manualData "resources.assets") -Force
foreach ($bundle in @(
    "localization-string-tables-english(en)_assets_all.bundle",
    "dialoguedb_assets_all.bundle",
    "defaultlocalgroup_assets_all.bundle")) {
    Copy-Item -LiteralPath (Join-Path $Raiz "atualizacao\staging\$bundle") -Destination (Join-Path $manualBundles $bundle) -Force
}

@'
LITTLE WITCH IN THE WOODS — TRADUCAO PT-BR

OPCAO RECOMENDADA — LAUNCHER.EXE

1. Extraia esta pasta em um local permanente.
2. Abra LittleWitch.Launcher.exe sempre que for jogar.
3. Caso a Steam esteja em outra biblioteca, selecione a pasta do jogo uma vez.

O EXE E SEGURO PARA INSPECAO: ele nao baixa mod pronto nem altera arquivos sem
antes ler a instalacao local. Ele detecta atualizacoes, recria os assets PT-BR
localmente e guarda uma copia original em backups. Nao requer UABEA, .NET ou
Python instalados.

Depois de uma atualizacao da Steam, o launcher reconstrói e reinstala a traducao
automaticamente.

OPCAO SEM EXE — INSTALACAO_MANUAL

Feche o jogo e a Steam. Copie TODO o conteudo da pasta INSTALACAO_MANUAL para a
pasta raiz do jogo (a que contem LWIW_Data) e confirme a substituicao. Esta opcao
e apenas para a versao atual do jogo incluida neste ZIP: apos uma atualizacao da
Steam, nao reutilize esses arquivos; use o launcher ou aguarde o proximo pacote.

Se a Steam adicionar textos ainda sem traducao revisada, o launcher mostra a
quantidade e permite manter esses textos em ingles ate a proxima versao oficial ou
tentar traduzi-los automaticamente. A segunda opcao usa internet, mostra
progresso/estimativa e pode levar alguns minutos. Ela e somente um ganha-tempo:
a traducao oficial revisada continua sendo publicada depois. O projeto e mantido
junto com outros projetos pessoais, entao essa escolha evita deixar novos textos
sem cobertura enquanto a revisao manual nao chega.

MANTER EM INGLES: aplica a traducao revisada ja existente e deixa somente os
textos novos em ingles. Nao usa internet e e a opcao mais fiel ate a revisao.

TRADUZIR AUTOMATICAMENTE: usa internet somente apos sua confirmacao, preserva
tags/codigos do jogo e grava o resultado localmente para reutilizar depois. Pode
soar menos natural; a versao oficial substituira essas frases quando revisadas.

Para voltar ao original, use "Verificar integridade dos arquivos" na Steam.
'@ | Set-Content -LiteralPath (Join-Path $destination "LEIA-ME.txt") -Encoding utf8

@'
INSTALACAO MANUAL — LITTLE WITCH IN THE WOODS PT-BR

1. Feche o jogo e a Steam.
2. Abra a pasta do jogo pela Steam: Gerenciar > Procurar arquivos locais.
3. Copie o CONTEUDO desta pasta para a pasta raiz do jogo.
4. Confirme a substituicao de LWIW_Data\resources.assets e dos tres bundles.

Estes arquivos foram gerados para a versao do jogo usada nesta publicacao. Depois
de atualizar o jogo pela Steam, NAO os copie de novo: prefira LittleWitch.Launcher.exe
ou aguarde uma nova versao oficial da traducao.

Para desfazer, use "Verificar integridade dos arquivos" na Steam.
'@ | Set-Content -LiteralPath (Join-Path $destination "INSTALACAO_MANUAL\LEIA-ME - INSTALACAO MANUAL.txt") -Encoding utf8

$zip = Join-Path $Raiz "dist\Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $destination -DestinationPath $zip -Force
Write-Host "Pacote Nexus pronto: $zip"
