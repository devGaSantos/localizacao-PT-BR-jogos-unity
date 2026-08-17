# Revisão do Translator nos diálogos

## Escopo

Em 15/08/2026, as 1.158 entradas de
`dialogos/memory/traduzidas_por_translator.json` foram comparadas com o inglês,
com a memória revisada anterior e com o contexto de atores do `DialogueDB` exportado.

O lote já estava inserido em `dialogos/memory/memoria.json`. A revisão alterou 168
traduções e sincronizou os mesmos valores nos dois arquivos. Nenhuma chave foi criada
ou removida.

## O que foi revisado

- coerência com nomes de criaturas e termos já aprovados;
- concordância de gênero, especialmente falas de e para Ellie e Diane;
- sentido de frases traduzidas literalmente ou com omissões;
- títulos, itens, locais e termos de interface;
- texto inglês restante dentro de marcações de ênfase;
- preservação de `[em1]`, `<shake>`, tags de fonte, comandos Lua e quebras `\r`;
- consistência entre o arquivo do Translator e a memória usada na regeneração.

## Resultado da validação

- 1.158 entradas verificadas;
- 168 traduções corrigidas;
- 0 chaves adicionadas ou removidas;
- 0 entradas ausentes ou divergentes em `dialogos/memory/memoria.json`;
- 0 tags, comandos Lua ou quebras `\r` perdidos;
- 0 traduções vazias;
- 0 nomes ingleses restantes entre as criaturas já aprovadas;
- 0 conflitos entre fontes equivalentes normalizadas.

Seis valores permanecem iguais ao inglês de propósito: dois contêm somente comandos
Lua, dois são risadas, um contém apenas nomes próprios e um usa a expressão latina
`Magna cum laude`.

Uma segunda auditoria tornou neutras as construções pessoais cujo gênero não estava
explicitamente comprovado pelo texto inglês. Os campos `Actor` e `Conversant` servem
para localizar o contexto, mas não bastam sozinhos para atribuir gênero. Consulte
`docs/RELATORIO_FINAL_REVISAO_TRANSLATOR.md` para o histórico completo de cada mudança.

Depois dessa revisão, uma auditoria de encoding removeu dois caracteres invisíveis de
uma das 1.158 traduções. Por isso, a comparação técnica final com o backup apresenta
169 valores alterados: 168 revisões textuais e uma limpeza técnica. Consulte
`docs/AUDITORIA_ENCODING_MEMORIAS.md`.

Uma auditoria posterior de valores idênticos encontrou as frases
`Daughter of Aria and Aiden Blueriver.` e `Now that the name appeared on the
certificate, Ellie Blueriver, I recognize your graduation.` ainda em inglês fora do
lote do Translator. Elas foram corrigidas na memória e na saída atual.

O auditor permanente `auditar_dialogos_nao_traduzidos.js` examina as 48.629 entradas
inglesas do exportado. Em 15/08/2026, ele encontrou 150 frases integralmente em inglês,
nenhuma chave ausente ou vazia e nenhuma tradução da memória pendente de aplicação na
saída. A lista completa está em `relatorios/auditoria_dialogos_nao_traduzidos.md`; os
casos ambíguos, nomes, comandos e efeitos estão separados no relatório JSON.

As 150 identidades linguísticas foram posteriormente revisadas e traduzidas: 148 vieram
da lista confirmada e outras duas (`Hmm... Alright.` e `*Gags*`) foram encontradas na
revisão manual dos casos curtos ambíguos. `Vine Deli` foi preservado como nome próprio
do estabelecimento, e `<wave>Do-do-fa! Sol-la! Sol-fa!</wave>` como sequência musical.
Depois da sincronização, o auditor registrou 0 frases confirmadas em inglês e 0 valores
da memória pendentes na saída.

As identidades restantes são nomes próprios, comandos Lua, identificadores, datas,
onomatopeias, interjeições ou termos que têm a mesma grafia em português, como
`Chocolate`, `Origami`, `Tutor` e `Familiar`.

Uma nova revisão do arquivo completo de 1.158 entradas confirmou que o anexo recebido
era idêntico ao lote do Translator e já estava integralmente inserido na memória. Uma
primeira passagem semântica adicional corrigiu 23 valores nas duas memórias, incluindo
pronomes de `broom`, `Eu sei que.`, `Paxs`, `Olhar! Essa gaveta!`, inglês residual,
concordância e traduções literais no prólogo do trem e no Museu dos Registros. O
DialogueDB foi sincronizado sem chamar tradução automática. A revisão humana integral
deve continuar por blocos; não considerar apenas a checagem estrutural como aprovação
semântica das 1.158 entradas.

Uma segunda passagem semântica completa corrigiu mais 98 entradas distintas no lote do
Translator e 194 entradas na memória geral. A diferença existe porque a memória geral
ainda continha interjeições antigas em inglês fora do lote, principalmente `Huh`,
`Ugh`, `Sniff` e `O-okay`. Também foram corrigidos:

- sete usos inconsistentes de `Little Honey Pumpkin` no lote e uma fala antiga na
  memória geral, todos normalizados para `Pequena Abóbora Doce` e suas flexões;
- traduções literais como `violador de regras`, `comi uma única mordida`,
  `páginas que estão circulando` e `olhar ao redor completamente`;
- concordância em `cada poção e cada doce certamente terá`;
- flexões pessoais sem prova textual, substituídas por construções neutras;
- referências a `master witch`, padronizadas neste lote como `autoridade de bruxaria`
  quando o inglês não comprova o gênero da pessoa;
- interjeições e palavras ainda em inglês, sem alterar nomes de personagens.

O segundo passe também detectou e corrigiu um efeito colateral da normalização:
`Uh-huh` havia se tornado `Uh-Hã` em duas falas antigas e agora aparece como `Aham`.
Depois da sincronização, 248 ocorrências do `DialogueDB` traduzido foram atualizadas.

Validação final do segundo passe:

- 1.158 entradas do Translator iguais às entradas correspondentes da memória geral;
- 0 divergências entre as duas memórias;
- 0 resíduos ingleses de alta confiança nos valores do lote;
- 0 problemas de encoding nos valores;
- 0 diferenças em tags, comandos Lua, placeholders ou quebras `\r`;
- 0 nomes canônicos de personagens alterados;
- 0 entradas ausentes, vazias ou não aplicadas na saída;
- 6 identidades intencionais: dois comandos Lua, duas risadas, uma frase formada por
  nomes próprios e `Magna cum laude, Ellie Blueriver.`.

O histórico completo, com original, valor anterior e valor final, está em
`relatorios/revisao_lote_dialogos_passe2_20260815.json`.

## Terceiro passe: calques literais

Uma terceira revisão foi iniciada depois da identificação de
`Go chase the cat right away!!` como `Vá perseguir o gato imediatamente!!`. Embora a
frase estivesse gramaticalmente montada, `chase` nesse contexto significa ir atrás do
gato, e não persegui-lo em sentido hostil. A tradução final ficou:

`Vá atrás do gato agora mesmo!!`

A busca foi ampliada para imperativos e construções frequentes do Translator, como
`go`, `come`, `look`, `check out`, `let me`, `make sure`, `I wonder` e `keep in mind`.
Foram corrigidas 86 entradas nas duas memórias, incluindo:

- `Vou me certificar de fazer isso` para `Pode deixar`;
- `obra-prima criada com minha vida` para `obra-prima da minha vida`;
- `dar uma olhada um pouco mais` para `procurar mais um pouco`;
- `Deixe-me dar-lhe` para formas naturais como `aqui estão`, `tome isto` e `vou
  explicar`, conforme o contexto;
- `eu estava sendo perseguido` para `estavam correndo atrás de mim`, sem atribuir
  gênero ao falante;
- `processo de elaboração` para `como prepará-lo`;
- imperativos formais ou literais para formas naturais em PT-BR;
- usos inconsistentes de `Vinha Espinhosa` e `Vinha Espinhosa Branca` dentro do lote.

O `DialogueDB` foi sincronizado e 92 ocorrências foram atualizadas. A validação final
do terceiro passe registrou:

- 0 divergências entre o lote e a memória geral;
- 0 alterações em tags, comandos Lua, placeholders ou quebras `\r`;
- 0 problemas de encoding;
- 0 nomes canônicos de personagens alterados;
- 0 entradas ausentes, vazias ou não aplicadas;
- 0 ocorrências restantes dos padrões literais pesquisados.

O relatório completo está em
`relatorios/revisao_calques_dialogos_lote3_20260815.json`.

## Quarto passe: bolsa no prologo do trem

A fala `I placed the bag on top so it wouldn't fall.` foi corrigida de
`Coloquei a sacola em cima para não cair.` para
`Coloquei a bolsa lá em cima para que ela não caísse.`. O novo valor mantém o termo
`bolsa`, usado nas falas seguintes, explicita que é a bolsa que poderia cair e preserva
o relato no passado com `caísse`.

A revisão contextual das conversas do mesmo evento corrigiu onze entradas nas duas
memórias. Também foram alinhados o pronome feminino de `bolsa`, a retomada feminina de
`páginas`, o sentido de `approach` como `aproximar-se`, a hesitação de `Le-let's`, as
ocorrências isoladas de `sacola` e o tempo verbal de `The flower garden disappears on
its own.`. Em `Opening/ExplodeSuitcase/PaperCollectComplete`, o jardim já desapareceu;
por isso, a tradução passou a ser `O jardim de flores desapareceu sozinho.`. A pessoa
misteriosa continuou referida de forma neutra, sem suposição de gênero.

As sincronizações do DialogueDB registraram onze substituições e zero entradas
ausentes. A auditoria de encoding encontrou zero problemas nos valores da memória de
diálogos.

## Quinto passe: conjugação, concordância e traduções literais

Foi feita uma nova leitura automatizada das 34.470 entradas de
`dialogos/memory/memoria.json`, ligada ao contexto de 48.629 ocorrências no
`DialogueDB`. O índice registra ator, interlocutor, conversa e linha do exportado para
impedir que uma flexão seja alterada apenas por suposição.

Foram corrigidas 298 entradas distintas:

- 188 correções contextuais explícitas de conjugação, concordância, regência e
  traduções literais;
- 110 flexões de primeira pessoa alinhadas ao personagem confirmado;
- usos literais de `I wonder`, `make sure`, `eventually`, `for now`, `sounds`,
  `check out`, `take your time`, `ser capaz de` e `de alguma forma`;
- futuro do subjuntivo em `Se você vir um quebra-cabeça`;
- concordâncias como `isso são aventuras`, `humano` para Lisa, `um explorador` e
  `encorajador` dirigidos a Ellie;
- saudações e adjetivos dirigidos a Ellie, sem confiar cegamente no campo
  `Conversant`, que em algumas conversas aponta para o próprio falante;
- formulações neutras para Laurel, Baobab, Deus Gato Branco, Guardião Silencioso e
  falas sem ator identificado, pois o contexto local não comprova gênero.

Duas ocorrências de `obrigado` faladas por Ellie foram mantidas intencionalmente. Em
uma, Ellie relata que Arden disse `obrigado`; na outra, ela diz a Theo que ele poderia
ter falado `obrigado`. A flexão pertence ao homem citado, não a Ellie.

Os resíduos do auditor também foram revisados. `Nós éramos amigas`, `haviam
desaparecido`, `haviam morrido` e `haviam sido concluídos` estão corretos. Os usos
restantes de `deixe-me`, `dar uma olhada` e `olhar para` fazem sentido em seus
contextos; apenas os casos artificiais foram reescritos. Os três usos restantes de
`soa` descrevem voz ou uma fórmula solene, não o calque de `sounds like`.

Resultado da validação:

- 0 alterações em `traduzidas_por_translator.json`; as 7 entradas desse lote que
  receberam correções permanecem diferentes da memória principal de propósito;
- 319 ocorrências mantidas pendentes no `DialogueDB` traduzido, pois este passe altera
  somente os JSONs de memória;
- 0 entradas ausentes da memória;
- 0 falas confirmadas em inglês;
- 0 problemas de encoding em chaves ou valores da memória de diálogos;
- 0 alterações de nomes canônicos de personagens;
- 0 quebras em tags, comandos Lua ou marcadores `\r` nas correções;
- 1 falso positivo de inglês parcial: `Little Witch in the Woods`, mantido como título
  oficial do jogo.

O histórico cumulativo com fonte, valor anterior, valor final, motivo e contexto está
em `relatorios/revisao_linguistica_dialogos_20260815.json`. O aplicador reproduzível e
idempotente é `aplicar_revisao_linguistica_dialogos.js`.

Os arquivos `dialogos/memory/traduzidas_por_translator.json` e
`dialogos/traduzidos` não fazem parte deste passe. As correções ficam somente em
`dialogos/memory/memoria.json` e só devem ser propagadas durante uma regeneração
solicitada explicitamente.

## Arquivos alterados

- `dialogos/memory/traduzidas_por_translator.json`
- `dialogos/memory/memoria.json`
- `memoria_revisado.json` (uma ocorrência de `Furnishing Bell`)
- `docs/GLOSSARIO.md`

## Backups

- `dialogos/memory/traduzidas_por_translator.before_revisao_20260815.json`
- `dialogos/memory/memoria.before_revisao_translator_20260815.json`
- `memoria_revisado.before_revisao_dialogos_20260815.json`
- `dialogos/memory/traduzidas_por_translator.before_revisao_total_lote2_20260815.json`
- `dialogos/memory/memoria.before_revisao_total_lote2_20260815.json`
- `dialogos/memory/traduzidas_por_translator.before_revisao_calques_lote3_20260815.json`
- `dialogos/memory/memoria.before_revisao_calques_lote3_20260815.json`
- `dialogos/memory/traduzidas_por_translator.before_revisao_linguistica_20260815.json`
- `dialogos/memory/memoria.before_revisao_linguistica_20260815.json`

## Próximo ciclo

Ao receber um novo lote do Translator, ele deve ser revisado antes da regeneração dos
diálogos. Depois da aprovação, copie cada valor corrigido para
`dialogos/memory/memoria.json`, valide as marcações e só então execute
`script_translation_batch.py` para gerar novamente `dialogos/traduzidos`.
