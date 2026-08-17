# Glossário PT-BR

## Política para nomes de criaturas

Nomes de criaturas podem ser abrasileirados quando a forma em português soar natural
e mantiver a personalidade do original. Depois de aprovado, um nome deve ser idêntico
em interface, itens, enciclopédia, missões e diálogos.

Uma troca não deve ser feita apenas na entrada exata do nome. Também devem ser revistas
frases, plurais, itens derivados e referências indiretas nestas memórias:

- `memoria_revisado.json`
- `dialogos/memory/memoria.json`
- `dialogos/memory/memoria_manual.json`, quando existir
- `dialogos/memory/traduzidas_por_translator.json`

Depois da alteração, os arquivos gerais e os diálogos devem ser regenerados, e as
variantes antigas devem ser procuradas nas saídas.

## Nomes aprovados

| Inglês | PT-BR oficial | Data |
| --- | --- | --- |
| Bush Bug | Inseto do Arbusto | 15/08/2026 |
| Fog Fox | Raposa da Névoa | 15/08/2026 |
| Mimic Jelly | Geléia Mímica | 15/08/2026 |
| Tinkle Spider | Aranha Tilintante | 15/08/2026 |
| Cotton Doggy | Cachorrinho de Algodão | 15/08/2026 |
| Furball Rat | Rato Bola de Pelo | 15/08/2026 |
| Ground Nailer | Cravador de Chão | 15/08/2026 |
| Jelly Shell | Concha de Geléia | 15/08/2026 |
| Buoyancy Herb | Erva Flutuante | 15/08/2026 |
| Dream Orb | Orbe dos Sonhos | 15/08/2026 |
| Moon Brilliance | Brilho Lunar | 15/08/2026 |
| Honey Bear | Ursinho de Mel | 15/08/2026 |
| One Eye Frog | Sapo Caolho | 15/08/2026 |
| Sprout Bird | Passarinho Broto | 15/08/2026 |
| Leafbeaver | Castor-Folha | 15/08/2026 |
| Grass Whistler | Assobiador do Mato | 15/08/2026 |
| Peanut Bat | Morcego-Amendoim | 15/08/2026 |
| Starwhale | Baleia Estelar | 15/08/2026 |
| Gaga Bird | Pássaro Gaga | 15/08/2026 |
| Water Dragonfly | Libélula Aquática | 15/08/2026 |

`Geléia Mímica` mantém o acento por decisão de estilo, mesmo que a ortografia brasileira
atual normalmente escreva `geleia` sem acento.

## Auditoria de consistência

Em 15/08/2026, os quatro nomes do terceiro lote foram conferidos em 122 referências.
Os demais nomes principais foram conferidos em outras 221 referências. Não restaram
variantes antigas nem nomes ingleses inesperados nas traduções auditadas.

Uma revisão posterior encontrou sete traduções novas no lote de 1.158 diálogos e uma
fala antiga na memória geral que não seguiam o padrão de `Little Honey Pumpkin`
(`Little Honey Pumpkins`, `abóbora com mel`, `Abóbora Little Honey` e outras
variantes). Todas foram corrigidas para `Pequena Abóbora Doce`, incluindo plural e
referências ao núcleo. A memória geral e o `DialogueDB` traduzido foram sincronizados
novamente.

No terceiro passe semântico do mesmo lote, as referências genéricas a `Prickly Vine`
e `White Prickly Vine` também foram normalizadas para `Vinha Espinhosa` e
`Vinha Espinhosa Branca`. A capitalização deve ser mantida quando o texto estiver
tratando a planta como o nome da espécie, inclusive dentro de frases.

## Termos gerais aprovados

| Inglês | PT-BR oficial |
| --- | --- |
| Bag Space | Espaço da Bolsa |
| Bitter Grape Tea Tree | Árvore de Chá de Uva Amarga |
| Blue Thunder Workshop | Oficina Trovão Azul |
| Bug Net | Rede de Insetos |
| Furnishing Bell | Sino de Decoração |
| Green Forest Tree Encyclopedia | Enciclopédia de Árvores da Floresta Verde |
| Little Honey Pumpkin | Pequena Abóbora Doce |
| Luna Coin | Moeda Luna |
| Phoenix Feather | Pena de Fênix |
| Potion Recipe | Receita de Poção |
| Prickly Vine | Vinha Espinhosa |
| Records Museum | Museu dos Registros |
| The Silent Guardian | O Guardião Silencioso |
| White Prickly Vine | Vinha Espinhosa Branca |

Flexões de número e gênero devem acompanhar a frase, sem trocar a base aprovada. Por
exemplo: `100 Moedas Luna`, `novas Receitas de Poção` e `Vinhas Espinhosas gigantes`.
Nomes próprios como `Silverrain`, `Blueriver`, `Wisteria`, `Pax`, `Arin` e `Ellie`
permanecem sem tradução.

## Política para nomes de personagens

Nomes pessoais de personagens nunca são traduzidos, aportuguesados, acentuados ou
abreviados. A grafia inglesa canônica deve permanecer em entradas isoladas e em todas
as frases: `Virgil`, `Aurea`, `Diane`, `Rubrum`, `Baobab`, `Ellie` e demais nomes.

O ator `Theo` aparece incorretamente como `Teo` em algumas falas inglesas do próprio
exportado. Nas traduções exibidas, use sempre `Theo`. Não altere identificadores
técnicos como `People_Teo`, `{People.Teo}`, `BlueprintTeoHouse` ou `SetFace(Teo, ...)`.

Essa política não se aplica a nomes de criaturas, que continuam seguindo as tabelas
aprovadas neste glossário, nem a rótulos descritivos como `Bartender` e `Train Crew`.

## Política de gênero nos diálogos

Não inferir gênero por nome, aparência, função narrativa, `Actor` ou `Conversant`.
Esses metadados ajudam a localizar a fala, mas a flexão pessoal só deve ser usada
quando o próprio texto do jogo trouxer evidência explícita. Quando possível, prefira
formas neutras como `agradeço`, `tudo pronto`, `me enganei` e `estou com receio`.

A wiki é apenas uma fonte secundária. Em caso de ausência ou contradição, prevalecem
o corpus local e a redação neutra. Toda exceção deve citar no relatório a frase que
comprova a escolha, como `son` para Pax e `father` para William.

## Consistentes, mas ainda não confirmados

| Inglês | PT-BR atual |
| --- | --- |
| Squishychub | Fofuxo |
| Pumpkin Terrier | Terrier de Abóbora |
| Blue Moon Butterfly | Borboleta da Lua Azul |
| Blue Bubble Lizard | Lagarto Bolha Azul |
| Pompom | Pompom |
| Nectar Moth | Mariposa do Néctar |
| Shroom Raccoon | Guaxinim Cogumelo |
| Crown Mole | Toupeira Coroada |
| Cloud Gecko | Geco da Nuvem |
| Honey Piglet | Leitãozinho de Mel |
| Tail-breathing Croc | Crocodilo Cauda-Respirante |
| Phantom Jellyfish | Água-viva Fantasma |
| Fort Rat | Rato Forte |
| Soil Diver | Mergulhador do Solo |
| Ritoring | Ritoring |
