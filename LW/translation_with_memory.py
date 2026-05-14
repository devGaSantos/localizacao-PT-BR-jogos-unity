import json
import re
import time
from pathlib import Path
from deep_translator import GoogleTranslator

# ============================================
# CONFIG
# ============================================

PASTA_EXPORTADOS = Path("exportados")
PASTA_MEMORY = Path("memory")
PASTA_RELATORIOS = Path("relatorios")

ARQUIVO_SAIDA = Path("memoria_revisado.json")
ARQUIVO_RELATORIO = PASTA_RELATORIOS / "relatorio_faltantes_translator.json"

USAR_CACHE_EXISTENTE = True
SLEEP_TRANSLATOR = 0.05

translator = GoogleTranslator(source="en", target="pt")

PASTA_RELATORIOS.mkdir(exist_ok=True)

# ============================================
# REGEX
# ============================================

REGEX_ID = re.compile(r'\s*0\s+SInt64\s+m_Id\s*=\s*(-?\d+)')
REGEX_LOCALIZED = re.compile(r'(\s*\d+\s+string\s+m_Localized\s*=\s*")(.*)(".*)$')

# ============================================
# JSON
# ============================================

def carregar_json(caminho: Path) -> dict:
    try:
        if caminho.exists():
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
                return dados if isinstance(dados, dict) else {}
    except Exception:
        pass

    return {}


def salvar_json(caminho: Path, dados: dict):
    temp = caminho.with_suffix(caminho.suffix + ".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    temp.replace(caminho)


# ============================================
# PROGRESSO
# ============================================

def progresso(atual, total, prefixo=""):
    if total == 0:
        return

    if atual % 250 != 0 and atual != total:
        return

    pct = atual / total
    barra = int(30 * pct)

    print(
        f"\r{prefixo} [{'█' * barra}{'-' * (30 - barra)}] {pct * 100:.1f}%",
        end=""
    )

    if atual == total:
        print()


# ============================================
# TEXTO / ENCODING
# ============================================

def corrigir_mojibake(texto: str) -> str:
    try:
        return texto.encode("latin1").decode("utf-8")
    except Exception:
        return texto


def desescape_unity(texto: str) -> str:
    if texto is None:
        return ""

    try:
        texto = bytes(texto, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    return corrigir_mojibake(texto)


def ler_linhas(caminho: Path):
    try:
        return caminho.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except Exception:
        return caminho.read_text(encoding="latin1", errors="replace").splitlines()


# ============================================
# PROTEÇÃO DE TOKENS
# ============================================

def proteger_tokens(texto: str):
    if not texto:
        return texto, []

    tokens = []

    def replacer(match):
        tokens.append(match.group(0))
        return f"__TOKEN_{len(tokens) - 1}__"

    pattern = r'(\[.*?\]|\{.*?\}|<.*?>|\(.*?\))'
    protegido = re.sub(pattern, replacer, texto)

    return protegido, tokens


def restaurar_tokens(texto: str, tokens):
    if not texto:
        return texto

    for i, token in enumerate(tokens):
        texto = texto.replace(f"__TOKEN_{i}__", token)

    return texto


# ============================================
# EXTRAÇÃO UNITY POR ID
# ============================================

def extrair_entries(caminho: Path, prefixo="") -> dict:
    linhas = ler_linhas(caminho)

    resultado = {}
    id_atual = None
    total = len(linhas)

    for i, linha in enumerate(linhas, start=1):
        progresso(i, total, prefixo=prefixo)

        match_id = REGEX_ID.match(linha)

        if match_id:
            id_atual = match_id.group(1)
            continue

        if id_atual:
            match_loc = REGEX_LOCALIZED.match(linha)

            if match_loc:
                texto = desescape_unity(match_loc.group(2)).strip()
                resultado[id_atual] = texto
                id_atual = None

    return resultado


# ============================================
# TRADUTOR
# ============================================

def deve_ignorar(texto: str) -> bool:
    if not texto or not texto.strip():
        return True

    return texto.strip() in {
        "???",
        "...",
        "......",
        "-",
        "_",
        "",
    }


def traduzir_com_google(texto: str) -> str:
    if deve_ignorar(texto):
        return texto

    try:
        protegido, tokens = proteger_tokens(texto)
        traduzido = translator.translate(protegido)

        if not traduzido:
            return texto

        traduzido = restaurar_tokens(traduzido, tokens)

        time.sleep(SLEEP_TRANSLATOR)

        return traduzido

    except Exception:
        return texto


# ============================================
# MAIN
# ============================================

def main():
    if not PASTA_EXPORTADOS.exists():
        print(f"❌ Pasta não encontrada: {PASTA_EXPORTADOS}")
        return

    if not PASTA_MEMORY.exists():
        print(f"❌ Pasta não encontrada: {PASTA_MEMORY}")
        return

    memoria_revisado = carregar_json(ARQUIVO_SAIDA) if USAR_CACHE_EXISTENTE else {}
    relatorio = carregar_json(ARQUIVO_RELATORIO)

    total_arquivos = 0
    arquivos_sem_memory = 0
    total_entries_en = 0
    total_por_memory = 0
    total_por_cache = 0
    total_por_translator = 0

    arquivos_exportados = sorted(PASTA_EXPORTADOS.glob("*.txt"))

    print(f"📂 Arquivos em exportados: {len(arquivos_exportados)}")
    print(f"🧠 Cache inicial memoria_revisado: {len(memoria_revisado)}")
    print(f"📊 Relatório inicial: {len(relatorio)} arquivos")
    print()

    for arquivo_exportado in arquivos_exportados:
        total_arquivos += 1

        nome = arquivo_exportado.name
        arquivo_memory = PASTA_MEMORY / nome

        print(f"\n⚙ Processando: {nome}")

        try:
            entries_en = extrair_entries(
                arquivo_exportado,
                prefixo=f"{nome} EN"
            )
        except Exception as e:
            print(f"  ❌ Erro lendo exportado: {e}")
            continue

        if arquivo_memory.exists():
            try:
                entries_pt = extrair_entries(
                    arquivo_memory,
                    prefixo=f"{nome} PT"
                )
            except Exception as e:
                print(f"  ⚠ Erro lendo memory correspondente: {e}")
                entries_pt = {}
        else:
            arquivos_sem_memory += 1
            entries_pt = {}
            print("  ⚠ Sem arquivo correspondente na pasta memory")

        faltantes_arquivo = {}
        por_memory_arquivo = 0
        por_cache_arquivo = 0
        por_translator_arquivo = 0

        ids = list(entries_en.items())
        total_ids = len(ids)

        for idx, (id_item, texto_en) in enumerate(ids, start=1):
            progresso(idx, total_ids, prefixo=f"{nome} MAP")

            total_entries_en += 1

            texto_en = texto_en.strip()

            if not texto_en:
                continue

            texto_pt_memory = entries_pt.get(id_item)

            if texto_pt_memory and texto_pt_memory.strip():
                texto_pt = texto_pt_memory.strip()
                memoria_revisado[texto_en] = texto_pt

                por_memory_arquivo += 1
                total_por_memory += 1
                continue

            if texto_en in memoria_revisado and memoria_revisado[texto_en]:
                por_cache_arquivo += 1
                total_por_cache += 1
                continue

            texto_traduzido = traduzir_com_google(texto_en)

            memoria_revisado[texto_en] = texto_traduzido
            faltantes_arquivo[texto_en] = texto_traduzido

            por_translator_arquivo += 1
            total_por_translator += 1

        if faltantes_arquivo:
            relatorio[nome] = {
                "arquivo": nome,
                "en_ids": len(entries_en),
                "pt_ids_memory": len(entries_pt),
                "usados_da_memory": por_memory_arquivo,
                "usados_do_cache_memoria_revisado": por_cache_arquivo,
                "traduzidos_por_translator": por_translator_arquivo,
                "faltantes_unicos_no_arquivo": len(faltantes_arquivo),
                "frases_nao_encontradas_na_memory_traduzidas_por_translator": faltantes_arquivo,
            }
        else:
            relatorio[nome] = {
                "arquivo": nome,
                "en_ids": len(entries_en),
                "pt_ids_memory": len(entries_pt),
                "usados_da_memory": por_memory_arquivo,
                "usados_do_cache_memoria_revisado": por_cache_arquivo,
                "traduzidos_por_translator": 0,
                "faltantes_unicos_no_arquivo": 0,
                "frases_nao_encontradas_na_memory_traduzidas_por_translator": {},
            }

        salvar_json(ARQUIVO_SAIDA, memoria_revisado)
        salvar_json(ARQUIVO_RELATORIO, relatorio)

        print(f"  EN IDs: {len(entries_en)}")
        print(f"  PT IDs memory: {len(entries_pt)}")
        print(f"  Usados da memory: {por_memory_arquivo}")
        print(f"  Usados do cache: {por_cache_arquivo}")
        print(f"  Usados do translator: {por_translator_arquivo}")
        print(f"  ✅ Progresso salvo em {ARQUIVO_SAIDA}")
        print(f"  ✅ Relatório atualizado em {ARQUIVO_RELATORIO}")

    print()
    print("====================================")
    print("FINALIZADO")
    print(f"Arquivos processados: {total_arquivos}")
    print(f"Arquivos sem correspondente na memory: {arquivos_sem_memory}")
    print(f"Entradas EN lidas: {total_entries_en}")
    print(f"Traduções vindas da pasta memory: {total_por_memory}")
    print(f"Traduções reaproveitadas do cache: {total_por_cache}")
    print(f"Traduções feitas pelo translator: {total_por_translator}")
    print(f"Total único em {ARQUIVO_SAIDA}: {len(memoria_revisado)}")
    print(f"Arquivo principal salvo: {ARQUIVO_SAIDA}")
    print(f"Relatório salvo: {ARQUIVO_RELATORIO}")
    print("====================================")


if __name__ == "__main__":
    main()