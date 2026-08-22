param(
    [string]$UabeaZip = (Join-Path $env:USERPROFILE "Downloads\uabea-windows.zip")
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$tools = Join-Path $PSScriptRoot ".tools"
$dotnetDirectory = Join-Path $tools "dotnet"
$dotnet = Join-Path $dotnetDirectory "dotnet.exe"
$classDataDirectory = Join-Path $tools "uabea"
$classData = Join-Path $classDataDirectory "classdata.tpk"
New-Item -ItemType Directory -Path $tools -Force | Out-Null

if (-not (Test-Path -LiteralPath $dotnet)) {
    $installer = Join-Path $tools "dotnet-install.ps1"
    Invoke-WebRequest "https://dot.net/v1/dotnet-install.ps1" -OutFile $installer
    & $installer -Channel "8.0" -InstallDir $dotnetDirectory -NoPath
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $dotnet)) {
        throw "Nao foi possivel instalar o .NET 8 SDK localmente."
    }
}

if (-not (Test-Path -LiteralPath $classData)) {
    if (-not (Test-Path -LiteralPath $UabeaZip)) {
        throw "UABEA nao encontrado em $UabeaZip. Informe outro zip com -UabeaZip."
    }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    New-Item -ItemType Directory -Path $classDataDirectory -Force | Out-Null
    $archive = [IO.Compression.ZipFile]::OpenRead($UabeaZip)
    try {
        $entry = $archive.Entries | Where-Object { $_.Name -eq "classdata.tpk" } | Select-Object -First 1
        if (-not $entry) { throw "classdata.tpk nao encontrado dentro de $UabeaZip." }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $classData, $true)
    } finally {
        $archive.Dispose()
    }
}

Write-Host "Ferramentas prontas em $tools"
