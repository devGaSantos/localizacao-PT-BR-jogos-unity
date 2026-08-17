# Auditoria de encoding das memórias

Data: 15/08/2026

## Arquivos verificados

- `dialogos/memory/traduzidas_por_translator.json`
- `dialogos/memory/memoria.json`
- `memoria_revisado.json`

## Resultado final

Os três arquivos foram decodificados com UTF-8 estrito e interpretados como JSON sem
erros. Nos valores traduzidos PT-BR, o resultado foi:

- 0 caracteres de substituição `U+FFFD`;
- 0 sequências típicas de mojibake;
- 0 pontos de interrogação substituindo letras dentro de palavras;
- 0 caracteres de largura zero ou controles invisíveis;
- 0 controles ASCII inválidos;
- 0 BOM UTF-8;
- 0 tags, comandos Lua ou quebras `\r` divergentes nas traduções revisadas;
- 0 valores divergentes entre o lote do Translator e a memória de diálogos.

## Problemas encontrados e corrigidos

A comparação histórica mostrou que o lote antigo de faltantes havia introduzido 39
pontos de interrogação no lugar de acentos em 35 entradas de `memoria_revisado.json`.
Todos foram corrigidos, incluindo `Incensário`, `Árvore`, `Exploração`, `Enciclopédia`,
`Alguém`, `Papéis`, `Você não`, `Nível`, `Preço`, `Espaço`, `Visualização` e `confiança`.

Uma segunda varredura, ampliada para um ou mais `?` consecutivos e para acentos
quebrados no fim de palavras, encontrou outras 11 entradas gerais. Foram corrigidos,
entre outros, `Decoração`, `Poção`, `Maldição`, `Respiração`, `Adoção`, `Recuperação`,
`Vibração`, `Criação`, `atualização` e `Nó`. No total, 63 pontos de interrogação que
substituíam letras foram eliminados de 46 entradas da memória geral.

Na memória de diálogos, `"What? Why not?"` estava como `"O quê? Por que??"` e foi
corrigido para `"O quê? Por que não?"`. As outras ocorrências de `??` e `???` foram
preservadas porque a mesma pontuação expressiva existe nas respectivas chaves inglesas.

Também foram removidos 12 caracteres invisíveis encontrados somente nos valores:

- 6 em três traduções da memória geral;
- 2 em uma tradução do lote do Translator;
- 4 na memória de diálogos, incluindo a cópia da entrada do Translator.

## Caracteres preservados nas chaves

Três caracteres `U+200C` continuam presentes apenas em chaves inglesas de
`memoria_revisado.json`:

- duas chaves relacionadas a `Starwhale`;
- a chave `Cat Adoption`.

Eles já existiam em `memoria_revisado.before_faltantes_20260815.json`, antes dos lotes
auditados. Não aparecem nos valores PT-BR e foram preservados porque remover ou alterar
uma chave pode impedir que a memória reconheça exatamente a string exportada do jogo.

## Contagens contra os backups

- Translator: 169 valores alterados, sendo 168 revisões textuais e 1 limpeza técnica;
- memória de diálogos: 172 valores alterados, sendo as alterações sincronizadas, uma
  limpeza adicional de entrada antiga, a correção de `Por que não?` e uma frase de
  confirmação de compra que ainda permanecia em inglês;
- memória geral: 50 valores alterados contra o backup anterior à revisão de diálogos,
  compostos pelas correções de encoding, três limpezas invisíveis e `Sino de Decoração`;
- 0 chaves adicionadas ou removidas nos três arquivos.

## Evidências

O resultado completo mais recente, com hashes SHA-256, está em
`relatorios/auditoria_encoding_completa.json`. A primeira passagem foi preservada em
`relatorios/auditoria_encoding_memorias_20260815.json` como histórico.

Para repetir a auditoria após qualquer alteração ou regeneração:

```powershell
node auditar_encoding_memorias.js
```

O comando retorna código diferente de zero se encontrar problema nos valores.

Backups imediatamente anteriores à limpeza:

- `memoria_revisado.before_correcao_encoding_20260815.json`
- `dialogos/memory/memoria.before_correcao_encoding_20260815.json`
- `dialogos/memory/traduzidas_por_translator.before_correcao_encoding_20260815.json`
- `memoria_revisado.before_correcao_encoding_lote2_20260815.json`
- `dialogos/memory/memoria.before_correcao_encoding_lote2_20260815.json`
