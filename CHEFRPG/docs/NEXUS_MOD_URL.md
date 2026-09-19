# Página Nexus Mods

- Chef RPG — Tradução PT-BR: <https://www.nexusmods.com/chefrpg/mods/42>

Antes de publicar, valide a tradução contra o `resources.assets` instalado pela
Steam. Registre o `buildid` do `appmanifest_1796790.acf` junto com a versão do
pacote manual para evitar publicar arquivos de uma atualização anterior.

> O `buildid` é um indicador útil, mas não substitui a validação do asset. Uma
> revisão distribuída pela Steam pode alterar tabelas de localização sem mudar a
> versão exibida pelo jogo. Sempre execute `atualizar_traducao.ps1 -Etapa analisar`
> contra a instalação recém-atualizada e gere o pacote somente se o relatório não
> tiver entradas pendentes.
