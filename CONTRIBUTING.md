# Contribuindo

Obrigado por ajudar a manter as traduções. Este é um projeto de localização com
arquivos de jogo binários: uma alteração aparentemente pequena pode quebrar um
asset inteiro. Prefira mudanças pequenas, verificáveis e documentadas.

## Antes de editar

1. Use a instalação mais recente do jogo pela Steam como fonte dos assets.
2. Atualize a memória apropriada, nunca um pacote de distribuição diretamente.
3. Preserve tags, marcadores, chaves e sequências de escape do texto original.
4. Não considere valores vazios ou compostos apenas por `#` como traduções válidas.

## Validação local

No diretório do jogo correspondente, execute o pipeline em modo de análise antes
de criar um pacote. O processo precisa terminar sem textos pendentes. No Chef RPG,
por exemplo:

```powershell
cd CHEFRPG
.\atualizar_traducao.ps1 -Etapa analisar
.\atualizar_traducao.ps1 -Etapa pacote
```

O Little Witch in the Woods possui fluxos separados para interface, diálogos e
missões; consulte `LW/docs/FLUXO_TRADUCAO.md`.

## O que não versionar

Não envie ZIPs de release, pastas de staging, backups, binários compilados,
relatórios temporários ou cópias de `resources.assets`. Eles são reproduzíveis e
estão excluídos pelo `.gitignore`.

## Pull requests

Explique a versão do jogo usada, quais memórias foram alteradas, o resultado da
validação e qualquer texto que precise de revisão contextual. Não inclua conteúdo
extraído que não seja necessário para reproduzir a tradução.
