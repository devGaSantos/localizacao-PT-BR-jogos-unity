import csv
import time
import os
import re
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="en", target="pt")

input_folder = "exportados"
output_folder = "traduzidos"

os.makedirs(output_folder, exist_ok=True)

cache = {}
memory = {}

def protect_tokens(text):
    """
    Protege placeholders/tags sem alterar o conteúdo original.
    Tudo que estiver entre <>, [], {}, () é preservado exatamente como está.
    """
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
        except:
            time.sleep(0.2)

    return text

files = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]

print(f"📂 Arquivos encontrados: {len(files)}")

# PASSO 1 — montar memória global
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
                protected_en, _ = protect_tokens(en)
                memory[protected_en] = br

        except:
            continue

print(f"🧠 Memória global carregada: {len(memory)} traduções")

# PASSO 2 — processar arquivos
for file in files:
    print(f"⚙ Processando: {file}")

    path = os.path.join(input_folder, file)

    with open(path, "r", encoding="utf-8") as f:
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

            protected_en, _ = protect_tokens(en)

            # 1. usa BR existente
            if br:
                row[en_index] = br

            # 2. usa memória global
            elif protected_en in memory:
                row[en_index] = memory[protected_en]

            # 3. traduz automático
            elif en:
                row[en_index] = safe_translate(en)

            new_line = ",".join(f'"{col}"' if col else "" for col in row)
            output_lines.append(new_line + "\n")

        except:
            output_lines.append(line)

    base_name = file.split("-")[0].strip()
    output_name = f"TRADUZIDO - {base_name}.txt"
    output_path = os.path.join(output_folder, output_name)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    print(f"✅ Gerado: {output_name}")

print("🚀 TODOS arquivos traduzidos!")