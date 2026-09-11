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

& $dotnetPath publish (Join-Path $Raiz "tools\asset-pipeline\ChefRpg.AssetPipeline.csproj") `
    --configuration Release --runtime win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
    --output (Join-Path $destino "bin")
if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar o atualizador." }

& $dotnetPath publish (Join-Path $Raiz "tools\launcher\ChefRpg.Launcher.csproj") `
    --configuration Release --runtime win-x64 --self-contained true `
    -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true `
    --output $destino
if ($LASTEXITCODE -ne 0) { throw "Falha ao publicar a interface do atualizador." }

Copy-Item -LiteralPath (Join-Path $Raiz "tools\asset-pipeline\lib\classdata.tpk") -Destination (Join-Path $destino "bin\classdata.tpk") -Force
New-Item -ItemType Directory -Path (Join-Path $destino "assets") -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $Raiz "tools\launcher\assets\hero.png") -Destination (Join-Path $destino "assets\hero.png") -Force
Copy-Item -LiteralPath (Join-Path $Raiz "memoria.json") -Destination (Join-Path $destino "memoria.json") -Force
Copy-Item -Path (Join-Path $Raiz "publico\*") -Destination $destino -Recurse -Force

$zip = Join-Path $Raiz "dist\Chef_RPG_PT-BR_AutoUpdater.zip"
if (Test-Path -LiteralPath $zip) { Remove-Item -LiteralPath $zip -Force }
Compress-Archive -Path $destino -DestinationPath $zip -Force
Write-Host "Pacote Nexus pronto: $zip"
