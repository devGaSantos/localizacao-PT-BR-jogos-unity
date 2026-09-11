# Texto para a página do Nexus Mods

## Título

Chef RPG — Tradução PT-BR

## Resumo

Tradução para português do Brasil de diálogos, menus, romances, festivais e itens
de Chef RPG, com atualizador automático para acompanhar atualizações da Steam.

## Descrição

Este mod inclui um launcher que reaplica a tradução automaticamente quando uma
atualização da Steam substitui `Chef RPG_Data/resources.assets`. Não requer UABEA,
BepInEx, Python ou .NET instalado.

Instalação: extraia o ZIP em uma pasta permanente e abra `ChefRpg.Launcher.exe`
sempre que for jogar. Na primeira execução, se a Steam estiver instalada em uma
biblioteca diferente, informe a pasta de Chef RPG. Em **Propriedades > Idioma**,
mantenha o jogo em **English**: a tradução substitui a tabela inglesa usada pelo mod.

O atualizador cria um backup antes de trocar o asset. Caso uma versão do jogo
adicione textos ainda não revisados, esses trechos permanecem em inglês até a
próxima atualização do mod; o restante da tradução continua funcionando.

Este lançamento não inclui os arquivos de cena `level*`; eles não são necessários
para a tradução principal e foram excluídos por segurança.

## Arquivo para enviar

`Chef_RPG_PT-BR_AutoUpdater.zip`

## Detalhes técnicos para mantenedores

- O ZIP inclui o pipeline publicado como executável autocontido para Windows x64,
  a memória de tradução e o `classdata.tpk` necessário para abrir os assets Unity.
- UABEA/AssetsTools não é necessário para usuários do Nexus.
