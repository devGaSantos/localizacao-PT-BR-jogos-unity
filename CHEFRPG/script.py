import csv

input_file = "input.txt"
output_file = "output.txt"

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

        # se ainda não detectou header, mantém linha
        if en_index is None or br_index is None:
            output_lines.append(line)
            continue

        # garante tamanho
        if len(row) <= max(en_index, br_index):
            output_lines.append(line)
            continue

        en = row[en_index]
        br = row[br_index]

        # substitui
        if en and br:
            row[en_index] = br

        # reconstruir linha corretamente
        new_line = ",".join(f'"{col}"' if col else "" for col in row)
        output_lines.append(new_line + "\n")

    except Exception as e:
        # mantém linha original se quebrar
        output_lines.append(line)

# salvar
with open(output_file, "w", encoding="utf-8") as f:
    f.writelines(output_lines)

print("✅ Feito")