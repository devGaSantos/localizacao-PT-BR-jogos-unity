import json
import argparse
from pathlib import Path

# =========================
# CONFIGURAÇÕES
# =========================
# Este script deve ficar dentro da pasta:
# LW/dialogos/nao_revisados
#
# Estrutura esperada:
# nao_revisados/
# ├─ generate_gpt_revision.py
# ├─ nao_revisadas.json
# ├─ memoria.json
# ├─ particionados/
# └─ revisados_gpt/

BASE_DIR = Path(__file__).resolve().parent

NAO_REVISADOS_DIR = BASE_DIR

ARQUIVO_NAO_REVISADAS = NAO_REVISADOS_DIR / "nao_revisadas.json"
ARQUIVO_MEMORIA = NAO_REVISADOS_DIR / "memoria.json"

PARTICIONADOS_DIR = NAO_REVISADOS_DIR / "particionados"
REVISADOS_GPT_DIR = NAO_REVISADOS_DIR / "revisados_gpt"

RELATORIO_PARTICIONAMENTO = NAO_REVISADOS_DIR / "relatorio_particionamento.json"
RELATORIO_GROUP = NAO_REVISADOS_DIR / "relatorio_group_revisados.json"

TAMANHO_LOTE = 300


# =========================
# FUNÇÕES JSON
# =========================

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# PARTICIONAR
# =========================

def particionar_nao_revisadas():
    print("📖 Lendo arquivo de não revisadas...")
    dados = load_json(ARQUIVO_NAO_REVISADAS)

    if not isinstance(dados, dict):
        raise ValueError(
            "nao_revisadas.json precisa estar no formato {chave_ingles: valor_ptbr}."
        )

    PARTICIONADOS_DIR.mkdir(parents=True, exist_ok=True)

    itens = list(dados.items())
    total = len(itens)

    print(f"📌 Total de entradas: {total}")
    print(f"📦 Tamanho de cada lote: {TAMANHO_LOTE}")

    arquivos_gerados = []

    for indice_inicio in range(0, total, TAMHO_LOTE := TAMANHO_LOTE):
        lote_numero = (indice_inicio // TAMHO_LOTE) + 1
        lote_itens = itens[indice_inicio:indice_inicio + TAMHO_LOTE]
        lote_dict = dict(lote_itens)

        nome_arquivo = f"nao_revisadas_parte_{lote_numero:03}.json"
        caminho_saida = PARTICIONADOS_DIR / nome_arquivo

        save_json(caminho_saida, lote_dict)

        arquivos_gerados.append({
            "arquivo": str(caminho_saida),
            "parte": lote_numero,
            "entradas": len(lote_dict),
            "primeira_chave": lote_itens[0][0] if lote_itens else None,
            "ultima_chave": lote_itens[-1][0] if lote_itens else None
        })

        print(f"✅ Gerado: {caminho_saida} ({len(lote_dict)} entradas)")

    relatorio = {
        "arquivo_origem": str(ARQUIVO_NAO_REVISADAS),
        "pasta_saida": str(PARTICIONADOS_DIR),
        "total_entradas": total,
        "tamanho_lote": TAMANHO_LOTE,
        "total_arquivos": len(arquivos_gerados),
        "arquivos": arquivos_gerados
    }

    save_json(RELATORIO_PARTICIONAMENTO, relatorio)

    print("\n✅ Particionamento concluído!")
    print(f"📂 Pasta: {PARTICIONADOS_DIR}")
    print(f"📊 Relatório: {RELATORIO_PARTICIONAMENTO}")


# =========================
# CARREGAR REVISADOS GPT
# =========================

def carregar_revisados_gpt():
    if not REVISADOS_GPT_DIR.exists():
        raise FileNotFoundError(f"Pasta não encontrada: {REVISADOS_GPT_DIR}")

    arquivos = sorted(REVISADOS_GPT_DIR.glob("*.json"))

    if not arquivos:
        raise FileNotFoundError(f"Nenhum JSON encontrado em: {REVISADOS_GPT_DIR}")

    revisados = {}
    duplicadas = {}

    for arquivo in arquivos:
        print(f"📖 Lendo revisado: {arquivo.name}")
        dados = load_json(arquivo)

        if not isinstance(dados, dict):
            raise ValueError(
                f"O arquivo {arquivo} não está no formato {{chave_ingles: valor_ptbr}}."
            )

        for chave, valor in dados.items():
            if chave in revisados:
                duplicadas.setdefault(chave, []).append(str(arquivo))

            revisados[chave] = valor

    return revisados, duplicadas, arquivos


# =========================
# AGRUPAR E APLICAR
# =========================

def aplicar_revisados_na_memoria():
    print("📖 Carregando arquivos revisados do GPT...")
    revisados, duplicadas, arquivos_lidos = carregar_revisados_gpt()

    print("📖 Carregando memória...")
    memoria = load_json(ARQUIVO_MEMORIA)

    if not isinstance(memoria, dict):
        raise ValueError(
            "memoria.json precisa estar no formato {chave_ingles: valor_ptbr}."
        )

    substituicoes = []
    chaves_nao_encontradas = []
    iguais = []

    print(f"🔎 Total de revisões carregadas: {len(revisados)}")
    print("🔁 Aplicando revisões na memória...")

    for chave, novo_valor in revisados.items():
        if chave not in memoria:
            chaves_nao_encontradas.append(chave)
            continue

        valor_antigo = memoria[chave]

        if valor_antigo == novo_valor:
            iguais.append(chave)
            continue

        memoria[chave] = novo_valor

        substituicoes.append({
            "chave": chave,
            "valor_antigo": valor_antigo,
            "valor_novo": novo_valor
        })

    save_json(ARQUIVO_MEMORIA, memoria)

    relatorio = {
        "arquivo_memoria": str(ARQUIVO_MEMORIA),
        "pasta_revisados": str(REVISADOS_GPT_DIR),
        "arquivos_lidos": [str(a) for a in arquivos_lidos],
        "total_revisoes_carregadas": len(revisados),
        "substituicoes_realizadas": len(substituicoes),
        "valores_iguais_sem_alteracao": len(iguais),
        "chaves_nao_encontradas": len(chaves_nao_encontradas),
        "duplicadas": {
            "total": len(duplicadas),
            "chaves": duplicadas
        },
        "detalhes_substituicoes": substituicoes,
        "detalhes_chaves_nao_encontradas": chaves_nao_encontradas,
        "detalhes_iguais": iguais
    }

    save_json(RELATORIO_GROUP, relatorio)

    print("\n✅ Agrupamento e substituição concluídos!")
    print(f"📌 Revisões carregadas: {len(revisados)}")
    print(f"✅ Substituições feitas: {len(substituicoes)}")
    print(f"➖ Já estavam iguais: {len(iguais)}")
    print(f"⚠️ Chaves não encontradas: {len(chaves_nao_encontradas)}")
    print(f"⚠️ Chaves duplicadas entre arquivos revisados: {len(duplicadas)}")
    print(f"📊 Relatório: {RELATORIO_GROUP}")


# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser(
        description="Particiona nao_revisadas.json e aplica revisões GPT na memoria.json."
    )

    parser.add_argument(
        "-group",
        action="store_true",
        help="Agrupa os JSONs da pasta revisados_gpt e aplica na memoria.json."
    )

    args = parser.parse_args()

    if args.group:
        aplicar_revisados_na_memoria()
    else:
        particionar_nao_revisadas()


if __name__ == "__main__":
    main()