# Nexus: referência de envio de arquivo

Página do mod: <https://www.nexusmods.com/littlewitchinthewoods/mods/14>.

## Pacote manual

Antes de enviar, valide que o ZIP não contém outro ZIP da instalação. O pacote
publicado deve conter apenas os arquivos que a pessoa copiará para a pasta do
jogo (por exemplo, `LWIW_Data/` e o README de instalação).

## Formulário de arquivos

O seletor de arquivo do Nexus é um `input[type="file"].hidden`. Quando o clique
não abrir o seletor, o caminho confiável no navegador automatizado é focar o
contêiner com `aria-label="Add file"`, pressionar `Enter` e aguardar o evento
`filechooser` antes de usar `setFiles`.

Para publicar uma atualização existente, escolha **Update existing file** e,
no combobox `Select existing file`, selecione o arquivo principal. O teclado
`ArrowDown` seguido de `Enter` funciona mesmo quando a lista visual não abre.

Depois, preencha `Display name`, `File version` e, se necessário, `Changelog
entry`; por fim use `Save file`. O botão final altera o arquivo público do mod,
portanto confira o nome, versão e conteúdo antes de salvar.
