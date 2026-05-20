import json
import argparse
from pathlib import Path

MEMORY_FILES = [
    Path("../LW/dialogos/memory/memoria.json"),
    Path("../LW/memoria_revisado.json"),
]

INPUT_EXTRACTED_FILE = Path("textos_extraidos.json")
INPUT_REPLACE_FILE = Path("chaves_para_substituir_corrigido.json")

OUTPUT_FILE = Path("chaves_para_substituir.json")
NOT_FOUND_FILE = Path("valores_nao_encontrados.json")
REPORT_FILE = Path("relatorio_revisao.json")


def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: Path, data):
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(text):
    if text is None:
        return ""

    return str(text).strip()


def load_extracted_values(path: Path):
    data = load_json(path)

    if isinstance(data, dict):
        return [normalize_text(key) for key in data.keys() if normalize_text(key)]

    if isinstance(data, list):
        return [normalize_text(item) for item in data if normalize_text(item)]

    raise ValueError("O JSON de entrada precisa ser um objeto {texto: 0} ou uma lista de textos.")


def search_values():
    textos_extraidos = load_extracted_values(INPUT_EXTRACTED_FILE)

    result = {}
    not_found = []
    duplicates = {}

    report = {
        "modo": "busca",
        "arquivo_entrada": str(INPUT_EXTRACTED_FILE),
        "arquivos_memoria": [str(p) for p in MEMORY_FILES],
        "total_textos_extraidos": len(textos_extraidos),
        "encontrados": 0,
        "nao_encontrados": 0,
        "duplicados": 0,
        "detalhes": {}
    }

    memories = {}

    for memory_path in MEMORY_FILES:
        memories[str(memory_path)] = load_json(memory_path)

    for texto in textos_extraidos:
        matches = []

        for memory_path, memory_data in memories.items():
            if not isinstance(memory_data, dict):
                continue

            for key, value in memory_data.items():
                if not isinstance(value, str):
                    continue

                if normalize_text(value) == texto:
                    matches.append({
                        "arquivo": memory_path,
                        "chave": key,
                        "valor": value
                    })

        if not matches:
            not_found.append(texto)
            continue

        if len(matches) > 1:
            duplicates[texto] = matches

        for match in matches:
            chave = match["chave"]
            valor = match["valor"]
            result[chave] = valor

        report["detalhes"][texto] = matches

    report["encontrados"] = len(result)
    report["nao_encontrados"] = len(not_found)
    report["duplicados"] = len(duplicates)

    if OUTPUT_FILE.exists():
        resultado_antigo = load_json(OUTPUT_FILE)
        if isinstance(resultado_antigo, dict):
            resultado_antigo.update(result)
            result = resultado_antigo

    save_json(OUTPUT_FILE, result)

    if NOT_FOUND_FILE.exists():
        antigos_nao_encontrados = load_json(NOT_FOUND_FILE)
        if isinstance(antigos_nao_encontrados, list):
            not_found = list(dict.fromkeys(antigos_nao_encontrados + not_found))

    save_json(NOT_FOUND_FILE, not_found)
    save_json(REPORT_FILE, report)

    print("✅ Busca concluída.")
    print(f"📥 Entrada: {INPUT_EXTRACTED_FILE}")
    print(f"📄 Gerado: {OUTPUT_FILE}")
    print(f"⚠️ Não encontrados: {len(not_found)} -> {NOT_FOUND_FILE}")
    print(f"⚠️ Textos duplicados encontrados: {len(duplicates)}")
    print(f"📊 Relatório: {REPORT_FILE}")


def replace_values():
    replacements = load_json(INPUT_REPLACE_FILE)

    if not isinstance(replacements, dict):
        raise ValueError("O arquivo de replace precisa ser um JSON no formato {chave: valor_corrigido}.")

    report = {
        "modo": "replace",
        "arquivo_entrada": str(INPUT_REPLACE_FILE),
        "arquivos_memoria": [str(p) for p in MEMORY_FILES],
        "substituicoes": [],
        "chaves_nao_encontradas": [],
        "arquivos_processados": []
    }

    missing_keys = set(replacements.keys())

    for memory_path in MEMORY_FILES:
        memory_data = load_json(memory_path)

        if not isinstance(memory_data, dict):
            print(f"⚠️ Ignorando arquivo que não é objeto JSON: {memory_path}")
            continue

        changed = False
        total_subs = 0

        for key, new_value in replacements.items():
            if key not in memory_data:
                continue

            old_value = memory_data[key]

            if old_value != new_value:
                memory_data[key] = new_value
                changed = True
                total_subs += 1

                report["substituicoes"].append({
                    "arquivo": str(memory_path),
                    "chave": key,
                    "valor_antigo": old_value,
                    "valor_novo": new_value
                })

            missing_keys.discard(key)

        if changed:
            save_json(memory_path, memory_data)

        report["arquivos_processados"].append({
            "arquivo": str(memory_path),
            "alterado": changed,
            "substituicoes": total_subs
        })

    report["chaves_nao_encontradas"] = sorted(missing_keys)

    save_json(REPORT_FILE, report)

    print("✅ Replace concluído.")
    print(f"📥 Entrada: {INPUT_REPLACE_FILE}")
    print(f"📊 Relatório: {REPORT_FILE}")

    if missing_keys:
        print(f"⚠️ Chaves não encontradas: {len(missing_keys)}")


def main():
    parser = argparse.ArgumentParser(
        description="Busca textos extraídos dos prints nos valores da memória e substitui usando chaves encontradas."
    )

    parser.add_argument(
        "-replace",
        action="store_true",
        help="Usa chaves_para_substituir_corrigido.json para substituir nos arquivos de memória."
    )

    args = parser.parse_args()

    if args.replace:
        replace_values()
    else:
        search_values()


if __name__ == "__main__":
    main()