import os
import re
import json
from pathlib import Path

# ============================================
# CONFIG
# ============================================

input_folder = Path("exportados")
output_folder = Path("traduzidos")
report_folder = Path("relatorios")

memory_file = Path("memoria_revisado.json")
relatorio_file = report_folder / "relatorio_aplicacao_memoria_revisado.json"

os.makedirs(output_folder, exist_ok=True)
os.makedirs(report_folder, exist_ok=True)

# ============================================
# REGEX DO FORMATO UNITY
# ============================================

# Captura:
# 1 string m_Localized = "texto"
#
# Usa (.*) para suportar aspas escapadas dentro do texto.
pattern_localized = re.compile(
    r'(\s*\d+\s+string\s+m_Localized\s*=\s*")(.*)(".*)$'
)

# ============================================
# JSON
# ============================================

def carregar_json(path: Path) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            dados = json.load(f)
            return dados if isinstance(dados, dict) else {}
    except Exception as e:
        print(f"❌ Erro ao carregar JSON {path}: {e}")
        return {}


def salvar_json(path: Path, dados: dict):
    temp = path.with_suffix(path.suffix + ".tmp")

    with open(temp, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    temp.replace(path)


# ============================================
# TEXTO / ENCODING
# ============================================

def corrigir_mojibake(texto: str) -> str:
    """
    Corrige coisas tipo:
    nÃ£o -> não
    enÃ©rgico -> enérgico
    """
    try:
        return texto.encode("latin1").decode("utf-8")
    except Exception:
        return texto


def desescape_unity(texto: str) -> str:
    """
    Converte texto do dump:
    \\n -> quebra real
    \\r -> retorno real
    \\" -> "
    """
    if texto is None:
        return ""

    try:
        texto = bytes(texto, "utf-8").decode("unicode_escape")
    except Exception:
        pass

    return corrigir_mojibake(texto)


def escapar_unity(texto: str) -> str:
    """
    Converte texto normal de volta para string Unity:
    quebra real -> \\n
    aspas -> \\"
    """
    if texto is None:
        return ""

    texto = str(texto)

    texto = texto.replace("\\", "\\\\")
    texto = texto.replace('"', '\\"')
    texto = texto.replace("\r", "\\r")
    texto = texto.replace("\n", "\\n")
    texto = texto.replace("\t", "\\t")

    return texto


def ler_linhas(path: Path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            return f.readlines()
    except Exception:
        with open(path, "r", encoding="latin1", errors="replace") as f:
            return f.readlines()


def separar_quebra_linha(linha: str):
    """
    Mantém a quebra original da linha.
    """
    if linha.endswith("\r\n"):
        return linha[:-2], "\r\n"

    if linha.endswith("\n"):
        return linha[:-1], "\n"

    if linha.endswith("\r"):
        return linha[:-1], "\r"

    return linha, ""


# ============================================
# PROGRESSO
# ============================================

def progresso(atual, total, prefixo=""):
    if total == 0:
        return

    if atual % 500 != 0 and atual != total:
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
# BUSCA NA MEMÓRIA
# ============================================

def buscar_na_memoria(texto_raw: str, memoria: dict):
    """
    Tenta encontrar a tradução no memoria_revisado.json.

    O JSON pode ter sido salvo com:
    - texto desescapado;
    - texto cru;
    - texto com/sem strip.

    Então tentamos algumas variações seguras.
    """

    texto_des = desescape_unity(texto_raw)

    tentativas = [
        texto_raw,
        texto_raw.strip(),
        texto_des,
        texto_des.strip(),
    ]

    for chave in tentativas:
        if chave in memoria and memoria[chave]:
            return memoria[chave], chave

    return None, None


# ============================================
# PROCESSAMENTO
# ============================================

def processar_arquivo(arquivo: str, memoria: dict):
    caminho_entrada = input_folder / arquivo
    caminho_saida = output_folder / f"TRADUZIDO - {arquivo}"

    linhas = ler_linhas(caminho_entrada)
    novas_linhas = []

    stats = {
        "arquivo": arquivo,
        "linhas": len(linhas),
        "entradas_m_Localized": 0,
        "substituidas": 0,
        "nao_encontradas": 0,
        "frases_nao_encontradas": {}
    }

    total = len(linhas)

    for i, linha in enumerate(linhas, start=1):
        progresso(i, total, prefixo=arquivo)

        linha_sem_eol, eol = separar_quebra_linha(linha)

        match = pattern_localized.match(linha_sem_eol)

        if not match:
            novas_linhas.append(linha)
            continue

        stats["entradas_m_Localized"] += 1

        inicio = match.group(1)
        texto_original_raw = match.group(2)
        fim = match.group(3)

        traducao, chave_usada = buscar_na_memoria(texto_original_raw, memoria)

        if traducao is None:
            stats["nao_encontradas"] += 1

            texto_limpo = desescape_unity(texto_original_raw).strip()

            if texto_limpo:
                stats["frases_nao_encontradas"][texto_limpo] = ""

            novas_linhas.append(linha)
            continue

        traducao_escapada = escapar_unity(traducao)

        nova_linha = inicio + traducao_escapada + fim + eol
        novas_linhas.append(nova_linha)

        stats["substituidas"] += 1

    with open(caminho_saida, "w", encoding="utf-8", newline="") as f:
        f.writelines(novas_linhas)

    return stats


# ============================================
# MAIN
# ============================================

def main():
    if not input_folder.exists():
        print(f"❌ Pasta não encontrada: {input_folder}")
        return

    if not memory_file.exists():
        print(f"❌ Arquivo não encontrado: {memory_file}")
        return

    memoria = carregar_json(memory_file)

    if not memoria:
        print(f"❌ Memória vazia ou inválida: {memory_file}")
        return

    arquivos = sorted([
        f for f in os.listdir(input_folder)
        if f.lower().endswith(".txt")
    ])

    print(f"📂 Arquivos encontrados em exportados: {len(arquivos)}")
    print(f"🧠 Entradas em {memory_file}: {len(memoria)}")
    print()

    relatorio = {}

    total_linhas = 0
    total_entries = 0
    total_substituidas = 0
    total_nao_encontradas = 0

    for idx, arquivo in enumerate(arquivos, start=1):
        print(f"\n⚙ [{idx}/{len(arquivos)}] Processando: {arquivo}")

        stats = processar_arquivo(arquivo, memoria)

        relatorio[arquivo] = stats
        salvar_json(relatorio_file, relatorio)

        total_linhas += stats["linhas"]
        total_entries += stats["entradas_m_Localized"]
        total_substituidas += stats["substituidas"]
        total_nao_encontradas += stats["nao_encontradas"]

        print(f"✅ Gerado: {output_folder / ('TRADUZIDO - ' + arquivo)}")
        print(f"   Entradas m_Localized: {stats['entradas_m_Localized']}")
        print(f"   Substituídas: {stats['substituidas']}")
        print(f"   Não encontradas: {stats['nao_encontradas']}")
        print(f"   Relatório atualizado: {relatorio_file}")

    print()
    print("====================================")
    print("FINALIZADO")
    print(f"Arquivos processados: {len(arquivos)}")
    print(f"Linhas lidas: {total_linhas}")
    print(f"Entradas m_Localized: {total_entries}")
    print(f"Substituídas pela memória: {total_substituidas}")
    print(f"Não encontradas na memória: {total_nao_encontradas}")
    print(f"Pasta de saída: {output_folder}")
    print(f"Relatório: {relatorio_file}")
    print("====================================")


if __name__ == "__main__":
    main()