import os
import re
import json
import time
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="en", target="pt")

input_folder = "exportados"
output_folder = "traduzidos"
memory_file = "memoria.json"
manual_memory_file = "memoria_manual.json"

os.makedirs(output_folder, exist_ok=True)

# =========================
# MEMÓRIA
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
# PROGRESSO (LEVE)
# =========================

def progresso(atual, total, prefixo=""):
    if total == 0:
        return

    if atual % 500 != 0 and atual != total:
        return

    pct = atual / total
    barra = int(30 * pct)
    print(f"\r{prefixo} [{'█'*barra}{'-'*(30-barra)}] {pct*100:.1f}%", end="")

    if atual == total:
        print()

# =========================
# TRADUÇÃO
# =========================

def traduzir(texto):
    if not texto or not texto.strip():
        return texto

    texto_limpo = texto.strip()

    # ignora lixo
    if texto_limpo in ["???", "...", "-", "_"]:
        return texto

    # memória manual
    if texto in memoria_manual:
        return memoria_manual[texto]

    # memória automática
    if texto in memoria:
        return memoria[texto]

    try:
        traduzido = translator.translate(texto)

        # 🔥 evita None
        if not traduzido:
            return texto

        memoria[texto] = traduzido
        time.sleep(0.05)

        return traduzido

    except:
        return texto

# =========================
# REGEX DO FORMATO UNITY
# =========================

pattern = re.compile(r'(\s*\d+\s+string\s+m_Localized\s*=\s*")([^"]*)(".*)')

# =========================
# PROCESSAMENTO
# =========================

arquivos = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]

print(f"📂 Arquivos encontrados: {len(arquivos)}")

for arquivo in arquivos:
    caminho_entrada = os.path.join(input_folder, arquivo)
    caminho_saida = os.path.join(output_folder, f"TRADUZIDO - {arquivo}")

    print(f"\n⚙ Processando: {arquivo}")

    with open(caminho_entrada, "r", encoding="utf-8") as f:
        linhas = f.readlines()

    total = len(linhas)
    novas_linhas = []

    for i, linha in enumerate(linhas, start=1):
        progresso(i, total, prefixo=arquivo)

        match = pattern.match(linha)

        if match:
            inicio = match.group(1)
            texto_original = match.group(2)
            fim = match.group(3)

            texto_traduzido = traduzir(texto_original)

            # 🔥 GARANTE STRING
            if not isinstance(texto_traduzido, str):
                texto_traduzido = texto_original

            nova_linha = inicio + texto_traduzido + fim + "\n"
            novas_linhas.append(nova_linha)
        else:
            novas_linhas.append(linha)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ Gerado: {caminho_saida}")

# =========================
# FINAL
# =========================

salvar_memoria()

print("\n🔥 Tradução completa (rápida + estável)")