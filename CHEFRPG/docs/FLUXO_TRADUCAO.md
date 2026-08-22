# Fluxo de traducao do Chef RPG

## Estrutura atual

Chef RPG usa Unity `2019.4.41f2` com backend Mono. Os textos ficam em cinco
`TextAsset` CSV dentro de `Chef RPG_Data/resources.assets`:

- `Romance Localization`;
- `Localization`;
- `UI Localization`;
- `Festivals Localization`;
- `Item Localization`.

Cada CSV possui as colunas `key`, `en` e `br`. O pipeline preserva todas as outras
linguas e usa esta prioridade para o texto em portugues:

1. coluna `br` do asset atual do jogo;
2. `memoria.json`, quando `br` estiver vazio;
3. bloquear e relatar, quando nenhuma traducao existir.

No arquivo reconstruido, o portugues escolhido e aplicado em `br` e tambem em `en`
para manter compatibilidade com o mod antigo, que executava o jogo no idioma ingles.
Durante o build, as traducoes `br` atuais dos desenvolvedores tambem sao gravadas em
`memoria.json`, mantendo o mesmo comportamento do script convencional antigo.

## Preparacao unica

Coloque `uabea-windows.zip` em `Downloads` e execute:

```powershell
.\preparar_pipeline_assets.ps1
```

As ferramentas locais ficam em `.tools/` e nao entram no Git.

Para permitir que `automatico` traduza textos novos, instale uma vez:

```powershell
python -m pip install deep-translator
```

Essa dependencia nao e necessaria para `status` ou `analisar`.

## Atualizacao do jogo

No Prompt de Comando (CMD), use o lancador `.cmd`:

```batch
atualizar_traducao.cmd analisar
atualizar_traducao.cmd automatico
```

Sem argumento, `atualizar_traducao.cmd` executa `automatico`. Arquivos `.ps1` devem
ser executados pelo PowerShell; tentar abri-los diretamente no CMD mostra a janela
"Selecione um aplicativo para abrir este arquivo".

Primeiro analise o asset instalado sem modificar o jogo:

```powershell
.\atualizar_traducao.ps1 -Etapa analisar
```

Os resultados ficam em:

- `relatorios/chef_rpg_pipeline.json`: cobertura completa por tabela;
- `relatorios/faltantes_memoria.json`: textos ingleses unicos ainda sem traducao.

O modo `analisar` nao chama traducao automatica. Para revisar manualmente, insira os
faltantes em `memoria.json`. Para executar o fluxo completo, use:

```powershell
.\atualizar_traducao.ps1 -Etapa automatico
```

O comando le sempre o `resources.assets` vivo da Steam, reconstroi uma copia em
`atualizacao/staging/`, reabre o asset, valida as cinco tabelas e gera:

`atualizacao/pacote_merlin/Chef RPG_Data/resources.assets`

Se houver textos novos, `automatico` usa `deep-translator`, cria um backup datado de
`memoria.json`, preserva nomes associados a `character_name_*`, protege tags e
placeholders e reexecuta a analise. As traducoes automaticas devem ser revisadas
linguisticamente antes de publicar o pacote.

Arraste `Chef RPG_Data` para a raiz `Chef RPG` e confirme a substituicao. Para
recriar apenas o pacote usando um staging ja validado:

```powershell
.\atualizar_traducao.ps1 -Etapa pacote
```

Para instalar diretamente com backup:

```powershell
.\atualizar_traducao.ps1 -Etapa instalar -ConfirmarInstalacao
```

## Seguranca

- `analisar` nunca escreve no jogo;
- `automatico` nunca escreve no jogo;
- faltantes impedem a geracao;
- o asset e reaberto e validado antes do pacote;
- `instalar` exige confirmacao, jogo fechado e cria backup datado;
- `script_translation_batch.py`, `exportados/` e `traduzidos/` continuam disponiveis
  como fluxo convencional.
