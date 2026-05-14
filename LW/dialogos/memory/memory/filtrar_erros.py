#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path


MOTIVO_IGNORAR = "Tradução ficou igual ao original em inglês."


def carregar_json(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8-sig")

    try:
        return json.loads(texto)
    except json.JSONDecodeError as e:
        print(f"❌ Erro ao ler JSON: {e}")
        print(f"Arquivo: {caminho}")
        sys.exit(1)


def salvar_json(caminho: Path, dados: dict) -> None:
    caminho.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def main():
    if len(sys.argv) < 2:
        print("Uso:")
        print('  python filtrar_erros.py "relatorio_erros.json"')
        print()
        print("Ou:")
        print('  python filtrar_erros.py "relatorio_erros.json" "saida_filtrada.json"')
        sys.exit(1)

    entrada = Path(sys.argv[1])

    if len(sys.argv) >= 3:
        saida = Path(sys.argv[2])
    else:
        saida = entrada.with_name(entrada.stem + "_sem_iguais.json")

    if not entrada.exists():
        print(f"❌ Arquivo não encontrado: {entrada}")
        sys.exit(1)

    dados = carregar_json(entrada)

    if not isinstance(dados, dict):
        print("❌ O arquivo precisa ser um JSON no formato objeto:")
        print('{ "texto original": "motivo do erro" }')
        sys.exit(1)

    filtrado = {}
    contagem_motivos = {}

    total = len(dados)
    ignorados = 0

    for chave, motivo in dados.items():
        if motivo == MOTIVO_IGNORAR:
            ignorados += 1
            continue

        filtrado[chave] = motivo
        contagem_motivos[motivo] = contagem_motivos.get(motivo, 0) + 1

    salvar_json(saida, filtrado)

    print("✅ JSON filtrado gerado com sucesso!")
    print(f"📄 Entrada: {entrada}")
    print(f"📄 Saída:   {saida}")
    print()
    print(f"Total original: {total}")
    print(f"Ignorados por texto igual ao inglês: {ignorados}")
    print(f"Restantes no JSON: {len(filtrado)}")

    if contagem_motivos:
        print()
        print("Motivos restantes:")
        for motivo, qtd in sorted(contagem_motivos.items(), key=lambda x: x[1], reverse=True):
            print(f"  {qtd}x - {motivo}")


if __name__ == "__main__":
    main()