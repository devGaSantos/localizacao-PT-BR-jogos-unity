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

O segundo comando gera os arquivos em `traduzidos/` e o relatorio em
`relatorios/relatorio_translate_missoes.json`. O script nao remove arquivos antigos
da pasta de saida, exceto por separar com seguranca qualquer `base-*` em
`nao_importar/`. Mantenha juntos os 10 dumps `CAB-*` importaveis e os 18 dumps
`*-resources.assets-*`; os nomes dos arquivos distinguem o destino de reinsercao.

Esse script cobre os dois conjuntos de `TextTable`. `Post`, `QuestUI` e `QuestNode`
continuam no fluxo geral de `memoria_revisado.json`.

Na validação de 15/08/2026, os 11 arquivos do bundle foram processados, incluindo
indevidamente o `base`, com
132 substituições, zero faltantes e zero erros. Essa validação não cobria o histórico
do jornal e nao deve ser repetida: processe somente os 10 importaveis mais os 18
exports atuais de `resources.assets`.

## Pipeline automatizado de atualizacao

O orquestrador `atualizar_traducao.ps1` coordena os textos gerais, dialogos, missoes
e auditorias. Ele nunca altera diretamente a instalacao do jogo.

### Passo a passo recomendado

1. Feche o jogo e deixe a Steam concluir qualquer atualizacao.
2. Dentro de `LW`, execute `atualizar_traducao.ps1 -Etapa status` para conferir os
   hashes e quais exports ainda pertencem a versao anterior.
3. Execute `atualizar_traducao.ps1 -Etapa preparar`. O comando copia os quatro
   artefatos atuais do jogo para `LW/atualizacao/bundles_originais/`, sem alterar a
   instalacao.
4. No editor de assets, exporte 26 tabelas gerais, 1 `DialogueDB_en-*`, 10 tabelas
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

O pipeline automatiza copia segura, aplicacao das memorias, geracao e auditoria. A
exportacao e a reinsercao ainda sao manuais porque a ferramenta grafica de assets nao
esta integrada por CLI.

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

As copias ficam em `atualizacao/bundles_originais/`. Enquanto nao houver uma
ferramenta de bundles com CLI configurada, use o editor grafico para exportar:

- 26 tabelas gerais para `LW/exportados/`;
- 1 `DialogueDB_en-*` para `LW/dialogos/exportados/`;
- 10 `TextTable` `CAB-*` importaveis do `defaultlocalgroup` para
  `missoes/exportados/`;
- nao exporte nem importe `base`; se exportar por engano, o script ira ignora-lo;
- 18 `TextTable` `*-resources.assets-*` para `missoes/exportados/`.

Depois dos exports, todo o restante e executado com um comando:

```powershell
.\atualizar_traducao.ps1 -Etapa atualizar
```

Tambem e possivel clicar em `atualizar_traducao.cmd`. O pipeline:

1. detecta os tres bundles e o `resources.assets` e valida os exports;
2. aplica `memoria_revisado.json` nas tabelas gerais;
3. gera o DialogueDB atual diretamente de `dialogos/memory/memoria.json`;
4. atualiza e aplica `missoes/memoria_missoes.json`;
5. audita encoding, nomes de personagens e dialogos ainda em ingles;
6. grava `relatorios/resumo_pipeline_atualizacao.json` com `pronto` ou
   `revisao_necessaria`.

Etapas individuais tambem podem ser usadas:

```powershell
.\atualizar_traducao.ps1 -Etapa gerar
.\atualizar_traducao.ps1 -Etapa validar
```

A extracao e a reinsercao nos bundles ainda sao manuais. Para automatiza-las sem
risco, sera necessario configurar a ferramenta exata usada para editar os bundles e
confirmar que ela oferece CLI ou API de importacao/exportacao.

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
