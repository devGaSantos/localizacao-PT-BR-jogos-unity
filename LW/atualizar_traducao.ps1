param(
    [ValidateSet("status", "preparar", "gerar", "validar", "atualizar", "automatico", "pacote", "instalar")]
    [string]$Etapa = "status",
    [string]$Jogo = "C:\Program Files (x86)\Steam\steamapps\common\Little Witch in the Woods",
    [switch]$ConfirmarInstalacao
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
$AssetPipelineReport = Join-Path $Relatorios "asset_pipeline_automatico.json"
$MissingTranslator = Join-Path $Raiz "traduzir_faltantes_pipeline.py"
$AssetPipeline = Join-Path $Raiz "tools\asset-pipeline\LittleWitch.AssetPipeline.csproj"
$AssetPipelineDll = Join-Path $Raiz "tools\asset-pipeline\bin\Release\net8.0\LittleWitch.AssetPipeline.dll"
$AssetPipelineAssets = Join-Path $Raiz "tools\asset-pipeline\obj\project.assets.json"
$ClassData = Join-Path $Raiz ".tools\uabea\classdata.tpk"
$Staging = Join-Path $Raiz "atualizacao\staging"
$PacoteMerlin = Join-Path $Raiz "atualizacao\pacote_merlin"

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
    if ($general -ne 25) { throw "Esperadas exatamente 25 tabelas gerais; encontradas $general. Nao exporte o objeto tecnico c0f64... do bundle." }
    if ($dialogs -ne 1) { throw "Esperado exatamente 1 DialogueDB atual; encontrados $dialogs." }
    if ($missionTables -ne 10) { throw "Esperados 10 exports CAB-* importaveis de missoes; encontrados $missionTables. O asset base nao entra nessa contagem." }
    if ($missionBase -gt 1) { throw "Encontrado mais de um export base-*; mantenha no maximo um, que sera ignorado." }
    if ($missionJournal -ne 18) { throw "Esperados 18 exports *-resources.assets-* do jornal; encontrados $missionJournal." }
}

function Move-StaleTranslationOutputs(
    [string]$Fluxo,
    [string]$ExportDirectory,
    [string]$OutputDirectory,
    [string]$OutputPrefix = "",
    [string]$ExcludeExportRegex = ""
) {
    if (-not (Test-Path -LiteralPath $OutputDirectory)) { return }

    $exportNames = @(
        Get-ChildItem -LiteralPath $ExportDirectory -File -Filter "*.txt" |
            Where-Object { -not $ExcludeExportRegex -or $_.Name -notmatch $ExcludeExportRegex } |
            ForEach-Object Name
    )
    $staleOutputs = @(
        Get-ChildItem -LiteralPath $OutputDirectory -File -Filter "*.txt" |
            Where-Object {
                $sourceName = $_.Name
                if ($OutputPrefix -and $sourceName.StartsWith($OutputPrefix)) {
                    $sourceName = $sourceName.Substring($OutputPrefix.Length)
                }
                $sourceName -notin $exportNames
            }
    )
    if ($staleOutputs.Count -eq 0) { return }

    $quarantine = Join-Path $Raiz "atualizacao\nao_importar\$Fluxo"
    New-Item -ItemType Directory -Path $quarantine -Force | Out-Null
    foreach ($file in $staleOutputs) {
        Move-Item -LiteralPath $file.FullName -Destination (Join-Path $quarantine $file.Name) -Force
        Write-Warning "Saida antiga isolada (nao importar): $($file.Name)"
    }
}

function Generate-Translations {
    Assert-Exports
    Move-StaleTranslationOutputs "geral" (Join-Path $Raiz "exportados") (Join-Path $Raiz "traduzidos") "TRADUZIDO - "
    Move-StaleTranslationOutputs "dialogos" (Join-Path $Raiz "dialogos\exportados") (Join-Path $Raiz "dialogos\traduzidos") "TRADUZIDO - "
    Move-StaleTranslationOutputs "missoes" (Join-Path $Missoes "exportados") (Join-Path $Missoes "traduzidos") "" "^base-"
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

function Assert-TranslationOutputs {
    $general = @(Get-ChildItem -LiteralPath (Join-Path $Raiz "traduzidos") -File -Filter "*.txt")
    $dialogs = @(Get-ChildItem -LiteralPath (Join-Path $Raiz "dialogos\traduzidos") -File -Filter "*.txt")
    $missionRoot = Join-Path $Missoes "traduzidos"
    $missionLoose = @(Get-ChildItem -LiteralPath $missionRoot -File -Filter "*.txt")
    $missionBundle = @(Get-ChildItem -LiteralPath (Join-Path $missionRoot "defaultlocalgroup") -File -Filter "*.txt")
    $missionResources = @(Get-ChildItem -LiteralPath (Join-Path $missionRoot "resources_assets") -File -Filter "*.txt")
    $missionBase = @($missionBundle + $missionResources | Where-Object { $_.Name -match "^base-" })

    if ($general.Count -ne 25) { throw "Saida geral invalida: esperados 25 arquivos; encontrados $($general.Count)." }
    if ($dialogs.Count -ne 1) { throw "Saida de dialogos invalida: esperado 1 arquivo; encontrados $($dialogs.Count)." }
    if ($missionLoose.Count -ne 0) { throw "Existem $($missionLoose.Count) missoes soltas em traduzidos; use as subpastas por destino." }
    if ($missionBundle.Count -ne 10) { throw "Saida defaultlocalgroup invalida: esperados 10 arquivos; encontrados $($missionBundle.Count)." }
    if ($missionResources.Count -ne 18) { throw "Saida resources.assets invalida: esperados 18 arquivos; encontrados $($missionResources.Count)." }
    if ($missionBase.Count -ne 0) { throw "Asset base encontrado nas saidas de importacao; mova-o para nao_importar." }
}

function Validate-Translations {
    Assert-TranslationOutputs
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

function Resolve-DotNetSdk {
    $local = Join-Path $Raiz ".tools\dotnet\dotnet.exe"
    if (Test-Path -LiteralPath $local) { return $local }
    return Resolve-Executable "dotnet" @()
}

function Initialize-AssetPipeline {
    if (-not (Test-Path -LiteralPath $ClassData)) {
        throw "classdata.tpk nao encontrado em $ClassData. Consulte docs\FLUXO_TRADUCAO.md para preparar a ferramenta uma unica vez."
    }
    $dotnet = Resolve-DotNetSdk
    if (-not (Test-Path -LiteralPath $AssetPipelineAssets)) {
        $nugetConfig = Join-Path $Raiz "tools\asset-pipeline\NuGet.Config"
        Invoke-Tool $dotnet @("restore", $AssetPipeline, "--configfile", $nugetConfig) $Raiz
    }
    Invoke-Tool $dotnet @("build", $AssetPipeline, "--configuration", "Release", "--no-restore") $Raiz
}

function Invoke-AssetPipeline([string]$DotNet, [string]$Mode) {
    Invoke-Tool $DotNet @($AssetPipelineDll, $Mode, $Jogo, $Raiz, $ClassData, $Staging) $Raiz
}

function Invoke-AssetPipelineScan([string]$DotNet) {
    $oldPythonIoEncoding = $env:PYTHONIOENCODING
    $oldPythonUtf8 = $env:PYTHONUTF8
    Push-Location $Raiz
    try {
        $env:PYTHONIOENCODING = "utf-8"
        $env:PYTHONUTF8 = "1"
        & $DotNet @($AssetPipelineDll, "scan", $Jogo, $Raiz, $ClassData, $Staging)
        $exitCode = $LASTEXITCODE
        if ($exitCode -ne 0 -and $exitCode -ne 3) {
            throw "Scan do AssetPipeline falhou ($exitCode)."
        }
    } finally {
        $env:PYTHONIOENCODING = $oldPythonIoEncoding
        $env:PYTHONUTF8 = $oldPythonUtf8
        Pop-Location
    }
}

function Get-AssetPipelineReport {
    if (-not (Test-Path -LiteralPath $AssetPipelineReport)) {
        throw "Relatorio do AssetPipeline nao encontrado: $AssetPipelineReport"
    }
    return Get-Content -LiteralPath $AssetPipelineReport -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Update-MissingAutomaticTranslations {
    $report = Get-AssetPipelineReport
    if ($report.Ready) { return }

    $missingTotal = 0
    foreach ($flow in $report.Flows) {
        $missingTotal += [int]$flow.MissingUnique
    }
    if ($missingTotal -le 0) {
        throw "O scan retornou Ready=false, mas nao informou textos faltantes."
    }

    if (-not (Test-Path -LiteralPath $MissingTranslator)) {
        throw "Tradutor de faltantes nao encontrado: $MissingTranslator"
    }

    $pythonFallback = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    $python = Resolve-Executable "python" @($pythonFallback)

    Write-Host "`nForam encontrados $missingTotal textos novos. Traduzindo e atualizando as memorias..."
    Invoke-Tool $python @(
        $MissingTranslator,
        "--report", $AssetPipelineReport,
        "--project", $Raiz,
        "--missions-root", $Missoes
    ) $Raiz
}

function Export-MerlinPackage {
    $dataDirectory = Join-Path $PacoteMerlin "LWIW_Data"
    $bundleDirectory = Join-Path $dataDirectory "StreamingAssets\aa\StandaloneWindows64"
    New-Item -ItemType Directory -Path $bundleDirectory -Force | Out-Null

    foreach ($artifact in $Artefatos) {
        $source = Join-Path $Staging $artifact.Nome
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Asset validado nao encontrado no staging: $source"
        }
        $destinationDirectory = if ($artifact.Nome -eq "resources.assets") { $dataDirectory } else { $bundleDirectory }
        $destination = Join-Path $destinationDirectory $artifact.Nome
        Copy-Item -LiteralPath $source -Destination $destination -Force
        $sourceHash = (Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash
        $destinationHash = (Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash
        if ($sourceHash -ne $destinationHash) {
            throw "Falha ao validar o arquivo do pacote: $destination"
        }
    }

    Write-Host "PACOTE MERLIN PRONTO: $PacoteMerlin"
    Write-Host "Arraste a pasta LWIW_Data para a raiz do jogo e confirme a substituicao."
}

function Build-AutomaticStaging {
    Initialize-AssetPipeline
    $dotnet = Resolve-DotNetSdk

    Write-Host "`n[1/3] Analisando assets atuais e cobertura das memorias"
    Invoke-AssetPipelineScan $dotnet
    $scanReport = Get-AssetPipelineReport

    if (-not $scanReport.Ready) {
        Update-MissingAutomaticTranslations

        Write-Host "`n[1/3] Reanalisando cobertura depois da traducao automatica"
        Invoke-AssetPipelineScan $dotnet
        $scanReport = Get-AssetPipelineReport

        if (-not $scanReport.Ready) {
            $remaining = 0
            foreach ($flow in $scanReport.Flows) {
                $remaining += [int]$flow.MissingUnique
            }
            throw "Ainda existem $remaining textos sem traducao depois do Translator. Build cancelado."
        }
    }

    Write-Host "`n[2/3] Reconstruindo os quatro assets no staging"
    Invoke-AssetPipeline $dotnet "build"
    Write-Host "`n[3/3] Reabrindo e validando os assets reconstruidos"
    Invoke-AssetPipeline $dotnet "verify"
    Export-MerlinPackage
    Write-Host "`nSTAGING PRONTO: $Staging"
    Write-Host "O jogo ainda nao foi modificado. Para instalar, use -Etapa instalar -ConfirmarInstalacao."
}

function Build-MerlinPackage {
    Initialize-AssetPipeline
    $dotnet = Resolve-DotNetSdk
    Invoke-AssetPipeline $dotnet "verify"
    Export-MerlinPackage
}

function Install-AutomaticStaging {
    if (-not $ConfirmarInstalacao) {
        throw "Instalacao cancelada por seguranca. Repita com -Etapa instalar -ConfirmarInstalacao."
    }

    $gameProcess = Get-Process -ErrorAction SilentlyContinue | Where-Object {
        $_.ProcessName -like "*Little Witch*" -or $_.ProcessName -eq "LWIW"
    }
    if ($gameProcess) { throw "Feche Little Witch in the Woods antes de instalar a traducao." }

    Initialize-AssetPipeline
    $dotnet = Resolve-DotNetSdk
    Invoke-AssetPipeline $dotnet "verify"
    $expected = @($Artefatos | ForEach-Object { $_.Nome })
    $staged = @(Get-ChildItem -LiteralPath $Staging -File | ForEach-Object Name)
    if (@($staged | Where-Object { $_ -notin $expected }).Count -ne 0 -or $staged.Count -ne $expected.Count) {
        throw "Staging invalido: devem existir somente os quatro assets esperados."
    }

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backup = Join-Path $Raiz "atualizacao\backups\$timestamp"
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($artifact in $Artefatos) {
        Copy-Item -LiteralPath $artifact.Caminho -Destination (Join-Path $backup $artifact.Nome) -Force
    }

    try {
        foreach ($artifact in $Artefatos) {
            Copy-Item -LiteralPath (Join-Path $Staging $artifact.Nome) -Destination $artifact.Caminho -Force
        }
    } catch {
        foreach ($artifact in $Artefatos) {
            $saved = Join-Path $backup $artifact.Nome
            if (Test-Path -LiteralPath $saved) {
                Copy-Item -LiteralPath $saved -Destination $artifact.Caminho -Force
            }
        }
        throw "A instalacao falhou e o backup foi restaurado. Erro original: $($_.Exception.Message)"
    }

    $manifest = [pscustomobject]@{
        installedAt = (Get-Date).ToUniversalTime().ToString("o")
        game = $Jogo
        backup = $backup
        files = @($Artefatos | ForEach-Object {
            [pscustomobject]@{
                fluxo = $_.Fluxo
                caminho = $_.Caminho
                sha256 = (Get-FileHash -LiteralPath $_.Caminho -Algorithm SHA256).Hash
            }
        })
    }
    Write-JsonUtf8 (Join-Path $backup "manifesto_instalacao.json") $manifest
    Write-Host "Traducao instalada. Backup dos originais: $backup"
}

switch ($Etapa) {
    "status" { Show-Status | Out-Null }
    "preparar" { Show-Status | Out-Null; Prepare-Bundles }
    "gerar" { Generate-Translations }
    "validar" { Validate-Translations | Out-Null }
    "atualizar" { Show-Status | Out-Null; Generate-Translations; Validate-Translations | Out-Null }
    "automatico" { Build-AutomaticStaging }
    "pacote" { Build-MerlinPackage }
    "instalar" { Install-AutomaticStaging }
}
