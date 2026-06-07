import json
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

CORRIGIDAS_PATH = "frases_corrigidas_openai.json"
CHECKPOINT_PATH = "checkpoint_corrigidas_openai.json"
ANTES_DEPOIS_PATH = "relatorio_antes_depois_corrigidas.json"

# Coloque aqui as chaves em inglês que você quer reverter.
CHAVES_PARA_REVERTER = [
    "Thank you for making it!",
    "There it is!",
    "I can have 10 in one go, but I've got other fish, so I need no more.",
]


# ============================================================
# FUNÇÕES
# ============================================================

def carregar_json(caminho: str) -> dict:
    path = Path(caminho)

    if not path.exists():
        print(f"Aviso: arquivo não encontrado: {caminho}")
        return {}

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def salvar_json(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def criar_backup(caminho: str) -> None:
    path = Path(caminho)

    if not path.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}.backup_{timestamp}{path.suffix}")

    shutil.copy2(path, backup_path)
    print(f"Backup criado: {backup_path}")


def reverter():
    print("Carregando arquivos...")

    corrigidas = carregar_json(CORRIGIDAS_PATH)
    checkpoint = carregar_json(CHECKPOINT_PATH)
    antes_depois = carregar_json(ANTES_DEPOIS_PATH)

    if not antes_depois:
        print("Nada encontrado no relatório antes/depois.")
        return

    print()
    print("Criando backups antes de alterar...")
    criar_backup(CORRIGIDAS_PATH)
    criar_backup(CHECKPOINT_PATH)
    criar_backup(ANTES_DEPOIS_PATH)

    revertidas = []
    nao_encontradas = []

    for chave in CHAVES_PARA_REVERTER:
        if chave not in antes_depois:
            nao_encontradas.append(chave)
            continue

        valor_antigo = antes_depois[chave]["antes"]

        if corrigidas:
            corrigidas[chave] = valor_antigo

        if checkpoint:
            checkpoint[chave] = valor_antigo

        del antes_depois[chave]

        revertidas.append(chave)

    salvar_json(corrigidas, CORRIGIDAS_PATH)
    salvar_json(checkpoint, CHECKPOINT_PATH)
    salvar_json(antes_depois, ANTES_DEPOIS_PATH)

    print()
    print("Concluído.")
    print(f"Revertidas: {len(revertidas)}")
    print(f"Não encontradas no antes/depois: {len(nao_encontradas)}")

    if revertidas:
        print()
        print("Frases revertidas:")
        for chave in revertidas:
            print(f"- {chave}")

    if nao_encontradas:
        print()
        print("Não encontradas:")
        for chave in nao_encontradas:
            print(f"- {chave}")


if __name__ == "__main__":
    reverter()