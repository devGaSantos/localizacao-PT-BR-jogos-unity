import argparse
import json
import re
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(".")

PASTA_EXPORTADOS = BASE_DIR / "exportados"
PASTA_TRADUZIDOS = BASE_DIR / "traduzidos"
PASTA_TRADUZIDOS_DEFAULTLOCALGROUP = PASTA_TRADUZIDOS / "defaultlocalgroup"
PASTA_TRADUZIDOS_RESOURCES = PASTA_TRADUZIDOS / "resources_assets"
PASTA_RELATORIOS = BASE_DIR / "relatorios"
PASTA_NAO_IMPORTAR = BASE_DIR / "nao_importar"

ARQUIVO_MEMORIA = BASE_DIR / "memoria_missoes.json"

PREFIXOS_NAO_IMPORTAVEIS = ("base-",)


# ============================================================
# REGEX
# ============================================================

RE_LANGUAGE_KEYS_START = re.compile(r'\s*\d+\s+(?:string|vector)\s+m_languageKeys\b')
RE_LANGUAGE_VALUES_START = re.compile(r'\s*\d+\s+vector\s+m_languageValues\b')

RE_FIELD_NAME = re.compile(r'\s*\d+\s+string\s+m_fieldName\s*=\s*"(.*)"')
RE_M_KEYS_START = re.compile(r'\s*\d+\s+vector\s+m_keys\b')
RE_M_VALUES_START = re.compile(r'\s*\d+\s+(?:string|vector)\s+m_values\b')

RE_STRING_DATA_LINE = re.compile(r'^(\s*\d+\s+string\s+data\s*=\s*)"(.*)"(\s*)$')
RE_INT_DATA_LINE = re.compile(r'\s*\d+\s+int\s+data\s*=\s*(-?\d+)')

RE_STRING_DATA_VALUE = re.compile(r'\s*\d+\s+string\s+data\s*=\s*"(.*)"')


# ============================================================
# FUNÇÕES DE STRING
# ============================================================

def decode_dump_string(raw: str) -> str:
    """
    Converte conteúdo de string do dump para texto normal.

    Ex:
      Olá\\nMundo -> Olá\nMundo
      \\\"texto\\\" -> "texto"
    """
    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw


def encode_dump_string(texto: str) -> str:
    """
    Converte texto normal para conteúdo seguro dentro do dump.

    Ex:
      Olá\nMundo -> Olá\\nMundo
      "texto" -> \\\"texto\\\"
    """
    return json.dumps(texto, ensure_ascii=False)[1:-1]


def carregar_json(caminho: Path, padrao):
    if not caminho.exists():
        return padrao

    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(caminho: Path, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)

    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def arquivo_importavel(caminho: Path) -> bool:
    nome = caminho.name.casefold()
    return not any(nome.startswith(prefixo) for prefixo in PREFIXOS_NAO_IMPORTAVEIS)


def listar_exports_importaveis():
    return sorted(
        arquivo
        for arquivo in PASTA_EXPORTADOS.glob("*")
        if arquivo.is_file() and arquivo_importavel(arquivo)
    )


def separar_saidas_nao_importaveis():
    movidos = []
    if not PASTA_TRADUZIDOS.exists():
        return movidos

    for arquivo in sorted(PASTA_TRADUZIDOS.glob("*")):
        if not arquivo.is_file() or arquivo_importavel(arquivo):
            continue

        PASTA_NAO_IMPORTAR.mkdir(parents=True, exist_ok=True)
        destino = PASTA_NAO_IMPORTAR / arquivo.name
        contador = 1
        while destino.exists():
            destino = PASTA_NAO_IMPORTAR / f"{arquivo.stem}.{contador}{arquivo.suffix}"
            contador += 1
        arquivo.replace(destino)
        movidos.append({"origem": str(arquivo), "destino": str(destino)})

    return movidos


def pasta_saida_para_arquivo(caminho: Path) -> Path:
    if "-resources.assets-" in caminho.name:
        return PASTA_TRADUZIDOS_RESOURCES
    return PASTA_TRADUZIDOS_DEFAULTLOCALGROUP


def organizar_saidas_importaveis_existentes():
    movidos = []
    if not PASTA_TRADUZIDOS.exists():
        return movidos

    for arquivo in sorted(PASTA_TRADUZIDOS.glob("*")):
        if not arquivo.is_file() or not arquivo_importavel(arquivo):
            continue

        pasta_destino = pasta_saida_para_arquivo(arquivo)
        pasta_destino.mkdir(parents=True, exist_ok=True)
        destino = pasta_destino / arquivo.name
        arquivo.replace(destino)
        movidos.append({"origem": str(arquivo), "destino": str(destino)})

    return movidos


def separar_saidas_obsoletas(exports_atuais):
    nomes_atuais = {arquivo.name for arquivo in exports_atuais}
    movidos = []

    for pasta in (PASTA_TRADUZIDOS_DEFAULTLOCALGROUP, PASTA_TRADUZIDOS_RESOURCES):
        if not pasta.exists():
            continue

        for arquivo in sorted(pasta.glob("*")):
            if not arquivo.is_file() or arquivo.name in nomes_atuais:
                continue

            PASTA_NAO_IMPORTAR.mkdir(parents=True, exist_ok=True)
            destino = PASTA_NAO_IMPORTAR / arquivo.name
            contador = 1
            while destino.exists():
                destino = PASTA_NAO_IMPORTAR / f"{arquivo.stem}.{contador}{arquivo.suffix}"
                contador += 1
            arquivo.replace(destino)
            movidos.append({"origem": str(arquivo), "destino": str(destino)})

    return movidos


# ============================================================
# PARSER DE IDIOMAS
# ============================================================

def extrair_mapa_idiomas(linhas):
    """
    Lê:

      m_languageKeys:
        [0] Default
        [1] ko
        [2] en

      m_languageValues:
        [0] 0
        [1] 1
        [2] 2

    E retorna:
      {
        "Default": 0,
        "ko": 1,
        "en": 2
      }

    Importante:
    O script usa esse mapa para descobrir qual ID representa o inglês.
    """

    language_keys = []
    language_values = []

    modo = None

    for linha in linhas:
        if RE_LANGUAGE_KEYS_START.match(linha):
            modo = "language_keys"
            continue

        if RE_LANGUAGE_VALUES_START.match(linha):
            modo = "language_values"
            continue

        # Depois que terminou m_languageValues e começou outra seção grande,
        # podemos parar.
        if modo == "language_values" and re.match(r'\s*0\s+vector\s+m_fieldKeys\b', linha):
            break

        if modo == "language_keys":
            match = RE_STRING_DATA_VALUE.match(linha)
            if match:
                language_keys.append(decode_dump_string(match.group(1)))

        elif modo == "language_values":
            match = RE_INT_DATA_LINE.match(linha)
            if match:
                language_values.append(int(match.group(1)))

    mapa = {}

    for idx, key in enumerate(language_keys):
        if idx < len(language_values):
            mapa[key] = language_values[idx]

    return mapa


# ============================================================
# EXTRAÇÃO DE TEXTOS EM INGLÊS
# ============================================================

def finalizar_campo_para_extracao(campo_atual, memoria, ocorrencias, arquivo_nome, en_id):
    if not campo_atual:
        return

    field_name = campo_atual.get("field_name")
    keys = campo_atual.get("keys", [])
    values = campo_atual.get("values", [])

    if en_id not in keys:
        return

    idx_en = keys.index(en_id)

    if idx_en >= len(values):
        return

    texto_en = values[idx_en].strip()

    if not texto_en:
        return

    if texto_en not in memoria:
        memoria[texto_en] = ""

    ocorrencias.append({
        "arquivo": arquivo_nome,
        "field_name": field_name,
        "ingles": texto_en
    })


def extrair_ingles_de_arquivo(caminho: Path, memoria: dict):
    texto = caminho.read_text(encoding="utf-8")
    linhas = texto.splitlines(keepends=True)

    mapa_idiomas = extrair_mapa_idiomas(linhas)

    if "en" not in mapa_idiomas:
        return {
            "arquivo": caminho.name,
            "erro": "Idioma 'en' não encontrado em m_languageKeys/m_languageValues.",
            "extraidos": 0
        }

    en_id = mapa_idiomas["en"]

    campo_atual = None
    modo = None
    ocorrencias = []

    for linha in linhas:
        match_field = RE_FIELD_NAME.match(linha)
        if match_field:
            finalizar_campo_para_extracao(
                campo_atual,
                memoria,
                ocorrencias,
                caminho.name,
                en_id
            )

            campo_atual = {
                "field_name": decode_dump_string(match_field.group(1)),
                "keys": [],
                "values": []
            }
            modo = None
            continue

        if campo_atual is None:
            continue

        if RE_M_KEYS_START.match(linha):
            modo = "keys"
            continue

        if RE_M_VALUES_START.match(linha):
            modo = "values"
            continue

        if modo == "keys":
            match_int = RE_INT_DATA_LINE.match(linha)
            if match_int:
                campo_atual["keys"].append(int(match_int.group(1)))

        elif modo == "values":
            match_str = RE_STRING_DATA_VALUE.match(linha)
            if match_str:
                campo_atual["values"].append(decode_dump_string(match_str.group(1)))

    finalizar_campo_para_extracao(
        campo_atual,
        memoria,
        ocorrencias,
        caminho.name,
        en_id
    )

    return {
        "arquivo": caminho.name,
        "extraidos": len(ocorrencias),
        "ocorrencias": ocorrencias
    }


def modo_extrair():
    PASTA_EXPORTADOS.mkdir(parents=True, exist_ok=True)
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

    memoria = carregar_json(ARQUIVO_MEMORIA, {})

    if not isinstance(memoria, dict):
        raise ValueError("memoria_missoes.json precisa ser um objeto JSON: { \"english\": \"tradução\" }")

    arquivos = listar_exports_importaveis()

    if not arquivos:
        print(f"Nenhum arquivo encontrado em: {PASTA_EXPORTADOS.resolve()}")
        return

    total_antes = len(memoria)
    relatorio = []

    print("======================================")
    print("Extraindo missões em inglês")
    print("======================================")
    print(f"Pasta: {PASTA_EXPORTADOS.resolve()}")
    print("Ignorados por seguranca: base-*")
    print()

    for arquivo in arquivos:
        try:
            resultado = extrair_ingles_de_arquivo(arquivo, memoria)
            relatorio.append(resultado)

            if "erro" in resultado:
                print(f"{arquivo.name}: ERRO - {resultado['erro']}")
            else:
                print(f"{arquivo.name}: {resultado['extraidos']} ocorrências em inglês")

        except Exception as e:
            relatorio.append({
                "arquivo": arquivo.name,
                "erro": str(e),
                "extraidos": 0
            })
            print(f"{arquivo.name}: ERRO - {e}")

    total_depois = len(memoria)

    salvar_json(ARQUIVO_MEMORIA, memoria)
    salvar_json(PASTA_RELATORIOS / "relatorio_extracao_missoes.json", relatorio)

    print()
    print("Finalizado.")
    print(f"Frases únicas antes: {total_antes}")
    print(f"Frases únicas depois: {total_depois}")
    print(f"Novas frases adicionadas: {total_depois - total_antes}")
    print(f"Memória gerada/atualizada em: {ARQUIVO_MEMORIA.resolve()}")
    print(f"Relatório em: {(PASTA_RELATORIOS / 'relatorio_extracao_missoes.json').resolve()}")


# ============================================================
# TRADUÇÃO DOS DUMPS USANDO A MEMÓRIA
# ============================================================

def traduzir_conteudo_dump(conteudo: str, memoria: dict, arquivo_nome: str):
    linhas = conteudo.splitlines(keepends=True)
    mapa_idiomas = extrair_mapa_idiomas(linhas)

    if "en" not in mapa_idiomas:
        return conteudo, {
            "arquivo": arquivo_nome,
            "erro": "Idioma 'en' não encontrado em m_languageKeys/m_languageValues.",
            "substituidas": 0,
            "sem_traducao": []
        }

    en_id = mapa_idiomas["en"]

    novas_linhas = []

    campo_atual = None
    modo = None

    substituidas = 0
    sem_traducao = []

    for linha in linhas:
        match_field = RE_FIELD_NAME.match(linha)
        if match_field:
            campo_atual = {
                "field_name": decode_dump_string(match_field.group(1)),
                "keys": [],
                "value_index": 0
            }
            modo = None
            novas_linhas.append(linha)
            continue

        if campo_atual is not None and RE_M_KEYS_START.match(linha):
            modo = "keys"
            novas_linhas.append(linha)
            continue

        if campo_atual is not None and RE_M_VALUES_START.match(linha):
            modo = "values"
            campo_atual["value_index"] = 0
            novas_linhas.append(linha)
            continue

        if campo_atual is not None and modo == "keys":
            match_int = RE_INT_DATA_LINE.match(linha)
            if match_int:
                campo_atual["keys"].append(int(match_int.group(1)))

            novas_linhas.append(linha)
            continue

        if campo_atual is not None and modo == "values":
            match_str_line = RE_STRING_DATA_LINE.match(linha)

            if match_str_line:
                prefixo = match_str_line.group(1)
                raw_value = match_str_line.group(2)
                sufixo = match_str_line.group(3)

                idx = campo_atual["value_index"]
                campo_atual["value_index"] += 1

                idioma_id = None
                if idx < len(campo_atual["keys"]):
                    idioma_id = campo_atual["keys"][idx]

                if idioma_id == en_id:
                    texto_en = decode_dump_string(raw_value)

                    traducao = memoria.get(texto_en)

                    if traducao and isinstance(traducao, str) and traducao.strip():
                        novo_raw = encode_dump_string(traducao)
                        nova_linha = f'{prefixo}"{novo_raw}"{sufixo}'
                        novas_linhas.append(nova_linha)
                        substituidas += 1
                        continue

                    if texto_en.strip():
                        sem_traducao.append({
                            "field_name": campo_atual.get("field_name"),
                            "ingles": texto_en
                        })

            novas_linhas.append(linha)
            continue

        novas_linhas.append(linha)

    relatorio = {
        "arquivo": arquivo_nome,
        "substituidas": substituidas,
        "sem_traducao": sem_traducao
    }

    return "".join(novas_linhas), relatorio


def modo_translate():
    PASTA_EXPORTADOS.mkdir(parents=True, exist_ok=True)
    PASTA_TRADUZIDOS.mkdir(parents=True, exist_ok=True)
    PASTA_TRADUZIDOS_DEFAULTLOCALGROUP.mkdir(parents=True, exist_ok=True)
    PASTA_TRADUZIDOS_RESOURCES.mkdir(parents=True, exist_ok=True)
    PASTA_RELATORIOS.mkdir(parents=True, exist_ok=True)

    if not ARQUIVO_MEMORIA.exists():
        print(f"Arquivo de memória não encontrado: {ARQUIVO_MEMORIA.resolve()}")
        print("Rode primeiro sem -translate para gerar memoria_missoes.json.")
        return

    memoria = carregar_json(ARQUIVO_MEMORIA, {})

    if not isinstance(memoria, dict):
        raise ValueError("memoria_missoes.json precisa ser um objeto JSON: { \"english\": \"tradução\" }")

    arquivos = listar_exports_importaveis()

    if not arquivos:
        print(f"Nenhum arquivo encontrado em: {PASTA_EXPORTADOS.resolve()}")
        return

    relatorio_geral = []
    saidas_separadas = separar_saidas_nao_importaveis()
    saidas_organizadas = organizar_saidas_importaveis_existentes()
    saidas_obsoletas = separar_saidas_obsoletas(arquivos)

    print("======================================")
    print("Aplicando traduções nas missões")
    print("======================================")
    print(f"Pasta origem: {PASTA_EXPORTADOS.resolve()}")
    print(f"Pasta saída: {PASTA_TRADUZIDOS.resolve()}")
    print("Ignorados por seguranca: base-*")
    for item in saidas_separadas:
        print(f"Separado para nao importar: {item['destino']}")
    for item in saidas_obsoletas:
        print(f"Saida obsoleta separada: {item['destino']}")
    if saidas_organizadas:
        print(f"Saidas antigas organizadas: {len(saidas_organizadas)}")
    print()

    for arquivo in arquivos:
        try:
            conteudo = arquivo.read_text(encoding="utf-8")

            novo_conteudo, relatorio = traduzir_conteudo_dump(
                conteudo,
                memoria,
                arquivo.name
            )

            pasta_saida = pasta_saida_para_arquivo(arquivo)
            caminho_saida = pasta_saida / arquivo.name
            caminho_saida.write_text(novo_conteudo, encoding="utf-8")

            relatorio_geral.append(relatorio)

            if "erro" in relatorio:
                print(f"{arquivo.name}: ERRO - {relatorio['erro']}")
            else:
                print(
                    f"{arquivo.name}: "
                    f"{relatorio['substituidas']} substituições, "
                    f"{len(relatorio['sem_traducao'])} sem tradução"
                )

        except Exception as e:
            relatorio_geral.append({
                "arquivo": arquivo.name,
                "erro": str(e),
                "substituidas": 0,
                "sem_traducao": []
            })
            print(f"{arquivo.name}: ERRO - {e}")

    salvar_json(PASTA_RELATORIOS / "relatorio_translate_missoes.json", relatorio_geral)

    total_substituidas = sum(
        item.get("substituidas", 0)
        for item in relatorio_geral
    )

    total_sem_traducao = sum(
        len(item.get("sem_traducao", []))
        for item in relatorio_geral
    )

    print()
    print("Finalizado.")
    print(f"Total substituídas: {total_substituidas}")
    print(f"Total sem tradução: {total_sem_traducao}")
    print(f"DefaultLocalGroup: {PASTA_TRADUZIDOS_DEFAULTLOCALGROUP.resolve()}")
    print(f"Resources.assets: {PASTA_TRADUZIDOS_RESOURCES.resolve()}")
    print(f"Relatório em: {(PASTA_RELATORIOS / 'relatorio_translate_missoes.json').resolve()}")


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Extrai e aplica traduções de missões do Little Witch in the Woods."
    )

    parser.add_argument(
        "-translate",
        action="store_true",
        help="Aplica memoria_missoes.json nos arquivos de missoes/exportados e gera missoes/traduzidos."
    )

    args = parser.parse_args()

    if args.translate:
        modo_translate()
    else:
        modo_extrair()


if __name__ == "__main__":
    main()
