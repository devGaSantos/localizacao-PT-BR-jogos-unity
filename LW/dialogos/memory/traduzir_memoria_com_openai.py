import os
import re
import json
import time
import shutil
import argparse
import requests
from datetime import datetime


# =========================
# CONFIGURAÇÕES
# =========================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "lwitw-ptbr"  # ou "tradutor-game-ptbr"

MEMORY_FOLDER = "memory"

# Entrada principal: só o que faltou
INPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria_faltantes.json")

# Saída revisada pelo Ollama
OUTPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria_faltantes_corrigidos.json")

# Arquivo que será atualizado quando usar -update
MEMORIA_ATUALIZADA_FILE = os.path.join(MEMORY_FOLDER, "memoria_atualizada.json")

# Arquivos auxiliares
IGNORE_FILE = os.path.join(MEMORY_FOLDER, "ignore.json")
CHECKPOINT_FILE = os.path.join(MEMORY_FOLDER, "memoria_faltantes_checkpoint.json")
FAILURES_FILE = os.path.join(MEMORY_FOLDER, "falhas_faltantes_ollama.json")
REPORT_FILE = os.path.join(MEMORY_FOLDER, "relatorio_faltantes_ollama.txt")

# Começa com 50 no 7B.
# Se estiver estável e rápido, teste 75.
# Se falhar muito, reduza para 30.
BATCH_SIZE = 50

TEMPERATURE = 0.03
NUM_CTX = 8192
REQUEST_TIMEOUT = 900
KEEP_ALIVE = "60m"

SAVE_EVERY = 50
PRETTY_FINAL_JSON = True
PRETTY_CHECKPOINT_JSON = False

# Use True se seu checkpoint antigo tiver muita entrada em inglês salva como tradução.
CLEAN_CHECKPOINT_ON_START = True

# Se True, exige que todos os __PH_0__, __PH_1__ etc voltem intactos.
VALIDAR_PLACEHOLDERS = True

# Se True, força a resposta JSON pelo Ollama.
USE_FORMAT_JSON = True

# Se True, entradas ignoradas/código puro são copiadas como valor original atual.
COPIAR_IGNORADOS_NO_RESULTADO = True

os.makedirs(MEMORY_FOLDER, exist_ok=True)


# =========================
# REGEX
# =========================

TOKEN_PATTERN = re.compile(
    r"("
    r"\[lua\(.*?\)\]"
    r"|\[[^\]]+\]"
    r"|</?[^>]+>"
    r"|\{[^}]+\}"
    r"|\\n"
    r"|\\r"
    r"|\\t"
    r"|%[sdif]"
    r")"
)

PH_PATTERN = re.compile(r"__PH_\d+__")
SPACE_PATTERN = re.compile(r"\s+")
CJK_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


# =========================
# JSON
# =========================

def carregar_json_dict(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def carregar_ignore(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, list):
            return set(data)

        if isinstance(data, dict):
            return set(data.keys())

        return set()

    except Exception:
        return set()


def salvar_json(path, data, pretty=False):
    with open(path, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))


def criar_backup(path):
    if not os.path.exists(path):
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base, ext = os.path.splitext(path)
    backup_path = f"{base}.backup-{timestamp}{ext}"
    shutil.copy2(path, backup_path)
    return backup_path


# =========================
# TEMPO / PROGRESSO
# =========================

def formatar_tempo(segundos):
    segundos = int(max(0, segundos))

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60

    if horas > 0:
        return f"{horas:02d}h {minutos:02d}m {segs:02d}s"

    if minutos > 0:
        return f"{minutos:02d}m {segs:02d}s"

    return f"{segs:02d}s"


def calcular_eta(inicio_tempo, feitos, total):
    if feitos <= 0:
        return "calculando...", "calculando..."

    decorrido = time.time() - inicio_tempo

    if decorrido <= 0:
        return "calculando...", "calculando..."

    media_por_item = decorrido / feitos
    restantes = max(0, total - feitos)
    eta_segundos = restantes * media_por_item
    traducoes_por_minuto = feitos / (decorrido / 60)

    return formatar_tempo(eta_segundos), f"{traducoes_por_minuto:.1f} itens/min"


def progresso(atual, total, prefixo="", extra=""):
    if total <= 0:
        return

    pct = atual / total
    barra = int(30 * pct)

    texto = (
        f"\r{prefixo} "
        f"[{'█' * barra}{'-' * (30 - barra)}] "
        f"{pct * 100:.1f}% "
        f"({atual}/{total})"
    )

    if extra:
        texto += f" | {extra}"

    print(texto, end="", flush=True)

    if atual >= total:
        print()


# =========================
# PLACEHOLDERS / TOKENS
# =========================

def proteger_tokens(texto):
    if not TOKEN_PATTERN.search(texto or ""):
        return texto, []

    tokens = []

    def replacer(match):
        tokens.append(match.group(0))
        return f"__PH_{len(tokens) - 1}__"

    protegido = TOKEN_PATTERN.sub(replacer, texto)
    return protegido, tokens


def restaurar_tokens(texto, tokens):
    if not tokens:
        return texto

    for i, token in enumerate(tokens):
        texto = texto.replace(f"__PH_{i}__", token)

    return texto


def placeholders_validos(texto_protegido_original, traducao_protegida):
    if not VALIDAR_PLACEHOLDERS:
        return True

    esperados = PH_PATTERN.findall(texto_protegido_original)
    recebidos = PH_PATTERN.findall(traducao_protegida or "")

    return esperados == recebidos


def remover_tokens(texto):
    if not texto:
        return ""

    texto = TOKEN_PATTERN.sub("", texto)
    texto = SPACE_PATTERN.sub(" ", texto)
    return texto.strip()


def tem_cjk(texto):
    return bool(CJK_PATTERN.search(texto or ""))


def parece_ingles_nao_traduzido(original, traducao):
    if not isinstance(original, str) or not isinstance(traducao, str):
        return True

    original_limpo = original.strip()
    traducao_limpa = traducao.strip()

    if not original_limpo:
        return False

    if original_limpo == traducao_limpa:
        return True

    original_sem_tokens = remover_tokens(original_limpo)
    traducao_sem_tokens = remover_tokens(traducao_limpa)

    if original_sem_tokens and original_sem_tokens == traducao_sem_tokens:
        return True

    return False


def parece_codigo_puro(texto):
    if not isinstance(texto, str):
        return False

    t = texto.strip()

    if not t:
        return True

    if t.startswith("[lua(") and t.endswith("]"):
        return True

    if t.startswith("(GetGlobalVariable("):
        return True

    if re.fullmatch(r"[\[\]\(\)\{\}_$A-Za-z0-9\"'=<>!&|.,:\s+-]+", t):
        if "GetGlobalVariable" in t or "GetLocalizedString" in t or "GetItemName" in t:
            return True

    return False


def limpar_checkpoint_contaminado(checkpoint, ignore_set):
    limpo = {}
    removidos = 0

    for chave, valor in checkpoint.items():
        if chave in ignore_set or parece_codigo_puro(chave):
            limpo[chave] = valor
            continue

        if parece_ingles_nao_traduzido(chave, valor):
            removidos += 1
            continue

        if tem_cjk(valor):
            removidos += 1
            continue

        limpo[chave] = valor

    return limpo, removidos


# =========================
# OLLAMA
# =========================

USER_PROMPT = """
Revise e traduza para PT-BR os valores do JSON abaixo.

IMPORTANTE:
- As chaves numéricas devem permanecer iguais.
- Cada valor contém um objeto com:
  - "source": texto original em inglês
  - "current": tradução atual, que pode estar ruim, literal, em inglês ou com erro
- Retorne APENAS um JSON no formato:
  {
    "0": "valor corrigido em PT-BR",
    "1": "valor corrigido em PT-BR"
  }

REGRAS:
- Use o "source" para entender o sentido correto.
- Use o "current" apenas como referência, corrigindo quando estiver ruim.
- Preserve placeholders como __PH_0__, __PH_1__, etc.
- Não altere, remova, reordene ou duplique placeholders.
- Mantenha temporalidade verbal: passado no passado, presente no presente, futuro no futuro.
- Corrija concordância de gênero e número.
- Não traduza ao pé da letra se ficar estranho.
- Use PT-BR natural, casual e fluido.
- Não use palavras arcaicas/rebuscadas demais.
- Não invente contexto.
- Não explique nada.
- Responda somente JSON válido.
""".strip()


def limpar_resposta_json(texto):
    texto = (texto or "").strip()

    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?", "", texto).strip()
        texto = re.sub(r"```$", "", texto).strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio != -1 and fim != -1 and fim > inicio:
        return texto[inicio:fim + 1]

    return texto


def chamar_ollama_json(session, payload):
    prompt = USER_PROMPT + "\n\n" + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":")
    )

    request_json = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "keep_alive": KEEP_ALIVE,
        "options": {
            "temperature": TEMPERATURE,
            "num_ctx": NUM_CTX,
        },
    }

    if USE_FORMAT_JSON:
        request_json["format"] = "json"

    response = session.post(
        OLLAMA_URL,
        json=request_json,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()
    content = data.get("response", "")
    content = limpar_resposta_json(content)

    return json.loads(content)


# =========================
# LOTES
# =========================

def montar_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


def preparar_lote(lote, memoria_faltantes):
    """
    Envia IDs numéricos.
    Cada item leva:
      source  = chave original em inglês, com tokens protegidos
      current = valor atual, com tokens protegidos quando possível

    O modelo deve devolver:
      { "0": "tradução revisada", "1": "..." }
    """
    payload = {}
    mapa = {}

    for idx, texto_original in enumerate(lote):
        id_texto = str(idx)
        valor_atual = memoria_faltantes.get(texto_original, texto_original)

        source_protegido, source_tokens = proteger_tokens(texto_original)

        # Para evitar bagunça com placeholders corrompidos no valor atual,
        # a validação final usa os placeholders da chave original.
        current_protegido = valor_atual

        if source_tokens:
            for i, token in enumerate(source_tokens):
                current_protegido = current_protegido.replace(token, f"__PH_{i}__")

        payload[id_texto] = {
            "source": source_protegido,
            "current": current_protegido,
        }

        mapa[id_texto] = {
            "original": texto_original,
            "valor_atual": valor_atual,
            "source_protegido": source_protegido,
            "source_tokens": source_tokens,
        }

    return payload, mapa


def traduzir_lote(session, lote, memoria_faltantes):
    payload, mapa = preparar_lote(lote, memoria_faltantes)

    if not payload:
        return {}, {}

    try:
        resposta = chamar_ollama_json(session, payload)

    except Exception as e:
        motivo = str(e)
        return {}, {texto: motivo for texto in lote}

    traduzidos = {}
    falhas = {}

    for id_texto, dados in mapa.items():
        original = dados["original"]
        source_protegido = dados["source_protegido"]
        source_tokens = dados["source_tokens"]

        traducao_protegida = resposta.get(id_texto)

        if not isinstance(traducao_protegida, str):
            falhas[original] = "Modelo não devolveu este ID."
            continue

        traducao_protegida = traducao_protegida.strip()

        if not placeholders_validos(source_protegido, traducao_protegida):
            falhas[original] = "Placeholders protegidos corrompidos, ausentes ou fora de ordem."
            continue

        traducao_final = restaurar_tokens(traducao_protegida, source_tokens).strip()

        if not traducao_final:
            falhas[original] = "Tradução vazia."
            continue

        if tem_cjk(traducao_final):
            falhas[original] = "Tradução contém CJK."
            continue

        if parece_ingles_nao_traduzido(original, traducao_final) and not parece_codigo_puro(original):
            falhas[original] = "Tradução ficou igual ao original em inglês."
            continue

        traduzidos[original] = traducao_final

    return traduzidos, falhas


# =========================
# RESULTADO FINAL
# =========================

def montar_resultado_ordenado(memoria_faltantes, checkpoint, ignore_set):
    resultado = {}

    for chave, valor_atual in memoria_faltantes.items():
        if chave in ignore_set or parece_codigo_puro(chave):
            resultado[chave] = valor_atual if COPIAR_IGNORADOS_NO_RESULTADO else chave
        elif chave in checkpoint:
            resultado[chave] = checkpoint[chave]
        else:
            # Se falhou, mantém o valor atual do memoria_faltantes.
            # O motivo fica em falhas_faltantes_ollama.json.
            resultado[chave] = valor_atual

    return resultado


def salvar_relatorio(path, dados):
    linhas = []
    linhas.append("RELATÓRIO - REVISÃO DE MEMÓRIA FALTANTE")
    linhas.append("=" * 80)

    for chave, valor in dados.items():
        linhas.append(f"{chave}: {valor}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas))


# =========================
# MODO UPDATE
# =========================

def atualizar_memoria_atualizada():
    memoria_atualizada = carregar_json_dict(MEMORIA_ATUALIZADA_FILE)
    faltantes_corrigidos = carregar_json_dict(OUTPUT_FILE)

    if not memoria_atualizada:
        print(f"Não consegui carregar: {MEMORIA_ATUALIZADA_FILE}")
        return

    if not faltantes_corrigidos:
        print(f"Não consegui carregar: {OUTPUT_FILE}")
        return

    backup_path = criar_backup(MEMORIA_ATUALIZADA_FILE)

    atualizados = 0
    adicionados = 0
    iguais = 0

    for chave, valor_corrigido in faltantes_corrigidos.items():
        if chave in memoria_atualizada:
            if memoria_atualizada[chave] == valor_corrigido:
                iguais += 1
            else:
                memoria_atualizada[chave] = valor_corrigido
                atualizados += 1
        else:
            memoria_atualizada[chave] = valor_corrigido
            adicionados += 1

    salvar_json(MEMORIA_ATUALIZADA_FILE, memoria_atualizada, pretty=True)

    print("🔥 Update concluído!")
    print(f"🧠 Arquivo atualizado: {MEMORIA_ATUALIZADA_FILE}")

    if backup_path:
        print(f"🛡️ Backup criado: {backup_path}")

    print(f"🔁 Chaves atualizadas: {atualizados}")
    print(f"➕ Chaves adicionadas: {adicionados}")
    print(f"🟰 Chaves já iguais: {iguais}")
    print(f"📦 Total em memoria_atualizada.json: {len(memoria_atualizada)}")


# =========================
# MAIN
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-update",
        action="store_true",
        help="Atualiza memory/memoria_atualizada.json usando memory/memoria_faltantes_corrigidos.json"
    )
    args = parser.parse_args()

    if args.update:
        atualizar_memoria_atualizada()
        return

    memoria_faltantes = carregar_json_dict(INPUT_FILE)
    checkpoint = carregar_json_dict(CHECKPOINT_FILE)
    falhas = carregar_json_dict(FAILURES_FILE)
    ignore_set = carregar_ignore(IGNORE_FILE)

    if not memoria_faltantes:
        print(f"Não consegui carregar o arquivo: {INPUT_FILE}")
        return

    if not ignore_set:
        print(f"Aviso: ignore.json vazio ou não encontrado: {IGNORE_FILE}")
        print("Continuando mesmo assim...")

    if CLEAN_CHECKPOINT_ON_START:
        checkpoint, removidos = limpar_checkpoint_contaminado(checkpoint, ignore_set)

        if removidos > 0:
            print(f"Checkpoint limpo: {removidos} entradas em inglês/CJK removidas.")
            salvar_json(CHECKPOINT_FILE, checkpoint, pretty=PRETTY_CHECKPOINT_JSON)

    textos_para_traduzir = [
        chave
        for chave in memoria_faltantes.keys()
        if chave not in ignore_set
        and chave not in checkpoint
        and not parece_codigo_puro(chave)
    ]

    total = len(textos_para_traduzir)

    if total == 0:
        resultado_final = montar_resultado_ordenado(
            memoria_faltantes,
            checkpoint,
            ignore_set
        )

        salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
        progresso(1, 1, prefixo="Revisando", extra="nenhuma revisão nova")
        print(f"Arquivo final: {OUTPUT_FILE}")
        return

    total_lotes = (total + BATCH_SIZE - 1) // BATCH_SIZE

    feitos = 0
    ok_total = 0
    falhas_total = 0
    desde_ultimo_save = 0
    inicio_tempo = time.time()

    session = requests.Session()

    try:
        for numero_lote, lote in enumerate(
            montar_lotes(textos_para_traduzir, BATCH_SIZE),
            start=1
        ):
            eta, velocidade = calcular_eta(inicio_tempo, feitos, total)

            progresso(
                feitos,
                total,
                prefixo=f"Revisando lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Falhas: {falhas_total}"
                )
            )

            traduzidos, falhas_lote = traduzir_lote(
                session,
                lote,
                memoria_faltantes
            )

            if traduzidos:
                checkpoint.update(traduzidos)

                for original in traduzidos.keys():
                    falhas.pop(original, None)

            if falhas_lote:
                falhas.update(falhas_lote)

            ok_total += len(traduzidos)
            falhas_total += len(falhas_lote)

            feitos += len(lote)
            desde_ultimo_save += len(lote)

            eta, velocidade = calcular_eta(inicio_tempo, feitos, total)

            progresso(
                feitos,
                total,
                prefixo=f"Revisando lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Falhas: {falhas_total}"
                )
            )

            if desde_ultimo_save >= SAVE_EVERY or feitos >= total:
                salvar_json(CHECKPOINT_FILE, checkpoint, pretty=PRETTY_CHECKPOINT_JSON)
                salvar_json(FAILURES_FILE, falhas, pretty=True)
                desde_ultimo_save = 0

    finally:
        session.close()

    resultado_final = montar_resultado_ordenado(
        memoria_faltantes,
        checkpoint,
        ignore_set
    )

    salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
    salvar_json(CHECKPOINT_FILE, checkpoint, pretty=PRETTY_CHECKPOINT_JSON)
    salvar_json(FAILURES_FILE, falhas, pretty=True)

    tempo_total = time.time() - inicio_tempo

    resumo = {
        "tempo_total": formatar_tempo(tempo_total),
        "entrada": INPUT_FILE,
        "saida": OUTPUT_FILE,
        "checkpoint": CHECKPOINT_FILE,
        "falhas": FAILURES_FILE,
        "total_para_revisar": total,
        "traducoes_validas_salvas": ok_total,
        "falhas_para_revisao": falhas_total,
        "total_no_resultado_final": len(resultado_final),
    }

    salvar_relatorio(REPORT_FILE, resumo)

    print(f"\nConcluído em {formatar_tempo(tempo_total)}.")
    print(f"Traduções/revisões válidas salvas: {ok_total}")
    print(f"Falhas para correção manual: {falhas_total}")
    print(f"Arquivo final: {OUTPUT_FILE}")
    print(f"Checkpoint: {CHECKPOINT_FILE}")
    print(f"Falhas: {FAILURES_FILE}")
    print(f"Relatório: {REPORT_FILE}")
    print("")
    print("Para aplicar no memoria_atualizada.json, rode:")
    print("python script.py -update")


if __name__ == "__main__":
    main()