# Little Witch in the Woods — Tradução PT-BR

## Para jogadores

1. Extraia `Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip` em uma pasta permanente.
2. Abra `LittleWitch.Launcher.exe` para jogar.
3. Na primeira execução, selecione a pasta do jogo caso a Steam não seja detectada.

O launcher acompanha a versão instalada. Quando a Steam atualizar os assets do jogo,
ele reconstrói e reinstala a tradução automaticamente. UABEA, .NET e Python não são
necessários para quem usa o pacote.

## Manutenção da tradução

As memórias são separadas por tipo de conteúdo:

- `memoria_revisado.json`: interface, itens e textos gerais;
- `dialogos/memory/memoria.json`: diálogos;
- `../missoes/memoria_missoes.json`: tabelas de missões.

O pipeline processa quatro assets: a tabela geral de localização, `dialoguedb`,
tabelas de missões e `resources.assets`. Ele só conclui uma compilação normal quando
todas as strings encontradas estão presentes nas memórias.

## Publicação e verificação

Execute `./publicar_atualizador.ps1` a partir da raiz do repositório para gerar:

`dist/Little_Witch_in_the_Woods_PT-BR_AutoUpdater.zip`

Antes da publicação deste pacote, a instalação atual da Steam foi reconstruída e
verificada em modo estrito: 8.656 strings gerais, 39.063 diálogos, 126 entradas de
missão e 159 recursos de missão, todos sem pendências.
