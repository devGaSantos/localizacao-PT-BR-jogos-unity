# Fluxo de traducao

## Textos gerais

- Origem exportada: `exportados/`
- Memoria principal: `memoria_revisado.json`
- Gerador: `gera_traduzidos_via_json.py`
- Saida: `traduzidos/`
- Relatorio: `relatorios/relatorio_aplicacao_memoria_revisado.json`

Entradas vazias `m_Localized = ""` nao precisam de traducao. Atualmente o gerador as
inclui no contador de nao encontradas, mas nao as lista em `frases_nao_encontradas`.
Assim, um relatorio com faltantes e lista vazia deve ser conferido como possivel falso
positivo. Na verificacao de 15/08/2026, as 86 entradas informadas eram todas vazias.

## Dialogos

Nas versoes atuais, os dialogos nao ficam mais em `resources.assets`. O asset esta no
bundle Addressables:

`LWIW_Data/StreamingAssets/aa/StandaloneWindows64/dialoguedb_assets_all.bundle`

Depois de exportado, o arquivo `DialogueDB_*.txt` fica em `dialogos/exportados/`.
O formato continua compativel com `dialogos/script_translation_batch.py`, que procura
blocos `Field data` contendo `title = "en"`, `value` e
`typeString = "CustomFieldType_Localization"`.

O script usa caminhos relativos. Execute-o dentro de `dialogos/`:

```powershell
cd C:\Users\AZTEKA\Videos\Little-witch-in-the-woods-PT-BR-localization\LW\dialogos
py .\script_translation_batch.py
```

Memorias usadas pelo fluxo de dialogos:

- `dialogos/memory/memoria_manual.json`, quando existir
- `dialogos/memory/memoria.json`
- `dialogos/memory/traduzidas_por_translator.json`

A saida fica em `dialogos/traduzidos/`. Na reinsercao, o arquivo traduzido deve voltar
ao `dialoguedb_assets_all.bundle`, nao ao antigo `resources.assets`.

## Alteracao de um termo recorrente

1. Definir a traducao oficial no glossario.
2. Procurar o nome em todas as chaves e traducoes das memorias gerais e de dialogos.
3. Atualizar todas as ocorrencias, preservando tags, tokens, plural e contexto.
4. Regenerar os textos gerais e os dialogos a partir das memorias.
5. Conferir se o termo antigo ainda aparece nas saidas.
6. Registrar no glossario a decisao e a data da revisao.

## Validacao de encoding

Antes de regenerar e depois de atualizar qualquer memoria, execute na raiz de `LW`:

```powershell
node .\auditar_encoding_memorias.js
```

O auditor verifica integralmente `dialogos/memory/memoria.json` e
`memoria_revisado.json`. Ele detecta UTF-8 invalido, BOM, mojibake, letras substituidas
por `?`, caracteres invisiveis nos valores, controles Unicode e texto fora de NFC.
O relatorio detalhado fica em `relatorios/auditoria_encoding_completa.json`.

## Auditoria de dialogos nao traduzidos

Depois de atualizar a memoria ou gerar novamente o DialogueDB, execute na raiz de `LW`:

```powershell
node .\auditar_dialogos_nao_traduzidos.js
```

O auditor compara todas as entradas `title = "en"` do exportado, da memoria e da saida.
Ele separa frases integralmente em ingles, possiveis trechos parciais, identidades
ambiguas, comandos tecnicos e traducoes presentes na memoria mas ainda nao aplicadas.
Os resultados ficam em `relatorios/auditoria_dialogos_nao_traduzidos.md` e `.json`.

Uma identidade `chave === valor` não deve ser traduzida cegamente. Antes, separe nomes
próprios, comandos, identificadores, sons, datas e palavras com grafia válida em PT-BR.
O objetivo do relatório é zerar `confirmedUntranslatedIdentity`, não zerar toda
identidade técnica ou não linguística.

Para conferir nomes próprios de personagens nas memórias, execute:

```powershell
node .\auditar_nomes_personagens.js
```

Para aplicar a memória atual ao DialogueDB sem chamar tradução automática, execute:

```powershell
node .\sincronizar_dialogos_com_memoria.js
```

## Auditoria linguística contextual

Antes de revisar gênero, concordância ou uma tradução literal, gere o índice de
contexto do `DialogueDB` e execute o auditor:

```powershell
node .\indexar_contexto_dialogos.js
node .\auditar_qualidade_linguistica_dialogos.js
```

Os resultados ficam em:

- `relatorios/indice_contexto_dialogos.json`;
- `relatorios/auditoria_qualidade_linguistica_dialogos.json`;
- `relatorios/auditoria_qualidade_linguistica_dialogos.md`.

O auditor gera candidatos, não correções automáticas. O campo `Conversant` pode
apontar para o próprio falante ou para um nó interno da conversa. Antes de flexionar
uma frase, confirme o personagem citado, o título da conversa e as falas vizinhas.
Falas entre aspas podem usar um gênero diferente do ator que as pronuncia.

As correções aprovadas no quinto passe podem ser reaplicadas de forma idempotente com:

```powershell
node .\aplicar_revisao_linguistica_dialogos.js
node .\auditar_encoding_memorias.js
node .\auditar_nomes_personagens.js
node .\auditar_dialogos_nao_traduzidos.js
```

O aplicador preserva backups, altera somente `dialogos/memory/memoria.json`, valida
tags, comandos Lua e `\r`, e grava o relatório cumulativo em
`relatorios/revisao_linguistica_dialogos_20260815.json`.

Execute `sincronizar_dialogos_com_memoria.js` somente quando houver uma solicitação
explícita para atualizar o arquivo em `dialogos/traduzidos`.

## Localização das missões na versão atual

As missões usam duas cópias de `TextTable` com funções diferentes. O catálogo
Addressables declara 11 tabelas dentro de `defaultlocalgroup_assets_all.bundle`, mas
somente 10 devem ser traduzidas e reinseridas:

- `main_Ellie`;
- `main_WhiteCat`;
- `npc_arden`;
- `npc_aurea`;
- `npc_diane`;
- `npc_enite`;
- `npc_kyla`;
- `npc_rosie`;
- `npc_rubrum`;
- `prologue`.

O asset `base` nao e importavel. Importa-lo de volta pode corromper ou quebrar o
bundle. Ele pode ficar entre os exports por conveniencia, mas `script_missoes.py`
sempre o ignora e move qualquer saida antiga `base-*` para `missoes/nao_importar/`.

O arquivo `LWIW_Data/resources.assets` ainda contém 18 tabelas, incluindo
`npc_Roy`, `npc_alvin`, `npc_arin`, `npc_bjorn`, `npc_clala`, `npc_library`,
`npc_rex`, `npc_teo` e `npc_vinch`. A tela de histórico do jornal lê os títulos
dessas tabelas. Isso foi confirmado em 17/08/2026 pelos títulos `The way to the
Room`, `White Cat`, `In Search For A Curious Creature` e `To Places Anew`, que
continuaram em inglês após a troca isolada do `defaultlocalgroup`.

Portanto, a cobertura completa das missões exige três fontes:

1. `defaultlocalgroup_assets_all.bundle`, com 10 `TextTable` importaveis e o asset
   `base` proibido para reinsercao;
2. `resources.assets`, com os 18 `TextTable` usados pelo histórico do jornal;
3. `localization-string-tables-english(en)_assets_all.bundle`, com `Post`, `QuestUI`
   e `QuestNode`.

As tabelas `Post`, `QuestUI` e `QuestNode` entram no fluxo geral de
`memoria_revisado.json`. Os 10 mais os 18 dumps importaveis de missão usam
`memoria_missoes.json`. Sempre exporte os 18 novamente a partir do
`resources.assets` da versão instalada; não reutilize automaticamente dumps de uma
versão antiga.

Na verificação de 15/08/2026, o pacote `LWIW_PTBR` já continha o bundle inglês de
tabelas de strings, mas essa cópia era anterior à instalada pelo jogo: 705.152 bytes
no pacote contra 724.580 bytes na instalação atual. O pacote ainda não continha o
`defaultlocalgroup_assets_all.bundle`. Ao atualizar a tradução, reconstrua os dois
bundles e o `resources.assets` usando como base os arquivos da versão atual do jogo
para não perder textos novos.

Para repetir a comparação após uma atualização do jogo, execute:

```powershell
node .\analisar_localizacao_missoes.js
```

O resultado detalhado fica em
`relatorios/analise_localizacao_missoes_atual.json`.

### Uso do script de missoes

O `script_missoes.py` usa caminhos relativos, por isso deve ser executado dentro da
pasta `missoes`:

```powershell
cd C:\Users\AZTEKA\Videos\Little-witch-in-the-woods-PT-BR-localization\missoes
py .\script_missoes.py
```

Sem argumentos, ele extrai os textos ingleses dos arquivos em `exportados/`, preserva
as traducoes existentes e adiciona novas chaves vazias em `memoria_missoes.json`.
Depois de preencher as traducoes vazias, aplique a memoria com:

```powershell
py .\script_missoes.py -translate
```

O segundo comando gera o relatorio em `relatorios/relatorio_translate_missoes.json`
e separa automaticamente as saidas por destino:

- `traduzidos/defaultlocalgroup/`: 10 dumps `CAB-*` para o bundle;
- `traduzidos/resources_assets/`: 18 dumps para `resources.assets`.

O script nao apaga saidas antigas. Qualquer `base-*` ou saida obsoleta de uma versao
anterior e movida com seguranca para `nao_importar/`.

Esse script cobre os dois conjuntos de `TextTable`. `Post`, `QuestUI` e `QuestNode`
continuam no fluxo geral de `memoria_revisado.json`.

Na validação de 15/08/2026, os 11 arquivos do bundle foram processados, incluindo
indevidamente o `base`, com
132 substituições, zero faltantes e zero erros. Essa validação não cobria o histórico
do jornal e nao deve ser repetida: processe somente os 10 importaveis mais os 18
exports atuais de `resources.assets`.

## Pipeline automatizado de atualizacao

### Launcher publico para Nexus

`publicar_atualizador.ps1` gera
`dist/Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip`. Esse ZIP contem o
`LittleWitch.Launcher.exe`, o pipeline e todas as tres memorias necessarias; quem
joga nao precisa instalar UABEA, .NET, Python ou ferramentas de modding.

O usuario extrai o ZIP em uma pasta permanente e abre o executavel. O launcher
detecta a primeira execucao ou uma troca dos assets pela Steam, reconstrói os quatro
arquivos a partir da versao instalada, valida o staging, cria backup em
`backups/<data-hora>/` e so entao abre o jogo. Nas execucoes seguintes, se o hash do
`resources.assets` instalado ainda for o mesmo que o hash da traducao aplicada, ele
somente inicia o jogo.

Se uma atualizacao incluir texto novo sem uma entrada na memoria, o launcher preserva
esse trecho em ingles e atualiza o restante. Isso evita copiar assets antigos ou
interromper o jogo por causa de uma unica frase nova; a traducao revisada volta numa
versao posterior do mod.

O orquestrador `atualizar_traducao.ps1` possui dois fluxos independentes:

- o fluxo convencional por dumps (`preparar`, `gerar`, `validar` e `atualizar`),
  mantido para diagnostico e edicao manual;
- o fluxo automatico por `AssetsTools.NET`, que le os assets instalados, aplica as
  memorias e reconstroi os quatro arquivos sem usar o UABEA manualmente.

### Preparacao unica

O fluxo automatico precisa do .NET 8 SDK e do `classdata.tpk` do UABEA. Com o arquivo
`uabea-windows.zip` em `Downloads`, execute uma vez:

```powershell
.\preparar_pipeline_assets.ps1
```

Se o zip estiver em outro lugar:

```powershell
.\preparar_pipeline_assets.ps1 -UabeaZip "C:\caminho\uabea-windows.zip"
```

As ferramentas ficam em `LW/.tools/`, que e ignorada pelo Git. O script instala um
.NET SDK local, sem alterar o SDK global do Windows, extrai somente `classdata.tpk` e
nao instala nem modifica o jogo.

### Geracao automatica segura

Feche o jogo, deixe a Steam terminar a atualizacao e execute dentro de `LW`:

```powershell
.\atualizar_traducao.ps1 -Etapa automatico
```

Esse comando:

1. le diretamente os assets atuais da instalacao;
2. exige exatamente 25 tabelas gerais, 1 DialogueDB, 10 tabelas de missao no
   `defaultlocalgroup` e 18 tabelas no `resources.assets`;
3. ignora sempre o asset tecnico `base`;
4. aplica `memoria_revisado.json`, `dialogos/memory/memoria.json` e
   `missoes/memoria_missoes.json`;
5. interrompe a geracao se encontrar qualquer texto sem traducao;
6. grava os quatro resultados em `LW/atualizacao/staging/`;
7. reabre os arquivos reconstruidos e repete toda a validacao;
8. monta `LW/atualizacao/pacote_merlin/LWIW_Data/` com os caminhos finais do jogo.

O relatorio completo fica em `relatorios/asset_pipeline_automatico.json`. Prossiga
somente quando `Ready` for `true`. O comando `automatico` nunca altera os arquivos
vivos da Steam.

Para distribuir pelo Merlin ou instalar manualmente, use a pasta:

`LW/atualizacao/pacote_merlin/LWIW_Data/`

Ela pode ser arrastada diretamente para a raiz `Little Witch in the Woods`, mantendo
os caminhos internos. Confirme a substituicao dos quatro arquivos quando o Windows
solicitar. Para remontar somente o pacote usando um staging existente e validado:

```powershell
.\atualizar_traducao.ps1 -Etapa pacote
```

Os quatro resultados sao mantidos separados:

- `localization-string-tables-english(en)_assets_all.bundle`: textos gerais;
- `dialoguedb_assets_all.bundle`: dialogos;
- `defaultlocalgroup_assets_all.bundle`: 10 tabelas atuais de missao;
- `resources.assets`: 18 tabelas usadas pelo historico do jornal.

### Instalacao com backup

Depois de conferir o relatorio, instale explicitamente com:

```powershell
.\atualizar_traducao.ps1 -Etapa instalar -ConfirmarInstalacao
```

Essa etapa verifica novamente o staging, exige que o jogo esteja fechado, salva os
quatro originais em `LW/atualizacao/backups/<data-hora>/` e so depois substitui os
arquivos. Se uma copia falhar, o script tenta restaurar imediatamente todos os
originais. Cada backup inclui `manifesto_instalacao.json` com caminhos e hashes dos
arquivos instalados.

### Fluxo convencional preservado

O processo anterior continua funcionando e nao foi removido. Para gerar dumps
traduzidos e fazer a reinsercao manual, use:

```powershell
.\atualizar_traducao.ps1 -Etapa preparar
.\atualizar_traducao.ps1 -Etapa atualizar
```

Nesse fluxo, exporte 25 tabelas gerais, 1 `DialogueDB_en-*`, 10 tabelas CAB de
missao e 18 tabelas de `resources.assets`. Nunca reinsira o asset `base`.

### Passo a passo convencional por dumps

1. Feche o jogo e deixe a Steam concluir qualquer atualizacao.
2. Dentro de `LW`, execute `atualizar_traducao.ps1 -Etapa status` para conferir os
   hashes e quais exports ainda pertencem a versao anterior.
3. Execute `atualizar_traducao.ps1 -Etapa preparar`. O comando copia os quatro
   artefatos atuais do jogo para `LW/atualizacao/bundles_originais/`, sem alterar a
   instalacao.
4. No editor de assets, exporte 25 tabelas gerais, 1 `DialogueDB_en-*`, 10 tabelas
   CAB de missao e 18 tabelas de missao de `resources.assets`.
5. Coloque os exports gerais em `LW/exportados/`, o DialogueDB em
   `LW/dialogos/exportados/` e os 28 exports importaveis de missao em
   `missoes/exportados/`.
6. Nao exporte nem importe o asset de missao `base`. Se ele estiver na pasta por
   engano, o script o ignora; qualquer saida antiga e movida para
   `missoes/nao_importar/`.
7. Execute `atualizar_traducao.ps1 -Etapa atualizar`. O pipeline aplica as tres
   memorias, gera as saidas e executa as auditorias.
8. Abra `relatorios/resumo_pipeline_atualizacao.json`. Prossiga somente se o status
   for `pronto`; se houver faltantes, atualize a memoria indicada e rode novamente.
9. Reinsira manualmente cada saida no artefato de onde veio: gerais no bundle de
   localizacao, dialogos no `dialoguedb`, 10 CAB no `defaultlocalgroup` e 18 tabelas
   no `resources.assets`.
10. Monte o pacote, instale em uma copia limpa e teste dialogos, diario e titulos de
    missoes antes de publicar.

Para verificar se a Steam mudou algum dos tres bundles ou o `resources.assets`:

```powershell
.\atualizar_traducao.ps1 -Etapa status
```

O status compara hashes SHA-256 da instalacao atual com a ultima geracao validada e
confere as quantidades de exports. O resultado fica em
`relatorios/status_atualizacao.json`.

Para copiar os artefatos atuais para uma area segura antes de exportar:

```powershell
.\atualizar_traducao.ps1 -Etapa preparar
```

As copias ficam em `atualizacao/bundles_originais/`. Para continuar pelo fluxo
convencional, use o editor grafico para exportar:

- 25 tabelas gerais para `LW/exportados/`;
- 1 `DialogueDB_en-*` para `LW/dialogos/exportados/`;
- 10 `TextTable` `CAB-*` importaveis do `defaultlocalgroup` para
  `missoes/exportados/`;
- nao exporte nem importe `base`; se exportar por engano, o script ira ignora-lo;
- 18 `TextTable` `*-resources.assets-*` para `missoes/exportados/`.

Nao exporte o objeto tecnico raiz cujo dump comeca por `c0f64...bundle-`. Ele nao e
uma tabela de strings e era o falso 26o arquivo das contagens antigas.

Antes de gerar, o pipeline tambem compara cada pasta `traduzidos/` com os exports
atuais. Saidas antigas ou tecnicas que nao correspondem mais a um export sao movidas,
sem exclusao, para `LW/atualizacao/nao_importar/<fluxo>/`. Nao reinsera arquivos
dessa pasta no jogo.

Depois dos exports, todo o restante e executado com um comando:

```powershell
.\atualizar_traducao.ps1 -Etapa atualizar
```

Tambem e possivel clicar em `atualizar_traducao.cmd`. O pipeline:

1. detecta os tres bundles e o `resources.assets` e valida os exports;
2. aplica `memoria_revisado.json` nas tabelas gerais;
3. gera o DialogueDB atual diretamente de `dialogos/memory/memoria.json`;
4. atualiza e aplica `missoes/memoria_missoes.json`, separando as saidas entre
   `defaultlocalgroup/` e `resources_assets/`;
5. audita encoding, nomes de personagens e dialogos ainda em ingles;
6. grava `relatorios/resumo_pipeline_atualizacao.json` com `pronto` ou
   `revisao_necessaria`.

Etapas individuais tambem podem ser usadas:

```powershell
.\atualizar_traducao.ps1 -Etapa gerar
.\atualizar_traducao.ps1 -Etapa validar
```

### Titulos de missoes ja ativas

O jogo salva o titulo da missao de maior prioridade no proprio save, no campo
`Player_Quest_Current_TopPriority_Title`. Alem disso, o historico do jornal le os
titulos das 18 tabelas em `resources.assets`. Portanto, trocar somente o
`defaultlocalgroup_assets_all.bundle` nao cobre nenhuma dessas duas situacoes.

Na verificacao de 15/08/2026, o bundle instalado continha `Uma Arvore Brilhante`,
mas `SaveData_1.es3` ainda guardava `A Shining Tree`. O `Player.log` confirmou que
esse valor foi carregado como `QuestData`. Isso nao indica falha na reinsercao do
bundle. Para corrigir toda a interface, tambem e necessario reinserir os 18 dumps
traduzidos no `resources.assets`; a missao ativa ainda pode manter o valor persistido
ate o save ser atualizado pelo jogo.

Nao edite nem apague saves para corrigir somente um titulo sem antes criar backup.
O arquivo `SaveData_1.es3_meta` tambem e gerado a partir do save e pode precisar ser
reconstruido pelo jogo.
