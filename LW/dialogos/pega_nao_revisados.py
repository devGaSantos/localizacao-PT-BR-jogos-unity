import json
import subprocess
from pathlib import Path

COMMIT_BASE = "1d207dcfa6a2924a02580ca2e78f09a0cb878b6a"

# =========================
# CAMINHOS
# =========================

ARQUIVO_JSON = Path("memory/memoria.json")
ARQUIVO_NO_GIT = "LW/dialogos/memory/memoria.json"

# =========================
# PASTA DE SAÍDA
# =========================

OUTPUT_DIR = Path("nao_revisados")
OUTPUT_DIR.mkdir(exist_ok=True)

SAIDA_NAO_REVISADAS = OUTPUT_DIR / "nao_revisadas.json"
SAIDA_REVISADAS = OUTPUT_DIR / "revisadas.json"
SAIDA_NOVAS = OUTPUT_DIR / "novas_desde_commit.json"
SAIDA_RELATORIO = OUTPUT_DIR / "relatorio_revisao_por_commit.json"

# =========================
# FUNÇÕES
# =========================

def load_json_atual(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_json_do_commit(commit, arquivo):
    result = subprocess.run(
        ["git", "show", f"{commit}:{arquivo}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Erro ao ler arquivo do commit:\n{result.stderr}"
        )

    return json.loads(result.stdout)


def save_json(path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# MAIN
# =========================

def main():
    print("📖 Carregando JSON atual...")
    atual = load_json_atual(ARQUIVO_JSON)

    print("📦 Carregando JSON do commit base...")
    base = load_json_do_commit(COMMIT_BASE, ARQUIVO_NO_GIT)

    nao_revisadas = {}
    revisadas = {}
    novas = {}

    print("🔍 Comparando linhas...")

    for chave, valor_atual in atual.items():

        # Nova linha criada após commit
        if chave not in base:
            novas[chave] = valor_atual

        # Linha NÃO alterada = provavelmente não revisada
        elif base[chave] == valor_atual:
            nao_revisadas[chave] = valor_atual

        # Linha alterada = revisada
        else:
            revisadas[chave] = valor_atual

    relatorio = {
        "arquivo": str(ARQUIVO_JSON),
        "commit_base": COMMIT_BASE,
        "total_atual": len(atual),
        "total_base": len(base),
        "revisadas": len(revisadas),
        "nao_revisadas": len(nao_revisadas),
        "novas_desde_commit": len(novas)
    }

    print("💾 Salvando arquivos...")

    save_json(SAIDA_NAO_REVISADAS, nao_revisadas)
    save_json(SAIDA_REVISADAS, revisadas)
    save_json(SAIDA_NOVAS, novas)
    save_json(SAIDA_RELATORIO, relatorio)

    print("\n✅ Concluído!")
    print(f"📌 Revisadas: {len(revisadas)}")
    print(f"📌 Não revisadas: {len(nao_revisadas)}")
    print(f"📌 Novas desde o commit: {len(novas)}")

    print("\n📂 Arquivos gerados:")
    print(f" - {SAIDA_NAO_REVISADAS}")
    print(f" - {SAIDA_REVISADAS}")
    print(f" - {SAIDA_NOVAS}")
    print(f" - {SAIDA_RELATORIO}")


if __name__ == "__main__":
    main()