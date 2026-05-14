import json
import re
from pathlib import Path

# ============================================
# CONFIG
# ============================================

PASTA_EXPORTADOS = Path("exportados")
PASTA_MEMORY = Path("memory")

ARQUIVO_SAIDA = "memory_extraida.json"

# ============================================
# REGEX
# ============================================

REGEX_ID = re.compile(r'0 SInt64 m_Id = (-?\d+)')
REGEX_LOCALIZED = re.compile(r'1 string m_Localized = "(.*?)"', re.DOTALL)

# ============================================
# FUNÇÕES
# ============================================

def corrigir_mojibake(texto: str) -> str:
    """
    Corrige textos quebrados tipo:
    enÃ©rgico -> enérgico
    nÃ£o -> não
    """
    try:
        return texto.encode("latin1").decode("utf-8")
    except Exception:
        return texto


def desescape_unity(texto: str) -> str:
    """
    Converte escapes do dump Unity:
    \\n -> quebra de linha
    \\" -> "
    \\r -> retorno
    e também corrige mojibake.
    """
    try:
        texto = bytes(texto, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    texto = corrigir_mojibake(texto)
    return texto


def ler_arquivo(caminho: Path) -> str:
    """
    Lê o arquivo tentando preservar acentos corretamente.
    """
    try:
        return caminho.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return caminho.read_text(encoding="latin1", errors="replace")


def extrair_entries(caminho: Path) -> dict:
    """
    Extrai entradas no formato:
    {
      "m_Id": "m_Localized"
    }
    """
    conteudo = ler_arquivo(caminho)
    linhas = conteudo.splitlines()

    resultado = {}
    id_atual = None

    for linha in linhas:
        match_id = REGEX_ID.search(linha)

        if match_id:
            id_atual = match_id.group(1)
            continue

        if id_atual:
            match_loc = REGEX_LOCALIZED.search(linha)

            if match_loc:
                texto = desescape_unity(match_loc.group(1))
                resultado[id_atual] = texto
                id_atual = None

    return resultado


def encontrar_arquivo_memory(nome_exportado: str) -> Path | None:
    """
    Procura arquivo com o mesmo nome na pasta memory.
    """
    caminho = PASTA_MEMORY / nome_exportado

    if caminho.exists():
        return caminho

    return None


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

    resultado_final = {}

    total_arquivos = 0
    arquivos_sem_memory = 0
    total_exportados = 0
    total_encontrados = 0
    total_sem_id_na_memory = 0

    arquivos_exportados = sorted(PASTA_EXPORTADOS.glob("*.txt"))

    print(f"Arquivos em exportados: {len(arquivos_exportados)}")
    print()

    for arquivo_exportado in arquivos_exportados:
        total_arquivos += 1

        print(f"Processando: {arquivo_exportado.name}")

        arquivo_memory = encontrar_arquivo_memory(arquivo_exportado.name)

        if not arquivo_memory:
            arquivos_sem_memory += 1
            print("  ⚠️ Sem arquivo correspondente na memory")
            continue

        try:
            entries_en = extrair_entries(arquivo_exportado)
            entries_pt = extrair_entries(arquivo_memory)
        except Exception as e:
            print(f"  ❌ Erro ao extrair: {e}")
            continue

        encontrados_arquivo = 0
        sem_id_arquivo = 0

        for id_item, texto_en in entries_en.items():
            total_exportados += 1

            texto_pt = entries_pt.get(id_item)

            if texto_pt is None:
                total_sem_id_na_memory += 1
                sem_id_arquivo += 1
                continue

            texto_en = texto_en.strip()
            texto_pt = texto_pt.strip()

            if not texto_en or not texto_pt:
                continue

            resultado_final[texto_en] = texto_pt
            encontrados_arquivo += 1
            total_encontrados += 1

        print(f"  EN IDs: {len(entries_en)}")
        print(f"  PT IDs: {len(entries_pt)}")
        print(f"  Pares encontrados: {encontrados_arquivo}")
        print(f"  IDs sem par na memory: {sem_id_arquivo}")
        print()

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(resultado_final, f, ensure_ascii=False, indent=2)

    print("====================================")
    print("FINALIZADO")
    print(f"Arquivos processados: {total_arquivos}")
    print(f"Arquivos sem memory: {arquivos_sem_memory}")
    print(f"Entradas exportadas lidas: {total_exportados}")
    print(f"Pares encontrados: {total_encontrados}")
    print(f"IDs sem par na memory: {total_sem_id_na_memory}")
    print(f"Total único no JSON: {len(resultado_final)}")
    print(f"Arquivo salvo: {ARQUIVO_SAIDA}")
    print("====================================")


if __name__ == "__main__":
    main()