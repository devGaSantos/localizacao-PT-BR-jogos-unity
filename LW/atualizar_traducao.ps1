param(
    [ValidateSet("status", "preparar", "gerar", "validar", "atualizar")]
    [string]$Etapa = "status",
    [string]$Jogo = "C:\Program Files (x86)\Steam\steamapps\common\Little Witch in the Woods"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$Raiz = $PSScriptRoot
$Projeto = Split-Path -Parent $Raiz
$Missoes = Join-Path $Projeto "missoes"
$Relatorios = Join-Path $Raiz "relatorios"
$BundlesJogo = Join-Path $Jogo "LWIW_Data\StreamingAssets\aa\StandaloneWindows64"
$ResourcesJogo = Join-Path $Jogo "LWIW_Data\resources.assets"
$EstadoPath = Join-Path $Relatorios "estado_atualizacao_bundles.json"
$ResumoPath = Join-Path $Relatorios "resumo_pipeline_atualizacao.json"

$Artefatos = @(
    [pscustomobject]@{ Fluxo = "geral"; Nome = "localization-string-tables-english(en)_assets_all.bundle"; Caminho = (Join-Path $BundlesJogo "localization-string-tables-english(en)_assets_all.bundle") },
    [pscustomobject]@{ Fluxo = "dialogos"; Nome = "dialoguedb_assets_all.bundle"; Caminho = (Join-Path $BundlesJogo "dialoguedb_assets_all.bundle") },
    [pscustomobject]@{ Fluxo = "missoes_tabelas"; Nome = "defaultlocalgroup_assets_all.bundle"; Caminho = (Join-Path $BundlesJogo "defaultlocalgroup_assets_all.bundle") },
    [pscustomobject]@{ Fluxo = "missoes_jornal"; Nome = "resources.assets"; Caminho = $ResourcesJogo }
)

function Write-JsonUtf8([string]$Path, $Data) {
    $json = $Data | ConvertTo-Json -Depth 20
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $json + [Environment]::NewLine, $utf8)
}

function Resolve-Executable([string]$Name, [string[]]$Fallbacks) {
    $candidates = @()
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) { $candidates += $command.Source }
    $candidates += $Fallbacks
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return $candidate }
    }
    throw "Executavel nao encontrado: $Name"
}

function Invoke-Tool([string]$Executable, [string[]]$Arguments, [string]$WorkingDirectory) {
    $oldPythonIoEncoding = $env:PYTHONIOENCODING
    $oldPythonUtf8 = $env:PYTHONUTF8
    Push-Location $WorkingDirectory
    try {
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Comando falhou ($LASTEXITCODE): $Executable $($Arguments -join ' ')"
        }
    } finally {
        $env:PYTHONIOENCODING = $oldPythonIoEncoding
        $env:PYTHONUTF8 = $oldPythonUtf8
        Pop-Location
    }
}

function Get-BundleStatus {
    $previous = $null
    if (Test-Path -LiteralPath $EstadoPath) {
        $previous = Get-Content -LiteralPath $EstadoPath -Raw -Encoding UTF8 | ConvertFrom-Json
    }

    $items = foreach ($bundle in $Artefatos) {
        $path = $bundle.Caminho
        if (-not (Test-Path -LiteralPath $path)) { throw "Bundle nao encontrado: $path" }
        $file = Get-Item -LiteralPath $path
        $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
        $oldHash = $null
        if ($previous -and $previous.bundles) {
            $old = $previous.bundles | Where-Object { $_.fluxo -eq $bundle.Fluxo }
            if ($old) { $oldHash = $old.sha256 }
        }
        [pscustomobject]@{
            fluxo = $bundle.Fluxo
            nome = $bundle.Nome
            caminho = $path
            bytes = $file.Length
            modificadoUtc = $file.LastWriteTimeUtc.ToString("o")
            sha256 = $hash
            mudouDesdeUltimaGeracao = [bool]($oldHash -and $oldHash -ne $hash)
            semHistorico = [bool](-not $oldHash)
        }
    }
    return @($items)
}

function Get-ExportStatus {
    $generalFiles = @(Get-ChildItem -LiteralPath (Join-Path $Raiz "exportados") -File -Filter "*.txt")
    $dialogFiles = @(Get-ChildItem -LiteralPath (Join-Path $Raiz "dialogos\exportados") -File -Filter "DialogueDB_en-*.txt")
    $missionFiles = @(Get-ChildItem -LiteralPath (Join-Path $Missoes "exportados") -File -Filter "*.txt")
    $missionBundleFiles = @($missionFiles | Where-Object { $_.Name -match "-CAB-" -and $_.Name -notmatch "^base-" })
    $missionBaseFiles = @($missionFiles | Where-Object { $_.Name -match "^base-" })
    $missionResourceFiles = @($missionFiles | Where-Object { $_.Name -match "-resources\.assets-" })
    return @(
        [pscustomobject]@{ fluxo = "geral"; arquivos = $generalFiles.Count; pasta = (Join-Path $Raiz "exportados") },
        [pscustomobject]@{ fluxo = "dialogos"; arquivos = $dialogFiles.Count; pasta = (Join-Path $Raiz "dialogos\exportados") },
        [pscustomobject]@{ fluxo = "missoes_tabelas"; arquivos = $missionBundleFiles.Count; pasta = (Join-Path $Missoes "exportados") },
        [pscustomobject]@{ fluxo = "missoes_base_nao_importar"; arquivos = $missionBaseFiles.Count; pasta = (Join-Path $Missoes "exportados") },
        [pscustomobject]@{ fluxo = "missoes_jornal"; arquivos = $missionResourceFiles.Count; pasta = (Join-Path $Missoes "exportados") }
    )
}

function Show-Status {
    New-Item -ItemType Directory -Path $Relatorios -Force | Out-Null
    $status = [pscustomobject]@{
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        jogo = $Jogo
        bundles = Get-BundleStatus
        exports = Get-ExportStatus
    }
    Write-JsonUtf8 (Join-Path $Relatorios "status_atualizacao.json") $status
    Write-Host "`nARTEFATOS DO JOGO"
    $status.bundles | Format-Table fluxo, bytes, mudouDesdeUltimaGeracao, semHistorico, nome -AutoSize | Out-Host
    Write-Host "EXPORTS"
    $status.exports | Format-Table fluxo, arquivos, pasta -AutoSize | Out-Host
    return $status
}

function Prepare-Bundles {
    $destination = Join-Path $Raiz "atualizacao\bundles_originais"
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    foreach ($bundle in $Artefatos) {
        $source = $bundle.Caminho
        Copy-Item -LiteralPath $source -Destination (Join-Path $destination $bundle.Nome) -Force
    }
    Write-Host "Copias atuais preparadas em: $destination"
    Write-Host "Exporte delas as tabelas gerais, o DialogueDB, os 10 TextTable importaveis do bundle e os 18 TextTable de resources.assets."
    Write-Warning "Nao importe o asset base. Se ele for exportado, o script de missoes ira ignora-lo."
}

function Assert-Exports {
    $status = Get-ExportStatus
    $general = ($status | Where-Object fluxo -eq "geral").arquivos
    $dialogs = ($status | Where-Object fluxo -eq "dialogos").arquivos
    $missionTables = ($status | Where-Object fluxo -eq "missoes_tabelas").arquivos
    $missionBase = ($status | Where-Object fluxo -eq "missoes_base_nao_importar").arquivos
    $missionJournal = ($status | Where-Object fluxo -eq "missoes_jornal").arquivos
    if ($general -lt 1) { throw "Nenhum export geral encontrado." }
    if ($dialogs -ne 1) { throw "Esperado exatamente 1 DialogueDB atual; encontrados $dialogs." }
    if ($missionTables -ne 10) { throw "Esperados 10 exports CAB-* importaveis de missoes; encontrados $missionTables. O asset base nao entra nessa contagem." }
    if ($missionBase -gt 1) { throw "Encontrado mais de um export base-*; mantenha no maximo um, que sera ignorado." }
    if ($missionJournal -ne 18) { throw "Esperados 18 exports *-resources.assets-* do jornal; encontrados $missionJournal." }
}

function Generate-Translations {
    Assert-Exports
    $pythonFallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $python = Resolve-Executable "python" @($pythonFallback)
    $nodeFallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    $node = Resolve-Executable "node" @($nodeFallback)

    Write-Host "`n[1/3] Textos gerais"
    Invoke-Tool $python @("gera_traduzidos_via_json.py") $Raiz

    Write-Host "`n[2/3] Dialogos"
    Invoke-Tool $node @("gerar_dialogos_via_memoria.js") $Raiz

    Write-Host "`n[3/3] Missoes"
    Invoke-Tool $python @("script_missoes.py") $Missoes
    Invoke-Tool $python @("script_missoes.py", "-translate") $Missoes
}

function Count-ObjectProperties($Object) {
    if ($null -eq $Object) { return 0 }
    return @($Object.PSObject.Properties).Count
}

function Validate-Translations {
    $nodeFallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
    $node = Resolve-Executable "node" @($nodeFallback)
    Invoke-Tool $node @("auditar_encoding_memorias.js") $Raiz
    Invoke-Tool $node @("auditar_nomes_personagens.js") $Raiz
    Invoke-Tool $node @("auditar_dialogos_nao_traduzidos.js") $Raiz

    $generalReport = Get-Content -LiteralPath (Join-Path $Relatorios "relatorio_aplicacao_memoria_revisado.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $generalMissing = 0
    foreach ($file in $generalReport.PSObject.Properties.Value) {
        $generalMissing += Count-ObjectProperties $file.frases_nao_encontradas
    }

    $dialogReport = Get-Content -LiteralPath (Join-Path $Relatorios "relatorio_geracao_dialogos_memoria.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $dialogAudit = Get-Content -LiteralPath (Join-Path $Relatorios "auditoria_dialogos_nao_traduzidos.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $missionReport = Get-Content -LiteralPath (Join-Path $Missoes "relatorios\relatorio_translate_missoes.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $encodingReport = Get-Content -LiteralPath (Join-Path $Relatorios "auditoria_encoding_completa.json") -Raw -Encoding UTF8 | ConvertFrom-Json

    $missionMissing = 0
    foreach ($file in $missionReport) { $missionMissing += @($file.sem_traducao).Count }

    $summary = [pscustomobject]@{
        generatedAt = (Get-Date).ToUniversalTime().ToString("o")
        status = if ($generalMissing + $dialogReport.missingUnique + $missionMissing -eq 0 -and $encodingReport.cleanValues) { "pronto" } else { "revisao_necessaria" }
        geral = [pscustomobject]@{ faltantesUnicos = $generalMissing }
        dialogos = [pscustomobject]@{
            faltantesUnicos = $dialogReport.missingUnique
            aindaEmIngles = $dialogAudit.counts.confirmedOutputStillEnglish
            identidadesNaoTraduzidas = $dialogAudit.counts.confirmedUntranslatedIdentity
        }
        missoes = [pscustomobject]@{ faltantes = $missionMissing }
        encoding = [pscustomobject]@{ limpo = $encodingReport.cleanValues }
        bundles = Get-BundleStatus
    }
    Write-JsonUtf8 $ResumoPath $summary

    Write-Host "`nRESUMO"
    $summary | Select-Object status, geral, dialogos, missoes, encoding | Format-List | Out-Host
    Write-Host "Relatorio: $ResumoPath"

    $state = [pscustomobject]@{
        generatedAt = $summary.generatedAt
        status = $summary.status
        bundles = $summary.bundles
    }
    Write-JsonUtf8 $EstadoPath $state
    return $summary
}

switch ($Etapa) {
    "status" { Show-Status | Out-Null }
    "preparar" { Show-Status | Out-Null; Prepare-Bundles }
    "gerar" { Generate-Translations }
    "validar" { Validate-Translations | Out-Null }
    "atualizar" { Show-Status | Out-Null; Generate-Translations; Validate-Translations | Out-Null }
}
