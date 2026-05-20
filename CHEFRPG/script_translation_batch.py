import csv
import time
import os
import re
import json
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="en", target="pt")

input_folder = "exportados"
output_folder = "traduzidos"
memory_file = "memoria.json"

os.makedirs(output_folder, exist_ok=True)

cache = {}

# =========================
# CONTADORES DO RELATÓRIO
# =========================

usadas_br = 0
usadas_memoria = 0
traduzidas_google = 0
linhas_ignoradas = 0

# =========================
# MEMÓRIA JSON
# =========================

def carregar_memoria():
    if not os.path.exists(memory_file):
        return {}

    try:
        with open(memory_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        print("⚠ Não foi possível carregar memoria.json. Usando memória vazia.")
        return {}


def salvar_memoria(memory):
    with open(memory_file, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


memory = carregar_memoria()

# =========================
# PROTEGER TOKENS
# =========================

def protect_tokens(text):
    if not text:
        return text, {}

    replacements = {}
    counter = 0

    pattern = r'(<[^<>]*?>|\[[^\[\]]*?\]|\{[^{}]*?\}|\([^()]*?\))'

    def replacer(match):
        nonlocal counter
        original = match.group(0)
        token = f"__PROTECTED_TOKEN_{counter}__"
        replacements[token] = original
        counter += 1
        return token

    protected_text = re.sub(pattern, replacer, text)
    return protected_text, replacements


def restore_tokens(text, replacements):
    if not text:
        return text

    for token, original in replacements.items():
        text = text.replace(token, original)

    return text

# =========================
# TRADUÇÃO SEGURA
# =========================

def safe_translate(text):
    if not text:
        return text

    protected_text, replacements = protect_tokens(text)

    if protected_text in cache:
        raw = cache[protected_text]
        return restore_tokens(raw, replacements)

    for _ in range(3):
        try:
            raw = translator.translate(protected_text)

            if raw and raw.strip():
                cache[protected_text] = raw
                time.sleep(0.05)
                return restore_tokens(raw, replacements)

        except Exception:
            time.sleep(0.2)

    return text

# =========================
# ARQUIVOS
# =========================

files = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]

print(f"📂 Arquivos encontrados: {len(files)}")
print(f"🧠 Memória carregada do JSON: {len(memory)} traduções")

# =========================
# PASSO 1 — ATUALIZAR MEMÓRIA COM BR EXISTENTE
# =========================

for file in files:
    path = os.path.join(input_folder, file)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    en_index = None
    br_index = None

    for line in lines:
        try:
            row = next(csv.reader([line]))

            if "en" in row and "br" in row:
                en_index = row.index("en")
                br_index = row.index("br")
                continue

            if en_index is None or br_index is None:
                continue

            if len(row) <= max(en_index, br_index):
                continue

            en = row[en_index]
            br = row[br_index]

            if en and br:
                memory[en] = br

        except:
            continue

print(f"🧠 Memória após ler BR existente: {len(memory)} traduções")

# =========================
# PASSO 2 — PROCESSAR ARQUIVOS
# =========================

for file in files:
    print(f"\n⚙ Processando: {file}")

    path = os.path.join(input_folder, file)

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    output_lines = []

    en_index = None
    br_index = None

    usadas_br_arquivo = 0
    usadas_memoria_arquivo = 0
    traduzidas_google_arquivo = 0

    for line in lines:
        stripped = line.strip()

        if not stripped:
            output_lines.append(line)
            continue

        try:
            row = next(csv.reader([line]))

            if "en" in row and "br" in row:
                en_index = row.index("en")
                br_index = row.index("br")
                output_lines.append(line)
                continue

            if en_index is None or br_index is None:
                output_lines.append(line)
                linhas_ignoradas += 1
                continue

            if len(row) <= max(en_index, br_index):
                output_lines.append(line)
                linhas_ignoradas += 1
                continue

            en = row[en_index]
            br = row[br_index]

            # PRIORIDADE 1 — coluna BR
            if br:
                row[en_index] = br
                if en:
                    memory[en] = br

                usadas_br += 1
                usadas_br_arquivo += 1

            # PRIORIDADE 2 — memoria.json
            elif en in memory:
                row[en_index] = memory[en]

                usadas_memoria += 1
                usadas_memoria_arquivo += 1

            # PRIORIDADE 3 — Google Translator
            elif en:
                translated = safe_translate(en)
                row[en_index] = translated
                memory[en] = translated

                traduzidas_google += 1
                traduzidas_google_arquivo += 1

            new_line = ",".join(f'"{col}"' if col else "" for col in row)
            output_lines.append(new_line + "\n")

        except:
            output_lines.append(line)
            linhas_ignoradas += 1

    base_name = file.split("-")[0].strip()
    output_name = f"TRADUZIDO - {base_name}.txt"
    output_path = os.path.join(output_folder, output_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"✅ Gerado: {output_name}")
    print(f"   BR: {usadas_br_arquivo}")
    print(f"   Memória: {usadas_memoria_arquivo}")
    print(f"   Google: {traduzidas_google_arquivo}")

# =========================
# SALVAR MEMÓRIA FINAL
# =========================

salvar_memoria(memory)

print("\n📊 RELATÓRIO FINAL")
print(f"✅ Usadas da coluna BR: {usadas_br}")
print(f"🧠 Usadas da memoria.json: {usadas_memoria}")
print(f"🤖 Traduzidas pelo Google: {traduzidas_google}")
print(f"⚠ Linhas ignoradas/fora do padrão: {linhas_ignoradas}")
print(f"💾 Memória final salva: {len(memory)} traduções")
print("🚀 TODOS arquivos traduzidos!")