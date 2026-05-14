import os
import re
import json
import time
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source="en", target="pt")

input_folder = "exportados"
output_folder = "traduzidos"
memory_folder = "memory"

memory_file = "memoria.json"
manual_memory_file = "memoria_manual.json"
faltantes_file = "string_tables_faltantes.json"

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

def salvar_json(path, dados):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

# =========================
# PROGRESSO
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
# REGEX DO FORMATO UNITY
# =========================

pattern = re.compile(r'(\s*\d+\s+string\s+m_Localized\s*=\s*")([^"]*)(".*)')
pattern_id = re.compile(r'\s*0\s+SInt64\s+m_Id\s*=\s*(-?\d+)')
pattern_localized = re.compile(r'(\s*\d+\s+string\s+m_Localized\s*=\s*")([^"]*)(".*)')

# =========================
# FUNÇÕES UNITY / MEMORY
# =========================

def corrigir_mojibake(texto: str) -> str:
    try:
        return texto.encode("latin1").decode("utf-8")
    except Exception:
        return texto

def desescape_unity(texto: str) -> str:
    try:
        texto = bytes(texto, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    texto = corrigir_mojibake(texto)
    return texto

def ler_arquivo(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.readlines()
    except:
        with open(path, "r", encoding="latin1", errors="replace") as f:
            return f.readlines()

def extrair_por_id(caminho):
    """
    Retorna:
    {
      "278980001792": "texto localizado"
    }
    """
    linhas = ler_arquivo(caminho)

    resultado = {}
    id_atual = None

    for linha in linhas:
        match_id = pattern_id.match(linha)

        if match_id:
            id_atual = match_id.group(1)
            continue

        if id_atual:
            match_loc = pattern_localized.match(linha)

            if match_loc:
                texto = desescape_unity(match_loc.group(2))
                resultado[id_atual] = texto
                id_atual = None

    return resultado

def carregar_memory_por_arquivo():
    """
    Carrega os arquivos da pasta memory indexados por nome de arquivo.

    Resultado:
    {
      "UI_en-CAB-xxx.txt": {
        "278980001792": "texto em pt"
      }
    }
    """
    index = {}

    if not os.path.isdir(memory_folder):
        print(f"⚠ Pasta memory não encontrada: {memory_folder}")
        return index

    arquivos_memory = [
        f for f in os.listdir(memory_folder)
        if f.lower().endswith(".txt")
    ]

    print(f"📚 Arquivos memory encontrados: {len(arquivos_memory)}")

    for arquivo in arquivos_memory:
        caminho = os.path.join(memory_folder, arquivo)

        try:
            index[arquivo] = extrair_por_id(caminho)
        except Exception as e:
            print(f"⚠ Erro lendo memory {arquivo}: {e}")
            index[arquivo] = {}

    return index

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

        if not traduzido:
            return texto

        memoria[texto] = traduzido
        time.sleep(0.05)

        return traduzido

    except:
        return texto

# =========================
# INDEXAR MEMORY
# =========================

memory_por_arquivo = carregar_memory_por_arquivo()

# =========================
# PROCESSAMENTO
# =========================

arquivos = [f for f in os.listdir(input_folder) if f.lower().endswith(".txt")]

print(f"📂 Arquivos encontrados em exportados: {len(arquivos)}")

faltantes = {}

total_faltantes = 0
total_com_memory = 0

for arquivo in arquivos:
    caminho_entrada = os.path.join(input_folder, arquivo)
    caminho_saida = os.path.join(output_folder, f"TRADUZIDO - {arquivo}")

    print(f"\n⚙ Processando: {arquivo}")

    linhas = ler_arquivo(caminho_entrada)
    total = len(linhas)
    novas_linhas = []

    memory_ids = memory_por_arquivo.get(arquivo, {})

    id_atual = None

    for i, linha in enumerate(linhas, start=1):
        progresso(i, total, prefixo=arquivo)

        match_id = pattern_id.match(linha)

        if match_id:
            id_atual = match_id.group(1)
            novas_linhas.append(linha)
            continue

        match = pattern.match(linha)

        if match:
            inicio = match.group(1)
            texto_original = match.group(2)
            fim = match.group(3)

            texto_original_limpo = desescape_unity(texto_original).strip()

            # =========================
            # VERIFICA SE EXISTE NA MEMORY PELO MESMO ARQUIVO + MESMO ID
            # =========================

            if id_atual and id_atual in memory_ids:
                total_com_memory += 1
            else:
                if texto_original_limpo:
                    faltantes[texto_original_limpo] = ""
                    total_faltantes += 1

            texto_traduzido = traduzir(texto_original)

            if not isinstance(texto_traduzido, str):
                texto_traduzido = texto_original

            nova_linha = inicio + texto_traduzido + fim + "\n"
            novas_linhas.append(nova_linha)

            id_atual = None
        else:
            novas_linhas.append(linha)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        f.writelines(novas_linhas)

    print(f"✅ Gerado: {caminho_saida}")

# =========================
# FINAL
# =========================

salvar_memoria()
salvar_json(faltantes_file, faltantes)

print("\n🔥 Tradução completa (rápida + estável)")
print(f"✅ Memória salva: {memory_file}")
print(f"✅ Faltantes salvos: {faltantes_file}")
print(f"📌 Frases com correspondência na memory: {total_com_memory}")
print(f"⚠ Frases sem correspondência na memory: {total_faltantes}")
print(f"⚠ Faltantes únicos no JSON: {len(faltantes)}")