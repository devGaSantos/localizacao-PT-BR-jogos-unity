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
OUTPUT_FILE = os.path.join(MEMORY_FOLDER, "memoria_ollama_corrigida.json")
CHECKPOINT_FILE = os.path.join(MEMORY_FOLDER, "memoria_ollama_checkpoint.json")
FAILURES_FILE = os.path.join(MEMORY_FOLDER, "falhas_ollama.json")

# Ponto de equilíbrio. Se ficar lento, teste 50. Se ficar estável, teste 100.
BATCH_SIZE = 50
NUM_CTX = 3000
TEMPERATURE = 0.03
SAVE_EVERY = 5000
KEEP_ALIVE = "60m"

# Salva checkpoint a cada X itens processados.
# Maior = mais rápido, menor = mais seguro se cair.
SAVE_EVERY = 2000

# Se True, deixa o arquivo final bonito. Se False, salva compacto e mais rápido.
PRETTY_FINAL_JSON = True

os.makedirs(MEMORY_FOLDER, exist_ok=True)


# =========================
# REGEX / CONSTANTES
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

EDGE_PUNCT_PATTERN = re.compile(r"^[\s\.\,\!\?\-\_\—\–\…\"'“”‘’\(\)\[\]<>]+|[\s\.\,\!\?\-\_\—\–\…\"'“”‘’\(\)\[\]<>]+$")

ONLY_PUNCT_PATTERN = re.compile(r"[\s\.\,\!\?\-\_\—\–\…]+")
NUMBER_PATTERN = re.compile(r"\d+")
DECIMAL_PATTERN = re.compile(r"\d+(\.\d+)?")
PERCENT_PATTERN = re.compile(r"\d+%")

PROPER_NAMES = {
    "Ellie",
    "Virgil",
    "Rubrum",
    "Enite",
    "Arden",
    "Kyla",
    "Roy",
    "Diane",
    "Lisa",
    "Highlion",
    "Wisteria",
    "Lucerine Ortu",
    "Alvin",
    "Miscella",
    "Pompom",
    "Ritoring",
    "Gaga Bird",
    "Mara Smith",
}

PRESERVE_EXACT = {
    "",
    "???",
    "...",
    "…",
    "-",
    "_",
    "--",
    "---",
    "----",
    ".",
    "..",
    "OK",
    "OK.",
    "ok",
    "ok.",
}


# =========================
# JSON
# =========================

def carregar_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data if isinstance(data, dict) else {}

    except Exception:
        return {}


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
# TOKENS / TEXTO
# =========================

def proteger_tokens(texto):
    tokens = []

    def replacer(match):
        tokens.append(match.group(0))
        return f"§§TOKEN_{len(tokens) - 1}§§"

    protegido = TOKEN_PATTERN.sub(replacer, texto)
    return protegido, tokens


def restaurar_tokens(texto, tokens):
    for i, token in enumerate(tokens):
        texto = texto.replace(f"§§TOKEN_{i}§§", token)

    return texto


def remover_tokens(texto):
    texto = TOKEN_PATTERN.sub("", texto or "")
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip()


def remover_pontuacao_bordas(texto):
    texto = texto.strip()
    texto = EDGE_PUNCT_PATTERN.sub("", texto)
    return texto.strip()


def texto_base_sem_tokens(texto):
    return remover_pontuacao_bordas(remover_tokens(texto))


def texto_eh_pontuacao_ou_vazio(texto):
    if texto is None:
        return True

    limpo = texto.strip()

    if limpo in PRESERVE_EXACT:
        return True

    return bool(ONLY_PUNCT_PATTERN.fullmatch(limpo))


def texto_eh_numero(texto):
    if texto is None:
        return False

    limpo = texto.strip()

    return (
        bool(NUMBER_PATTERN.fullmatch(limpo))
        or bool(DECIMAL_PATTERN.fullmatch(limpo))
        or bool(PERCENT_PATTERN.fullmatch(limpo))
    )


def texto_eh_so_tokens_ou_tags(texto):
    sem_tokens = remover_tokens(texto)
    return texto_eh_pontuacao_ou_vazio(sem_tokens)


def texto_eh_so_nome_proprio(texto):
    base = texto_base_sem_tokens(texto)

    if not base:
        return False

    return base in PROPER_NAMES


def texto_deve_ficar_igual(texto):
    if texto is None:
        return True

    limpo = texto.strip()

    if limpo in PRESERVE_EXACT:
        return True

    if texto_eh_pontuacao_ou_vazio(limpo):
        return True

    if texto_eh_numero(limpo):
        return True

    if texto_eh_so_tokens_ou_tags(limpo):
        return True

    if texto_eh_so_nome_proprio(limpo):
        return True

    return False


def parece_ingles_nao_traduzido(original, traducao):
    if not isinstance(original, str) or not isinstance(traducao, str):
        return True

    if texto_deve_ficar_igual(original):
        return False

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


def limpar_checkpoint_contaminado(checkpoint):
    limpo = {}
    removidos = 0

    for chave, valor in checkpoint.items():
        if texto_deve_ficar_igual(chave):
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

USER_PROMPT = "Traduza somente os valores deste JSON. Mantenha as chaves exatamente iguais. Responda somente JSON válido."


def limpar_resposta_json(texto):
    texto = texto.strip()

    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?", "", texto).strip()
        texto = re.sub(r"```$", "", texto).strip()

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio != -1 and fim != -1 and fim > inicio:
        texto = texto[inicio:fim + 1]

    return texto


def chamar_ollama_json(session, payload):
    prompt = USER_PROMPT + "\n" + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":")
    )

    response = session.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "keep_alive": KEEP_ALIVE,
            "options": {
                "temperature": TEMPERATURE,
                "num_ctx": NUM_CTX,
            },
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    data = response.json()
    content = data.get("response", "").strip()
    content = limpar_resposta_json(content)

    return json.loads(content)


# =========================
# LOTE
# =========================

def montar_lotes(lista, tamanho):
    for i in range(0, len(lista), tamanho):
        yield lista[i:i + tamanho]


def preparar_lote(lote):
    """
    Retorna:
    payload_protegido: dict enviado ao modelo
    mapa_tokens: dados para restaurar depois
    preservados: entradas que devem ficar iguais e nem vão ao modelo
    """
    payload_protegido = {}
    mapa_tokens = {}
    preservados = {}

    for texto_original in lote:
        if texto_deve_ficar_igual(texto_original):
            preservados[texto_original] = texto_original
            continue

        protegido, tokens = proteger_tokens(texto_original)

        # Regra central:
        # valor antigo do memoria.json é ignorado.
        # a chave em inglês é usada como fonte da tradução.
        payload_protegido[protegido] = protegido

        mapa_tokens[protegido] = {
            "original": texto_original,
            "tokens": tokens,
        }

    return payload_protegido, mapa_tokens, preservados


def traduzir_lote(session, lote):
    payload_protegido, mapa_tokens, preservados = preparar_lote(lote)

    if not payload_protegido:
        return {}, {}, preservados

    try:
        resposta = chamar_ollama_json(session, payload_protegido)

    except Exception as e:
        return {}, {texto: str(e) for texto in lote if not texto_deve_ficar_igual(texto)}, preservados

    traduzidos = {}
    falhas = {}

    for protegido, dados in mapa_tokens.items():
        original = dados["original"]
        tokens = dados["tokens"]

        traducao_protegida = resposta.get(protegido)

        if not isinstance(traducao_protegida, str):
            falhas[original] = "Modelo não devolveu esta chave."
            continue

        traducao_final = restaurar_tokens(traducao_protegida, tokens).strip()

        if parece_ingles_nao_traduzido(original, traducao_final):
            falhas[original] = "Tradução ficou igual ao original em inglês."
            continue

        traduzidos[original] = traducao_final

    return traduzidos, falhas, preservados


# =========================
# RESULTADO FINAL
# =========================

def montar_resultado_ordenado(memoria_original, checkpoint):
    resultado = {}

    for chave in memoria_original.keys():
        if texto_deve_ficar_igual(chave):
            resultado[chave] = chave
        elif chave in checkpoint:
            resultado[chave] = checkpoint[chave]
        else:
            # Se falhou, fica igual à chave no final.
            # O detalhe fica em falhas_ollama.json para correção manual.
            resultado[chave] = chave

    return resultado


# =========================
# MAIN
# =========================

def main():
    memoria_original = carregar_json(INPUT_FILE)
    checkpoint = carregar_json(CHECKPOINT_FILE)
    falhas = carregar_json(FAILURES_FILE)

    if not memoria_original:
        print(f"Não consegui carregar o arquivo: {INPUT_FILE}")
        return

    checkpoint, removidos = limpar_checkpoint_contaminado(checkpoint)

    if removidos > 0:
        print(f"Checkpoint limpo: {removidos} entradas em inglês removidas.")
        salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)

    textos_para_traduzir = []

    for chave in memoria_original.keys():
        if texto_deve_ficar_igual(chave):
            continue

        if chave in checkpoint:
            continue

        textos_para_traduzir.append(chave)

    total = len(textos_para_traduzir)

    if total == 0:
        resultado_final = montar_resultado_ordenado(memoria_original, checkpoint)
        salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
        progresso(1, 1, prefixo="Traduzindo", extra="nenhuma tradução nova")
        return

    lotes = list(montar_lotes(textos_para_traduzir, BATCH_SIZE))
    total_lotes = len(lotes)

    feitos = 0
    ok_total = 0
    falhas_total = 0
    preservados_total = 0
    desde_ultimo_save = 0
    inicio_tempo = time.time()

    session = requests.Session()

    try:
        for numero_lote, lote in enumerate(lotes, start=1):
            eta, velocidade = calcular_eta(inicio_tempo, feitos, total)

            progresso(
                feitos,
                total,
                prefixo=f"Traduzindo lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Preservados: {preservados_total} | Falhas: {falhas_total}"
                )
            )

            traduzidos, falhas_lote, preservados = traduzir_lote(session, lote)

            for original, traducao in traduzidos.items():
                checkpoint[original] = traducao
                falhas.pop(original, None)

            for original in preservados.keys():
                falhas.pop(original, None)

            for original, motivo in falhas_lote.items():
                falhas[original] = motivo

            ok_total += len(traduzidos)
            falhas_total += len(falhas_lote)
            preservados_total += len(preservados)

            feitos += len(lote)
            desde_ultimo_save += len(lote)

            eta, velocidade = calcular_eta(inicio_tempo, feitos, total)

            progresso(
                feitos,
                total,
                prefixo=f"Traduzindo lote {numero_lote}/{total_lotes}",
                extra=(
                    f"ETA: {eta} | Velocidade: {velocidade} | "
                    f"OK: {ok_total} | Preservados: {preservados_total} | Falhas: {falhas_total}"
                )
            )

            if desde_ultimo_save >= SAVE_EVERY or feitos >= total:
                salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)
                salvar_json(FAILURES_FILE, falhas, pretty=True)
                desde_ultimo_save = 0

    finally:
        session.close()

    resultado_final = montar_resultado_ordenado(memoria_original, checkpoint)

    salvar_json(OUTPUT_FILE, resultado_final, pretty=PRETTY_FINAL_JSON)
    salvar_json(CHECKPOINT_FILE, checkpoint, pretty=False)
    salvar_json(FAILURES_FILE, falhas, pretty=True)

    tempo_total = time.time() - inicio_tempo

    print(f"\nConcluído em {formatar_tempo(tempo_total)}.")
    print(f"Traduções válidas salvas: {ok_total}")
    print(f"Preservados corretamente: {preservados_total}")
    print(f"Falhas para correção manual: {falhas_total}")
    print(f"Arquivo final: {OUTPUT_FILE}")
    print(f"Checkpoint: {CHECKPOINT_FILE}")
    print(f"Falhas: {FAILURES_FILE}")


if __name__ == "__main__":
    main()