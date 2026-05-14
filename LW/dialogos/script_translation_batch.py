import os
import re
import json
import time
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="en", target="pt")

input_folder = "exportados"
output_folder = "traduzidos"
memory_folder = "memory"

manual_memory_file = os.path.join(memory_folder, "memoria_manual.json")
auto_memory_file = os.path.join(memory_folder, "memoria.json")
traduzidas_por_translator_file = os.path.join(memory_folder, "traduzidas_por_translator.json")

os.makedirs(output_folder, exist_ok=True)
os.makedirs(memory_folder, exist_ok=True)

def carregar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

memoria_manual = carregar_json(manual_memory_file)
memoria = carregar_json(auto_memory_file)
traduzidas_por_translator = carregar_json(traduzidas_por_translator_file)

def salvar_json(path, dados):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def salvar_memoria():
    salvar_json(auto_memory_file, memoria)
    salvar_json(traduzidas_por_translator_file, traduzidas_por_translator)

def proteger_tokens(texto):
    if not texto:
        return texto, []

    tokens = []

    def replacer(match):
        tokens.append(match.group(0))
        return f"__TOKEN_{len(tokens)-1}__"

    pattern = r'(\[.*?\]|\(.*?\)|\{.*?\}|<.*?>)'
    protegido = re.sub(pattern, replacer, texto)
    return protegido, tokens

def restaurar_tokens(texto, tokens):
    if not texto:
        return texto

    for i, token in enumerate(tokens):
        texto = texto.replace(f"__TOKEN_{i}__", token)

    return texto

def traduzir(texto):
    if not texto or not texto.strip():
        return texto

    if texto.strip() in ["???", "...", "-", "_"]:
        memoria[texto] = texto
        return texto

    if texto in memoria_manual:
        memoria[texto] = memoria_manual[texto]
        return memoria_manual[texto]

    if texto in memoria:
        return memoria[texto]

    try:
        protegido, tokens = proteger_tokens(texto)
        traduzido = translator.translate(protegido)

        if not traduzido:
            memoria[texto] = texto
            return texto

        traduzido = restaurar_tokens(traduzido, tokens)

        memoria[texto] = traduzido

        # 🔥 registra somente o que realmente passou pelo Google Translator
        traduzidas_por_translator[texto] = traduzido

        time.sleep(0.05)
        return traduzido

    except:
        memoria[texto] = texto
        return texto

def progresso(atual, total, prefixo=""):
    if total == 0:
        return

    if atual % 500 != 0 and atual != total:
        return

    pct = atual / total
    barra = int(30 * pct)

    print(f"\r{prefixo} [{'█' * barra}{'-' * (30 - barra)}] {pct * 100:.1f}%", end="")

    if atual == total:
        print()

title_pattern = re.compile(r'\s*\d+\s+string\s+title\s*=\s*"([^"]*)"')

# IMPORTANTE:
# Esse regex usa (.*) para capturar frases com aspas internas.
value_pattern = re.compile(r'(\s*\d+\s+string\s+value\s*=\s*")(.*)(".*)$')

type_string_pattern = re.compile(r'\s*\d+\s+string\s+typeString\s*=\s*"([^"]*)"')

def processar_bloco(bloco):
    title_is_en = False
    is_localization = False
    value_index = None
    value_match = None

    for idx, linha in enumerate(bloco):
        title_match = title_pattern.match(linha)
        if title_match and title_match.group(1) == "en":
            title_is_en = True

        match_value = value_pattern.match(linha)
        if match_value:
            value_index = idx
            value_match = match_value

        type_match = type_string_pattern.match(linha)
        if type_match and type_match.group(1) == "CustomFieldType_Localization":
            is_localization = True

    if title_is_en and is_localization and value_index is not None and value_match:
        inicio = value_match.group(1)
        texto_original = value_match.group(2)
        fim = value_match.group(3)

        texto_traduzido = traduzir(texto_original)

        if not isinstance(texto_traduzido, str):
            texto_traduzido = texto_original
            memoria[texto_original] = texto_original

        bloco[value_index] = inicio + texto_traduzido + fim + "\n"

    return bloco

arquivos = [
    f for f in os.listdir(input_folder)
    if f.lower().endswith(".txt")
]

print(f"📂 Arquivos encontrados: {len(arquivos)}")

for arquivo in arquivos:
    caminho_entrada = os.path.join(input_folder, arquivo)
    caminho_saida = os.path.join(output_folder, f"TRADUZIDO - {arquivo}")

    print(f"\n⚙ Processando: {arquivo}")

    with open(caminho_entrada, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    total = len(linhas)
    novas_linhas = []

    bloco_atual = []
    dentro_field_data = False

    for i, linha in enumerate(linhas, start=1):
        progresso(i, total, prefixo=arquivo)

        if re.match(r'\s*\d+\s+Field\s+data\s*$', linha):
            if bloco_atual:
                novas_linhas.extend(processar_bloco(bloco_atual))
                bloco_atual = []

            dentro_field_data = True
            bloco_atual.append(linha)
            continue

        if dentro_field_data:
            if re.match(r'\s*\[\d+\]\s*$', linha):
                novas_linhas.extend(processar_bloco(bloco_atual))
                bloco_atual = []
                dentro_field_data = False
                novas_linhas.append(linha)
                continue

            bloco_atual.append(linha)
            continue

        novas_linhas.append(linha)

    if bloco_atual:
        novas_linhas.extend(processar_bloco(bloco_atual))

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ Gerado: {caminho_saida}")

salvar_memoria()

print("\n🔥 Tradução concluída!")
print(f"✅ Memória atualizada: {auto_memory_file}")
print(f"✅ Frases que passaram pelo translator: {traduzidas_por_translator_file}")