# Auditoria de nomes de personagens

## Regra

Nomes pessoais permanecem na forma inglesa canônica em todas as traduções. Nomes de
criaturas continuam seguindo as decisões próprias de `GLOSSARIO.md`. Rótulos
descritivos de atores não são tratados automaticamente como nomes pessoais.

O elenco foi conferido no `DialogueDB` exportado e na lista de personagens da wiki.
O auditor também inclui personagens históricos e sobrenomes encontrados no corpus.

## Correções de 15/08/2026

| Forma incorreta | Forma aplicada | Ocorrências em memórias |
| --- | --- | --- |
| Virgílio | Virgil | 4 |
| Teo | Theo | 4 |
| Baobá | Baobab | 8 |
| Áurea | Aurea | 4 |
| Diana | Diane | 2 |
| Rubro | Rubrum | 1 |
| Elliezinha | Ellie II | 1 |

As contagens incluem valores repetidos entre a memória principal de diálogos e o lote
do Translator. Além disso, uma entrada geral que havia omitido a instrução `Talk to
Enite...` foi restaurada com o nome `Enite`, totalizando 25 valores corrigidos nos três
arquivos de memória.

## Validação

- 46 nomes pessoais e sobrenomes auditados;
- 0 nomes exatos alterados;
- 0 nomes ausentes nas traduções;
- 0 violações de grafia canônica;
- 0 chaves adicionadas, removidas ou reordenadas;
- 0 problemas de encoding nos valores.

O identificador interno do personagem Theo é `Teo`. Por isso, comandos Lua e IDs como
`SetFace(Teo, ...)`, `People_Teo` e `BlueprintTeoHouse` devem permanecer inalterados.

Relatórios gerados: `relatorios/auditoria_nomes_personagens.md` e
`relatorios/auditoria_nomes_personagens.json`.
