import csv
import time
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='en', target='pt')

input_file = "input.txt"
output_file = "output.txt"

cache = {}

def translate_text(text):
    if text in cache:
        return cache[text]

    for _ in range(3):  # retry até 3 vezes
        try:
            translated = translator.translate(text)

            if translated and translated.strip():
                cache[text] = translated
                time.sleep(0.05)  # evita bloqueio
                return translated

        except Exception as e:
            time.sleep(0.2)

    # fallback
    cache[text] = text
    return text


with open(input_file, "r", encoding="utf-8") as f:
    lines = f.readlines()

output_lines = []

en_index = None
br_index = None

rows_data = []

# 🔍 PARSE
for line in lines:
    stripped = line.strip()

    if not stripped:
        rows_data.append((line, None))
        continue

    try:
        row = next(csv.reader([line]))

        # detectar header
        if "en" in row and "br" in row:
            en_index = row.index("en")
            br_index = row.index("br")
            rows_data.append((line, None))
            continue

        if en_index is None or br_index is None:
            rows_data.append((line, None))
            continue

        if len(row) <= en_index:
            rows_data.append((line, None))
            continue

        en = row[en_index]
        br = row[br_index] if len(row) > br_index else ""

        rows_data.append((row, (en, br)))

    except:
        rows_data.append((line, None))


# ⚡ COLETAR textos únicos pra traduzir
to_translate = list(set(
    en for row, data in rows_data
    if data and not data[1] and data[0]
))

print(f"🧠 Traduzindo {len(to_translate)} textos...")

# 🚀 THREADS
with ThreadPoolExecutor(max_workers=15) as executor:
    results = list(executor.map(translate_text, to_translate))

translation_map = dict(zip(to_translate, results))


# 🔧 RECONSTRUIR
for item, data in rows_data:
    if data is None:
        output_lines.append(item if isinstance(item, str) else ",".join(item) + "\n")
        continue

    row = item
    en, br = data

    if br:
        row[en_index] = br
    elif en:
        row[en_index] = translation_map.get(en, en)

    new_line = ",".join(f'"{col}"' if col else "" for col in row)
    output_lines.append(new_line + "\n")


# 💾 SALVAR
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(output_lines)

print("✅ Tradução finalizada!")