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

@'
LITTLE WITCH IN THE WOODS — TRADUCAO PT-BR

1. Extraia esta pasta em um local permanente.
2. Abra LittleWitch.Launcher.exe sempre que for jogar.
3. Caso a Steam esteja em outra biblioteca, selecione a pasta do jogo uma vez.

Depois de uma atualizacao da Steam, o launcher reconstrói e reinstala a traducao
automaticamente. Nao requer UABEA, .NET ou Python instalados.

Textos novos que ainda nao existam na memoria da traducao permanecem em ingles ate a
proxima versao revisada do mod. O restante continua traduzido.
'@ | Set-Content -LiteralPath (Join-Path $destination "LEIA-ME.txt") -Encoding utf8

$zip = Join-Path $Raiz "dist\Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $destination -DestinationPath $zip -Force
Write-Host "Pacote Nexus pronto: $zip"
