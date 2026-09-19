# Arquitetura dos pipelines

## Fonte de verdade

As memórias JSON são a camada editável e versionada. Os assets Unity, dumps de
inspeção e ZIPs de distribuição são produtos derivados. Esse limite evita que uma
atualização seja corrigida manualmente em um binário sem que a correção fique
reutilizável na atualização seguinte.

## Fluxo comum

```text
Assets da Steam -> leitura das tabelas -> memória PT-BR -> validação -> asset reconstruído -> pacote Nexus
```

O pipeline preserva o texto original quando ainda não existe tradução válida e
interrompe a geração oficial quando a memória não cobre novas entradas. Valores em
branco ou sequências formadas só por `#` são inválidos e nunca contam como cobertura.

## Chef RPG

`CHEFRPG/tools/asset-pipeline` processa cinco tabelas de localização em
`resources.assets`. A memória em `CHEFRPG/memoria.json` é aplicada durante a
reconstrução; o pacote final contém apenas `Chef RPG_Data/resources.assets`.

## Little Witch in the Woods

O pipeline em `LW/tools/asset-pipeline` reconstrói tabelas gerais, diálogos e
missões. As fontes de verdade são `LW/memoria_revisado.json`,
`LW/dialogos/memory/memoria.json` e `missoes/memoria_missoes.json`.

## Segurança operacional

Os pipelines trabalham em staging e validam o asset reaberto antes de gerar um
pacote. A instalação manual sempre pode ser revertida por **Verificar integridade
dos arquivos** na Steam.
