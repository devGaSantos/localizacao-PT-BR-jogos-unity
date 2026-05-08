import os
import re
import json
import time
import requests


# =========================
# CONFIGURAÇÕES
# =========================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "tradutor-game-ptbr"

MEMORY_FOLDER = "memory"

INPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria.json")
IGNORE_FILE = os.path.join(MEMORY_FOLDER, "ignore.json")

OUTPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria_ollama_corrigida.json")
CHECKPOINT_FILE = os.path.join(MEMORY_FOLDER, "memoria_ollama_checkpoint.json")
FAILURES_FILE = os.path.join(MEMORY_FOLDER, "falhas_ollama.json")

# Começa com 50 no 7B.
# Se estiver estável e rápido, teste 75.
# Se falhar muito, reduza para 30.
BATCH_SIZE = 50

TEMPERATURE = 0.03
NUM_CTX = 3000
REQUEST_TIMEOUT = 900
KEEP_ALIVE = "60m"

# Quanto maior, menos escrita em disco.
SAVE_EVERY = 50

# False = mais rápido e arquivo menor.
# True = arquivo final legível.
PRETTY_FINAL_JSON = False

# Use True se seu checkpoint antigo tiver muita entrada em inglês salva como tradução.
# Depois pode deixar False para velocidade.
CLEAN_CHECKPOINT_ON_START = True

# Se True, exige que todos os __PH_0__, __PH_1__ etc voltem intactos.
VALIDAR_PLACEHOLDERS = True

# Se True, força a resposta JSON pelo Ollama.
# Se ficar lento, teste False.
USE_FORMAT_JSON = True

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


# =========================
# JSON
# =========================

def carregar_json_dict(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


def carregar_ignore(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
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

    return formatar_tempo(eta_segundos), f"{traducoes_por_minuto:.1f} trad/min"


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
    """
    Troca tags/placeholders reais do jogo por __PH_0__, __PH_1__ etc.
    Modelos pequenos preservam melhor esse formato do que §§TOKEN_0§§.
    """
    if not TOKEN_PATTERN.search(texto):
        return texto, None

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
    """
    Garante que o modelo não removeu, quebrou ou reorganizou placeholders.
    """
    if not VALIDAR_PLACEHOLDERS:
        return True

    esperados = PH_PATTERN.findall(texto_protegido_original)
    recebidos = PH_PATTERN.findall(traducao_protegida or "")

    return esperados == recebidos


def remover_tokens(texto):
    if not texto:
        return ""

    if not TOKEN_PATTERN.search(texto):
        return SPACE_PATTERN.sub(" ", texto).strip()

    texto = TOKEN_PATTERN.sub("", texto)
    texto = SPACE_PATTERN.sub(" ", texto)
    return texto.strip()


def parece_ingles_nao_traduzido(original, traducao):
    """
    Impede checkpoint contaminado com valor igual à chave.
    """
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


def limpar_checkpoint_contaminado(checkpoint, ignore_set):
    limpo = {}
    removidos = 0

    for chave, valor in checkpoint.items():
        if chave in ignore_set:
            limpo[chave] = valor
            continue

        if parece_ingles_nao_traduzido(chave, valor):
            removidos += 1
            continue

        limpo[chave] = valor

    return limpo, removidos


# =========================
# OLLAMA
# =========================

USER_PROMPT = (
    "Traduza apenas os valores para PT-BR. "
    "Mantenha as chaves iguais. "
    "Preserve placeholders como __PH_0__ e __PH_1__. "
    "Responda JSON."
)


def limpar_resposta_json(texto):
    texto = texto.strip()

    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?", "", texto).strip()
        texto = re.sub(r"```$", "", texto).strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio != -1 and fim != -1 and fim > inicio:
        return texto[inicio:fim + 1]

    return texto


def chamar_ollama_json(session, payload):
    prompt = USER_PROMPT + "\n" + json.dumps(
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
# LOTES COM IDS NUMÉRICOS
# =========================

def montar_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


def preparar_lote(lote):
    """
    Em vez de mandar:
    {
      "frase gigante": "frase gigante"
    }

    manda:
    {
      "0": "frase",
      "1": "frase"
    }

    Isso é mais rápido e evita falha por chave alterada.
    """
    payload = {}
    mapa = {}

    for idx, texto_original in enumerate(lote):
        id_texto = str(idx)

        protegido, tokens = proteger_tokens(texto_original)

        payload[id_texto] = protegido

        mapa[id_texto] = {
            "original": texto_original,
            "protegido": protegido,
            "tokens": tokens,
        }

    return payload, mapa


def traduzir_lote(session, lote):
    payload, mapa = preparar_lote(lote)

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
        protegido = dados["protegido"]
        tokens = dados["tokens"]

        traducao_protegida = resposta.get(id_texto)

        if not isinstance(traducao_protegida, str):
            falhas[original] = "Modelo não devolveu este ID."
            continue

        traducao_protegida = traducao_protegida.strip()

        if not placeholders_validos(protegido, traducao_protegida):
            falhas[original] = "Placeholders protegidos corrompidos, ausentes ou fora de ordem."
            continue

        traducao_final = restaurar_tokens(traducao_protegida, tokens).strip()

        if parece_ingles_nao_traduzido(original, traducao_final):
            falhas[original] = "Tradução ficou igual ao original em inglês."
            continue

        traduzidos[original] = traducao_final

    return traduzidos, falhas


# =========================
# RESULTADO FINAL
# =========================

def montar_resultado_ordenado(memoria_original, checkpoint, ignore_set):
    resultado = {}

    for chave in memoria_original.keys():
        if chave in ignore_set:
            resultado[chave] = chave
        elif chave in checkpoint:
            resultado[chave] = checkpoint[chave]
        else:
            # Se falhou, fica igual à chave.
            # O motivo fica em falhas_ollama.json.
            resultado[chave] = chave

    return resultado


# =========================
# MAIN
# =========================

def main():
    memoria_original = carregar_json_dict(INPUT_FILE)
    checkpoint = carregar_json_dict(CHECKPOINT_FILE)
    falhas = carregar_json_dict(FAILURES_FILE)
    ignore_set = carregar_ignore(IGNORE_FILE)

    if not memoria_original:
        print(f"Não consegui carregar o arquivo: {INPUT_FILE}")
        return

    if not ignore_set:
        print(f"Aviso: ignore.json vazio ou não encontrado: {IGNORE_FILE}")
        print("Rode primeiro: python .\\gerar_ignore.py")
        print("Continuando mesmo assim...")

    if CLEAN_CHECKPOINT_ON_START:
        checkpoint, removidos = limpar_checkpoint_contaminado(checkpoint, ignore_set)

        if removidos > 0:
            print(f"Checkpoint limpo: {removidos} entradas em inglês removidas.")
            salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)

    textos_para_traduzir = [
        chave
        for chave in memoria_original.keys()
        if chave not in ignore_set and chave not in checkpoint
    ]

    total = len(textos_para_traduzir)

    if total == 0:
        resultado_final = montar_resultado_ordenado(
            memoria_original,
            checkpoint,
            ignore_set
        )

        salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
        progresso(1, 1, prefixo="Traduzindo", extra="nenhuma tradução nova")
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
                prefixo=f"Traduzindo lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Falhas: {falhas_total}"
                )
            )

            traduzidos, falhas_lote = traduzir_lote(session, lote)

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
                prefixo=f"Traduzindo lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Falhas: {falhas_total}"
                )
            )

            if desde_ultimo_save >= SAVE_EVERY or feitos >= total:
                salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)
                salvar_json(FAILURES_FILE, falhas, pretty=False)
                desde_ultimo_save = 0

    finally:
        session.close()

    resultado_final = montar_resultado_ordenado(
        memoria_original,
        checkpoint,
        ignore_set
    )

    salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
    salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)
    salvar_json(FAILURES_FILE, falhas, pretty=False)

    tempo_total = time.time() - inicio_tempo

    print(f"\nConcluído em {formatar_tempo(tempo_total)}.")
    print(f"Traduções válidas salvas: {ok_total}")
    print(f"Falhas para correção manual: {falhas_total}")
    print(f"Arquivo final: {OUTPUT_FILE}")
    print(f"Checkpoint: {CHECKPOINT_FILE}")
    print(f"Falhas: {FAILURES_FILE}")


if __name__ == "__main__":
    main()