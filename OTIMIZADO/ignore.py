import os
import re
import json


MEMORY_FOLDER = "memory"

INPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria.json")
IGNORE_FILE = os.path.join(MEMORY_FOLDER, "ignore.json")

os.makedirs(MEMORY_FOLDER, exist_ok=True)


TOKEN_PATTERN = re.compile(
    r"("
    r"\[lua\(.*?\)\]"
    r"|\[[^\]]+\]"
    r"|</?[^>]+>"
    r"|\{[^}]+\}"
    r"|\\n"
    r"|\\r"
    r"|\\t"
    r"|%[sdif]"
    r")"
)

EDGE_PUNCT_PATTERN = re.compile(
    r"^[\s\.\,\!\?\-\_\—\–\…\"'“”‘’\(\)\[\]<>]+"
    r"|[\s\.\,\!\?\-\_\—\–\…\"'“”‘’\(\)\[\]<>]+$"
)

ONLY_PUNCT_PATTERN = re.compile(r"[\s\.\,\!\?\-\_\—\–\…]+")
NUMBER_PATTERN = re.compile(r"\d+")
DECIMAL_PATTERN = re.compile(r"\d+(\.\d+)?")
PERCENT_PATTERN = re.compile(r"\d+%")


PROPER_NAMES = {
    "Ellie",
    "Virgil",
    "Rubrum",
    "Enite",
    "Arden",
    "Kyla",
    "Roy",
    "Diane",
    "Lisa",
    "Highlion",
    "Wisteria",
    "Lucerine Ortu",
    "Alvin",
    "Miscella",
    "Pompom",
    "Ritoring",
    "Gaga Bird",
    "Mara Smith",
}


PRESERVE_EXACT = {
    "",
    "???",
    "...",
    "…",
    "-",
    "_",
    "--",
    "---",
    "----",
    ".",
    "..",
    "OK",
    "OK.",
    "ok",
    "ok.",
}


def carregar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def salvar_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def remover_tokens(texto):
    texto = TOKEN_PATTERN.sub("", texto or "")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def remover_pontuacao_bordas(texto):
    texto = texto.strip()
    texto = EDGE_PUNCT_PATTERN.sub("", texto)
    return texto.strip()


def texto_base_sem_tokens(texto):
    return remover_pontuacao_bordas(remover_tokens(texto))


def texto_eh_pontuacao_ou_vazio(texto):
    if texto is None:
        return True

    limpo = texto.strip()

    if limpo in PRESERVE_EXACT:
        return True

    return bool(ONLY_PUNCT_PATTERN.fullmatch(limpo))


def texto_eh_numero(texto):
    if texto is None:
        return False

    limpo = texto.strip()

    return (
        bool(NUMBER_PATTERN.fullmatch(limpo))
        or bool(DECIMAL_PATTERN.fullmatch(limpo))
        or bool(PERCENT_PATTERN.fullmatch(limpo))
    )


def texto_eh_so_tokens_ou_tags(texto):
    sem_tokens = remover_tokens(texto)
    return texto_eh_pontuacao_ou_vazio(sem_tokens)


def texto_eh_so_nome_proprio(texto):
    base = texto_base_sem_tokens(texto)

    if not base:
        return False

    return base in PROPER_NAMES


def deve_ignorar(texto):
    if texto is None:
        return True

    limpo = texto.strip()

    if limpo in PRESERVE_EXACT:
        return True

    if texto_eh_pontuacao_ou_vazio(limpo):
        return True

    if texto_eh_numero(limpo):
        return True

    if texto_eh_so_tokens_ou_tags(limpo):
        return True

    if texto_eh_so_nome_proprio(limpo):
        return True

    return False


def progresso(atual, total):
    if total <= 0:
        return

    pct = atual / total
    barra = int(30 * pct)

    print(
        f"\rGerando ignore [{'█' * barra}{'-' * (30 - barra)}] "
        f"{pct * 100:.1f}% ({atual}/{total})",
        end="",
        flush=True
    )

    if atual >= total:
        print()


def main():
    memoria = carregar_json(INPUT_FILE)

    if not memoria:
        print(f"Não consegui carregar: {INPUT_FILE}")
        return

    ignore = []
    total = len(memoria)

    for i, chave in enumerate(memoria.keys(), start=1):
        if deve_ignorar(chave):
            ignore.append(chave)

        progresso(i, total)

    salvar_json(IGNORE_FILE, ignore)

    print(f"\nIgnore gerado: {IGNORE_FILE}")
    print(f"Total de entradas ignoradas: {len(ignore)}")


if __name__ == "__main__":
    main()