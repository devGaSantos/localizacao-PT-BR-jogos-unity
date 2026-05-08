import csv
import json
import re
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='en', target='pt')

input_file = "input.txt"
output_file = "output.txt"
memory_file = "memoria.json"
manual_memory_file = "memoria_manual.json"

# =========================
# CARREGAR MEMÓRIAS
# =========================

def carregar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

memoria = carregar_json(memory_file)
memoria_manual = carregar_json(manual_memory_file)

def salvar_memoria():
    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump(memoria, f, indent=2, ensure_ascii=False)

# =========================
# PROTEGER TOKENS
# =========================

def proteger_tokens(texto):
    tokens = []

    def replacer(match):
        tokens.append(match.group(0))
        return f"__TOKEN_{len(tokens)-1}__"

    pattern = r'(\[.*?\]|\(.*?\)|\{.*?\})'
    texto_protegido = re.sub(pattern, replacer, texto)

    return texto_protegido, tokens


def restaurar_tokens(texto, tokens):
    for i, token in enumerate(tokens):
        texto = texto.replace(f"__TOKEN_{i}__", token)
    return texto

# =========================
# TRADUÇÃO PRINCIPAL
# =========================

def traduzir_texto(en, br_existente):
    if not en:
        return en

    # 🔥 PRIORIDADE 1 - MEMÓRIA MANUAL
    if en in memoria_manual:
        return memoria_manual[en]

    # 🧠 PRIORIDADE 2 - MEMÓRIA AUTO
    if en in memoria:
        return memoria[en]

    # 🟢 PRIORIDADE 3 - BR EXISTENTE
    if br_existente:
        memoria[en] = br_existente
        return br_existente

    # 🤖 PRIORIDADE 4 - TRADUTOR
    try:
        texto_protegido, tokens = proteger_tokens(en)

        translated = translator.translate(texto_protegido)

        translated = restaurar_tokens(translated, tokens)

        memoria[en] = translated

        print(f"Auto: {en} -> {translated}")

        return translated

    except Exception as e:
        print(f"Erro traduzindo: {en}")
        return en

# =========================
# PROCESSAR ARQUIVO
# =========================

with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

output_lines = []

en_index = None
br_index = None

for line in lines:
    stripped = line.strip()

    if not stripped:
        output_lines.append(line)
        continue

    try:
        row = next(csv.reader([line]))

        # detectar header
        if "en" in row and "br" in row:
            en_index = row.index("en")
            br_index = row.index("br")
            output_lines.append(line)
            continue

        if en_index is None or br_index is None:
            output_lines.append(line)
            continue

        if len(row) <= max(en_index, br_index):
            output_lines.append(line)
            continue

        en = row[en_index]
        br = row[br_index]

        novo_texto = traduzir_texto(en, br)

        row[en_index] = novo_texto

        new_line = ",".join(f'"{col}"' if col else "" for col in row)
        output_lines.append(new_line + "\n")

    except:
        output_lines.append(line)

# =========================
# SALVAR RESULTADOS
# =========================

with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(output_lines)

salvar_memoria()

print("🔥 Tradução completa com memória PRO!")