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

1. coluna `br` do asset atual do jogo, quando for válida;
2. `memoria.json`, quando `br` estiver vazio ou inválido;
3. bloquear e relatar, quando nenhuma traducao existir.

Valores em branco ou compostos apenas por `#` são inválidos. Eles nunca contam como
tradução existente e não são propagados para o pacote.

No arquivo reconstruido, o portugues escolhido e aplicado em `br` e tambem em `en`
para manter compatibilidade com o mod antigo, que executava o jogo no idioma ingles.
Durante o build, as traducoes `br` atuais dos desenvolvedores tambem sao gravadas em
`memoria.json`, mantendo o mesmo comportamento do script convencional antigo.

## Preparacao unica

O pipeline ja inclui `tools/asset-pipeline/lib/AssetsTools.NET.dll` e
`tools/asset-pipeline/lib/classdata.tpk`. Portanto, **nao e preciso instalar nem
abrir UABEA** para manter a traducao. A unica dependencia de manutencao e o .NET 8
SDK; o comando abaixo instala uma copia local dele caso necessario:

```powershell
.\preparar_pipeline_assets.ps1
```

As ferramentas locais ficam em `.tools/` e nao entram no Git. O parametro
`-UabeaZip` continua apenas como alternativa de recuperacao caso o arquivo incluso
seja removido.

## Atualizacao do jogo

### Manutenção

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

O modo `analisar` não altera o jogo. Revise os faltantes manualmente e insira-os em
`memoria.json`. Depois, execute o fluxo completo:

```powershell
.\atualizar_traducao.ps1 -Etapa automatico
```

O comando le sempre o `resources.assets` vivo da Steam, reconstroi uma copia em
`atualizacao/staging/`, reabre o asset, valida as cinco tabelas e gera:

`atualizacao/pacote_merlin/Chef RPG_Data/resources.assets`

O pacote só deve ser publicado depois da validação sem pendências. O pipeline
preserva nomes associados a `character_name_*`, tags e placeholders.

## Escopo seguro da publicacao

O pacote publico contem **somente** `Chef RPG_Data/resources.assets`. Esse unico
arquivo contem as cinco tabelas acima (25.768 registros na versao validada).

Os arquivos `level*` de cena/UI nao fazem parte da traducao e nao entram no projeto
nem no pacote. Os textos publicados ficam somente nas cinco tabelas de
`resources.assets`.

## UABEA: quem precisa dele?

Quem instala o mod pelo Nexus **nao precisa de UABEA**, Python, .NET ou qualquer
outro programa. Basta copiar o arquivo entregue para a pasta do jogo.

Para manter ou atualizar a traducao, o pipeline usa o `classdata.tpk` e a biblioteca
`AssetsTools.NET.dll` incluidos em `tools/asset-pipeline/lib/`. A interface grafica
do UABEA nao precisa ficar instalada nem e usada para gerar ou aplicar o pacote; ela
e apenas uma ferramenta opcional de inspecao.

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
- `memoria.json` é a memória principal e nunca deve ser apagada durante uma
  atualização.
