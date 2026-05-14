import os
import re

#ESSE CARA TINHA QUE GERAR O JSON COM TUDO

translated_folder = "traduzidos"
memory_folder = "memory"
output_folder = "revisados"

os.makedirs(output_folder, exist_ok=True)

id_pattern = re.compile(r'\s*\d+\s+SInt64\s+m_Id\s*=\s*(-?\d+)')
localized_pattern = re.compile(r'(\s*\d+\s+string\s+m_Localized\s*=\s*")([^"]*)(".*)')

def normalize_name(name):
    return name.replace("TRADUZIDO - ", "", 1).strip()

def build_memory_from_file(path):
    memory_by_id = {}

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_id = None

    for line in lines:
        id_match = id_pattern.match(line)

        if id_match:
            current_id = id_match.group(1)
            continue

        loc_match = localized_pattern.match(line)

        if loc_match and current_id:
            translated_text = loc_match.group(2)

            if translated_text and translated_text.strip():
                memory_by_id[current_id] = translated_text

            current_id = None

    return memory_by_id

def find_matching_memory_file(translated_file):
    normalized = normalize_name(translated_file)
    exact_path = os.path.join(memory_folder, normalized)

    if os.path.exists(exact_path):
        return exact_path

    return None

translated_files = [
    f for f in os.listdir(translated_folder)
    if f.lower().endswith(".txt")
]

print(f"📂 Arquivos traduzidos encontrados: {len(translated_files)}")

for translated_file in translated_files:
    translated_path = os.path.join(translated_folder, translated_file)
    memory_path = find_matching_memory_file(translated_file)

    if not memory_path:
        print(f"⚠ Sem memory correspondente: {translated_file}")

        output_path = os.path.join(output_folder, translated_file)

        with open(translated_path, "r", encoding="utf-8") as f:
            content = f.read()

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        continue

    print(f"⚙ Revisando: {translated_file}")

    memory_by_id = build_memory_from_file(memory_path)

    with open(translated_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    reviewed_lines = []
    current_id = None
    replacements = 0

    for line in lines:
        id_match = id_pattern.match(line)

        if id_match:
            current_id = id_match.group(1)
            reviewed_lines.append(line)
            continue

        loc_match = localized_pattern.match(line)

        if loc_match:
            inicio = loc_match.group(1)
            current_text = loc_match.group(2)
            fim = loc_match.group(3)

            if current_id and current_id in memory_by_id:
                memory_text = memory_by_id[current_id]

                if memory_text != current_text:
                    line = inicio + memory_text + fim + "\n"
                    replacements += 1

            reviewed_lines.append(line)
            current_id = None
            continue

        reviewed_lines.append(line)

    output_path = os.path.join(output_folder, translated_file)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(reviewed_lines)

    print(f"✅ Gerado: {output_path}")
    print(f"   ↳ Substituições por m_Id: {replacements}")

print("\n🔥 Revisão por memory concluída!")