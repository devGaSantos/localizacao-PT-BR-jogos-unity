# Localização PT-BR para jogos Unity

Projeto de engenharia de localização e manutenção de traduções comunitárias para
**Little Witch in the Woods** e **Chef RPG**. O repositório mantém as memórias de
tradução, os pipelines reprodutíveis e a documentação técnica usados para produzir
as distribuições publicadas no Nexus Mods.

> Projeto comunitário e não oficial. Não é afiliado a Sunny Side Up,
> SKONEC Entertainment, Steam ou Nexus Mods.

## Releases para jogadores

| Jogo | Distribuição | Instalação |
| --- | --- | --- |
| Little Witch in the Woods | [Nexus Mods](https://www.nexusmods.com/littlewitchinthewoods/mods/14) | Pacote publicado no Nexus |
| Chef RPG | [Nexus Mods](https://www.nexusmods.com/chefrpg/mods/42) | Copie `Chef RPG_Data` para a pasta raiz do jogo |

Os arquivos de release não são versionados aqui: eles são gerados a partir das
memórias e publicados no Nexus. Isso mantém o histórico Git leve e o código-fonte
auditável.

## O que este repositório demonstra

- leitura e reconstrução de assets Unity com AssetsTools.NET;
- memória de tradução versionada e aplicada de forma determinística;
- validação que bloqueia a geração quando existirem textos sem tradução;
- tratamento de dados corrompidos, como valores vazios ou preenchidos só com `#`;
- pacotes manuais mínimos, com instruções de reversão pela verificação de
  integridade da Steam.

## Estrutura

```text
CHEFRPG/       pipeline, memória e documentação do Chef RPG
LW/            pipeline, memórias e documentação do Little Witch in the Woods
missoes/       memória e fontes das tabelas de missões do Little Witch
docs/          visão de arquitetura e contribuição
```

Consulte [a arquitetura](docs/ARCHITECTURE.md) antes de alterar um pipeline e
[as orientações de contribuição](CONTRIBUTING.md) antes de abrir um PR.

## Princípios de manutenção

1. A memória de tradução é a fonte de verdade; dumps e pacotes são derivados.
2. Cada build é validado contra os assets da versão instalada do jogo.
3. Traduções novas passam por revisão humana antes da publicação oficial.
4. Arquivos de build, backups e relatórios transitórios não entram no Git.

## Ambiente técnico

Os pipelines usam PowerShell, .NET 8 e AssetsTools.NET. Os usuários finais não
precisam instalar essas dependências para aplicar os pacotes manuais.
