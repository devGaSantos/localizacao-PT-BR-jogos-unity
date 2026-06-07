import json
import re
import time
import sys
from pathlib import Path
from openai import OpenAI

try:
    from config_api import OPENAI_API_KEY, OPENAI_MODEL
except ImportError:
    OPENAI_API_KEY = "COLE_SUA_CHAVE_AQUI"
    OPENAI_MODEL = "gpt-5-mini"


# ============================================================
# CONFIGURAÇÃO
# ============================================================

INPUT_PATH = "frases_nao_modificadas_desde_commit.json"
OUTPUT_PATH = "frases_corrigidas_openai.json"
CHECKPOINT_PATH = "checkpoint_corrigidas_openai.json"
ERRORS_PATH = "erros_openai.json"
REPORT_PATH = "relatorio_corrigidas_openai.json"
BEFORE_AFTER_REPORT_PATH = "relatorio_antes_depois_corrigidas.json"

# Quantas frases mandar por chamada.
BATCH_SIZE = 50

# LIMIT = 50, 500, 1000 para teste.
# LIMIT = None para processar tudo.
LIMIT = None

# Pausa entre chamadas.
SLEEP_BETWEEN_REQUESTS = 0.5

# Tentativas por lote em caso de erro.
MAX_RETRIES = 3

# Tamanho visual da barra de progresso.
PROGRESS_BAR_WIDTH = 30


# ============================================================
# CLIENTE OPENAI
# ============================================================

client = OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# TERMOS PROTEGIDOS
# ============================================================

PROTECTED_EN_TO_PT_TERMS = {
    "White Cat God": "Deus Gato Branco",
    "Black Cat God": "Deus Gato Preto",
    "Leafbeaver": "Castor de Folha",
    "Squishychub": "Fofuxo",
    "Blue Lightning Workshop": "Oficina do Raio Azul",
    "Clock Alley": "Beco dos Relógios",
    "Records Museum": "Museu dos Registros",
    "Prickly Vine": "Vinha Espinhosa",
    "Prickly Vine Core": "Núcleo da Vinha Espinhosa",
    "Red Forget-me-not Tea": "Chá de Miosótis Vermelho",
}

PROTECTED_PT_TERMS = [
    "Deus Gato Branco",
    "Deus Gato Preto",
    "Castor de Folha",
    "Fofuxo",
    "Oficina do Raio Azul",
    "Beco dos Relógios",
    "Museu dos Registros",
    "Vinha Espinhosa",
    "Núcleo da Vinha Espinhosa",
    "Chá de Miosótis Vermelho",
]

PROTECTED_CHARACTER_NAMES = [
    "Diane",
    "Roy",
    "Ellie",
    "Kyla",
    "Aurea",
    "Auresa",
    "Enite",
    "Arden",
    "Rubrum",
    "Clala",
    "Vinch",
    "Lisa",
    "Kate",
    "Alvin",
    "Virgil",
    "Aria",
    "Aiden",
    "Arin",
    "Rahel",
    "Kent",
    "Diana",
]


# ============================================================
# REGRAS DE LOCALIZAÇÃO
# ============================================================

SYSTEM_PROMPT = """
Você é um revisor e localizador profissional de jogos contratado para revisar a localização PT-BR de Little Witch in the Woods.

Você NÃO deve reescrever tudo.
Você deve ser conservador.
A melhor resposta muitas vezes é manter a tradução atual exatamente igual.

Sua tarefa:
- Receber pares de texto no formato inglês original -> tradução atual em PT-BR.
- Comparar o inglês com a tradução atual.
- Corrigir apenas a tradução em PT-BR, e somente quando houver necessidade real.
- Manter a chave em inglês exatamente igual.
- Retornar somente JSON válido.
- Não adicionar comentários, explicações, markdown ou texto fora do JSON.

QUANDO ALTERAR:
Altere a tradução somente se houver pelo menos um destes problemas claros:
- A tradução não expressa corretamente o sentido do inglês.
- A tradução está desconexa, sem sentido ou incoerente.
- A tradução está literal demais e soa artificial em PT-BR.
- Há erro claro de concordância, regência, artigo, preposição ou tempo verbal.
- Há erro claro de gênero quando o contexto for explícito.
- Há termo de glossário/lore errado.
- Há frase com estrutura calcada no inglês que prejudica a naturalidade.
- Há informação faltando ou informação adicionada indevidamente.
- Há tom muito diferente do inglês sem motivo.

QUANDO NÃO ALTERAR:
- Não altere quando a diferença for apenas preferência estilística.
- Não altere apenas para deixar a frase "mais bonita".
- Não altere apenas pontuação se a pontuação atual já funciona.
- Não troque uma frase natural por outra igualmente natural sem ganho claro.
- Não troque tom casual por formal, nem formal por casual, sem motivo claro.
- Não remova informação presente no inglês ou na tradução atual.
- Não remova sujeito, objeto, artigo, pronome ou advérbio se isso deixar a frase mais vaga.
- Não transforme uma frase expressiva em uma frase genérica demais.
- Não altere infinitivo para gerúndio em textos curtos de UI sem contexto. Exemplo: "Sleeping" pode ser "Dormir" ou "Dormindo"; sem contexto, mantenha a tradução atual.

ARTIGOS, PREPOSIÇÕES E TEMPOS VERBAIS:
- Corrija artigos, preposições e tempos verbais quando estiverem explicitamente errados pelo sentido do inglês.
- Não adicione nem remova artigo antes de nome próprio só por preferência.
- Em PT-BR natural, nomes próprios de personagens frequentemente usam artigo definido quando a frase pede isso: "o Roy", "a Ellie", "a Kyla", "o Alvin".
- Não remova artigos antes de nomes próprios se isso deixar a frase artificial, dura ou com ordem de palavras estranha.
- Não force artigo em todo nome próprio.
- Evite estruturas calcadas no inglês, como "Que tipo de pessoa Roy era?".
- Prefira construções naturais como "Que tipo de pessoa era o Roy?" ou "Como era o Roy?", conforme o contexto.
- Se a tradução atual já usa artigo de forma natural, não remova sem motivo claro.
- Se a tradução atual não usa artigo e a frase está natural, não adicione sem motivo claro.

GÊNERO EM PRIMEIRA PESSOA:
- O inglês muitas vezes não marca gênero em frases de primeira pessoa.
- Não altere gênero de primeira pessoa sem contexto explícito do falante.
- Se não for possível identificar com segurança se quem fala é masculino ou feminino, tente usar uma formulação neutra em PT-BR.
- A formulação neutra só deve ser usada se preservar o sentido, o tom, a intenção e a força da frase original.
- Não neutralize apagando informação importante.
- Se a forma neutra ficar artificial, vaga, fraca, longa demais ou mudar o sentido, mantenha o gênero que já estava na tradução anterior.
- Nunca troque masculino por feminino, ou feminino por masculino, apenas por tentativa de melhorar a frase.
- Só altere o gênero se houver evidência clara no texto, no nome do falante, no contexto fornecido ou no glossário.

Exemplos corretos de neutralização:
- "Obrigado. Então serei direto." -> "Agradeço. Então vou direto ao ponto."
  Correto, porque preserva agradecimento e a ideia de ser direto.
- "Estou cansado." -> "Cansei."
  Correto, porque preserva a ideia de cansaço.
- "Estou perdido." -> "Não sei onde estou."
  Correto se o sentido for estar perdido fisicamente.

Exemplos ruins:
- "Obrigado. Então serei direto." -> "Agradeço."
  Ruim, porque remove "serei direto".
- "Estou cansado." -> "Não estou bem."
  Ruim, porque muda cansaço para mal-estar genérico.
- "Estou perdido." -> "Estou confuso."
  Ruim, porque pode mudar perdido fisicamente para confusão mental.
- "Vamos brincar juntas mais vezes!" -> "Vamos brincar mais vezes!"
  Ruim se remove a ideia de together/juntas sem necessidade.

REGRA CRÍTICA DE NOMES DE PERSONAGENS:
- Nunca altere nomes próprios de personagens já presentes na tradução atual.
- Não corrija nomes de personagens com base apenas no inglês.
- Se a tradução atual usa "Diane", mantenha "Diane", mesmo que o inglês diga "Diana".
- Se a tradução atual usa "Roy", "Ellie", "Kyla", "Aurea", "Enite", "Arden", "Rubrum", "Clala", "Vinch", "Lisa", "Kate", "Alvin", "Virgil", mantenha exatamente igual.
- Só altere nome próprio se houver regra explícita no glossário dizendo para alterar.
- Nomes próprios não devem ser traduzidos, adaptados, corrigidos, feminizados, masculinizados ou normalizados.

LORE, NOMES E TÍTULOS:
- Não reinterpretar gênero de nomes próprios, títulos, entidades, deuses, criaturas, locais ou itens já padronizados.
- Pronomes como "she", "he", "her" ou "his" podem indicar quem está sendo mencionado, mas não autorizam mudar o gênero de um nome/título estabelecido.
- Só ajuste o gênero de um nome/título se o próprio termo original em inglês deixar isso explicitamente claro ou se o glossário do projeto definir assim.
- Se a tradução atual já contém um nome próprio, título ou termo padronizado, preserve esse termo exatamente, salvo se ele estiver claramente errado pelo glossário.
- "White Cat God" deve ser sempre "Deus Gato Branco".
- Nunca trocar "Deus Gato Branco" por "Deusa Gata Branca".
- "Black Cat God" deve ser sempre "Deus Gato Preto".
- Nunca trocar "Deus Gato Preto" por "Deusa Gata Preta".

TOM EM DIÁLOGO PT-BR:
- Não transforme diálogo natural em norma culta artificial.
- Em falas casuais, não troque automaticamente "Vi ele" por "O vi", "te ajudar" por "ajudar você", ou construções naturais por formas mais formais.
- Corrija gramática apenas quando o erro prejudicar naturalidade, sentido ou qualidade da localização.
- Priorize PT-BR falado natural quando for diálogo.
- Não troque palavras comuns por termos formais sem necessidade.
- Evite "jamais", "o fiz", "o fizeram", "a que", "de que" quando a frase ficar formal demais para o tom do jogo.
- Use formas naturais de PT-BR, desde que corretas e fiéis ao inglês.

REGRA DE VERBOS E REFERENTES AMBÍGUOS:
- Não troque verbos ambíguos como "have", "get", "take", "make it", "bring", "carry", "go", "do" sem contexto claro.
- Se a tradução atual escolhe uma interpretação possível e não está claramente errada, mantenha.
- Só altere "have" para "levar", "comer", "pegar", "ter" etc. quando o contexto deixar claro.
- Não troque "Thank you for making it" para "Obrigado por ter vindo" sem contexto claro de chegada/presença.
- Não transforme automaticamente "them" em "eles", "elas", "os", "as", "trazê-los", "levá-los" etc. quando o referente não estiver claro.
- Em PT-BR, muitas vezes é mais natural e seguro omitir o objeto quando ele já está implícito pelo contexto.
- Se a tradução atual omite o objeto de forma natural, não adicione pronome de gênero sem contexto explícito.
- Não traduza "did" literalmente como "o fez", "o fizeram", "morreu" ou "morreram" sem contexto explícito.
- Quando "did" retoma uma ação anterior e o contexto não está disponível, mantenha a tradução atual se ela estiver compreensível.

PRESERVAÇÃO TÉCNICA OBRIGATÓRIA:
- Preserve tags e placeholders exatamente quando aparecerem:
  [em], [em1], [em2], [/em], [/em1], [/em2],
  <shake>, </shake>, <wave>, </wave>,
  <color=#...>, </color>,
  {0}, {1}, %s, \\n, \\r,
  [lua(GetLocalizedString(...))]
- Nunca apague, quebre ou traduza funções LUA.
- Nunca remova escapes.
- Nunca remova quebras de linha representadas como \\n.
- Se o inglês tiver tags/placeholders técnicos, a tradução corrigida deve preservá-los.

REGRA CRÍTICA DE PRONOMES E REFERENTES:
- Não remova pronomes como ele, ela, eles, elas, isso, aquele, aquela quando eles representam informação presente no inglês.
- Se o inglês diz "she was there", preserve a ideia de "ela estava lá", a menos que o contexto prove outra coisa.
- Não neutralize gênero apagando o referente da frase.
- Neutralização só é permitida quando preserva o referente e o sentido.
- Se não souber quem é "she/he", preserve o referente indicado pelo inglês como "ela/ele" quando isso for necessário para manter o sentido, em vez de apagar o pronome.
- Não transforme "ela estava lá" em "estava lá" se isso cria ambiguidade sobre quem estava lá.

REGRA DE DECISÃO FINAL:
- Se houver dúvida entre alterar e manter, mantenha a tradução atual.
- Se a alteração proposta não corrigir um erro claro, mantenha a tradução atual.
- Se a alteração deixar a frase mais vaga, mantenha a tradução atual.
- Se a alteração mudar o tom sem necessidade, mantenha a tradução atual.
- Se a alteração remover informação do inglês ou da tradução atual, mantenha a tradução atual.
- Altere apenas quando a nova versão for claramente mais fiel, natural e correta que a anterior.
- Quando houver símbolos, tags ou placeholders funcionando como substantivos/conceitos mágicos, preserve a função sintática deles. Não reposicione o símbolo de forma que ele vire adjetivo de outra palavra ou quebre a estrutura da frase.

GLOSSÁRIO E PADRÕES:
- White Cat God = Deus Gato Branco.
- Black Cat God = Deus Gato Preto.
- Leafbeaver = Castor de Folha.
- Squishychub = Fofuxo.
- Fluffy Squishychub Donut = Donut de Fofuxo.
- Pebble... = Pedrinha...
- Pebble. Gravel! = Pedrinhas. Cascalho!
- Caw, quando associado a Rahel/RahelServant = Crá! ou Craá!
- Dispensary = sala de poções / área de preparo de poções. Nunca farmácia/enfermaria.
- Blue Lightning Workshop = Oficina do Raio Azul.
- Clock Alley = Beco dos Relógios.
- Records Department = Seção de Registros ou Departamento de Registros.
- Records Museum = Museu dos Registros.
- Prickly Vine = Vinha Espinhosa.
- Prickly Vine Core = Núcleo da Vinha Espinhosa.
- Moonhare whiskers = bigodes de Lebre Lunar.
- Red Forget-me-not Tea = Chá de Miosótis Vermelho.
- grocer = dona da mercearia / vendedora. Evitar "merceeira".
- Wisteria, quando for nome próprio/local/termo estabelecido = Wisteria.
- wisteria flowers, quando for a planta = flores de glicínia.
- Não traduzir Wisteria automaticamente sem contexto; manter consistência com a tradução atual.
- Diane = Diane. Não trocar para Diana.
- pies, quando usado como moeda = moedas. Nunca deixar "pies" em inglês.

REGRA CRÍTICA SOBRE CHAVES:
- As chaves em inglês são identificadores técnicos.
- Copie cada chave exatamente como recebida, caractere por caractere.
- Não normalize espaços.
- Não troque aspas, apóstrofos, reticências, hífens ou pontuação.
- Não remova \\r, \\n, espaços invisíveis ou caracteres especiais.
- Não corrija inglês nas chaves.
- Não reescreva, traduza, simplifique ou altere nenhuma chave.
- Altere somente os valores em PT-BR.

REGRAS DE SAÍDA:
- Retorne um JSON objeto.
- Cada chave deve ser exatamente o texto em inglês recebido.
- Cada valor deve ser a tradução final em PT-BR.
- Não remova nenhuma chave.
- Não adicione nenhuma chave.
- Não altere a ordem intencionalmente.
- Se a tradução atual estiver correta, retorne o mesmo valor exatamente.
"""


# ============================================================
# FUNÇÕES DE TEMPO E PROGRESSO
# ============================================================

def formatar_tempo(segundos: float) -> str:
    segundos = int(max(0, segundos))

    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segs = segundos % 60

    if horas > 0:
        return f"{horas:02d}h {minutos:02d}m {segs:02d}s"

    if minutos > 0:
        return f"{minutos:02d}m {segs:02d}s"

    return f"{segs:02d}s"


def imprimir_barra_progresso(
    atual: int,
    total: int,
    frases_concluidas: int,
    total_frases: int,
    inicio_execucao: float
) -> None:
    if total <= 0:
        return

    porcentagem = atual / total
    preenchido = int(PROGRESS_BAR_WIDTH * porcentagem)
    vazio = PROGRESS_BAR_WIDTH - preenchido

    barra = "█" * preenchido + "░" * vazio

    tempo_decorrido = time.time() - inicio_execucao

    if atual > 0:
        media_por_lote = tempo_decorrido / atual
        lotes_restantes = total - atual
        eta = media_por_lote * lotes_restantes
    else:
        media_por_lote = 0
        eta = 0

    texto = (
        f"\r[{barra}] "
        f"{porcentagem * 100:6.2f}% | "
        f"Lotes: {atual}/{total} | "
        f"Frases: {frases_concluidas}/{total_frases} | "
        f"Decorrido: {formatar_tempo(tempo_decorrido)} | "
        f"ETA: {formatar_tempo(eta)} | "
        f"Média/lote: {formatar_tempo(media_por_lote)}"
    )

    sys.stdout.write(texto)
    sys.stdout.flush()


# ============================================================
# FUNÇÕES DE ARQUIVO
# ============================================================

def carregar_json(caminho: str) -> dict:
    path = Path(caminho)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def salvar_json(dados: dict, caminho: str) -> None:
    path = Path(caminho)

    with path.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


# ============================================================
# FUNÇÕES DE VALIDAÇÃO
# ============================================================

TOKEN_PATTERN = re.compile(
    r"""
    \[lua\(.*?\)\]              | # funções LUA
    \[/?em\d*\]                 | # [em], [/em], [em1], [/em1]
    <[^<>]+>                    | # tags HTML/XML simples
    \{[^{}]+\}                  | # placeholders {0}, {Item}
    %[sdif]                     | # placeholders %s, %d etc.
    \\n                         | # quebra de linha escapada
    \\r                           # retorno escapado
    """,
    re.VERBOSE
)


def extrair_tokens_tecnicos(texto: str) -> list:
    if not isinstance(texto, str):
        return []

    return TOKEN_PATTERN.findall(texto)


def validar_tokens(en: str, pt_antigo: str, pt_novo: str) -> tuple[bool, list]:
    tokens_esperados = []

    for token in extrair_tokens_tecnicos(en):
        if token not in tokens_esperados:
            tokens_esperados.append(token)

    for token in extrair_tokens_tecnicos(pt_antigo):
        if token not in tokens_esperados:
            tokens_esperados.append(token)

    ausentes = []

    for token in tokens_esperados:
        if token not in pt_novo:
            ausentes.append(token)

    return len(ausentes) == 0, ausentes


def validar_termos_protegidos(en: str, pt_antigo: str, pt_novo: str) -> tuple[bool, list]:
    problemas = []

    for termo_en, termo_pt in PROTECTED_EN_TO_PT_TERMS.items():
        if termo_en in en and termo_pt not in pt_novo:
            problemas.append({
                "tipo": "termo_ingles_exige_termo_pt",
                "termo_en": termo_en,
                "termo_pt_obrigatorio": termo_pt
            })

    for termo_pt in PROTECTED_PT_TERMS:
        if termo_pt in pt_antigo and termo_pt not in pt_novo:
            problemas.append({
                "tipo": "termo_pt_protegido_removido_ou_alterado",
                "termo_pt": termo_pt
            })

    return len(problemas) == 0, problemas


def validar_nomes_personagens(pt_antigo: str, pt_novo: str) -> tuple[bool, list]:
    problemas = []

    for nome in PROTECTED_CHARACTER_NAMES:
        if nome in pt_antigo and nome not in pt_novo:
            problemas.append({
                "tipo": "nome_personagem_removido_ou_alterado",
                "nome": nome
            })

    return len(problemas) == 0, problemas


def extrair_generos_primeira_pessoa(texto: str) -> dict:
    if not isinstance(texto, str):
        return {"masculino": set(), "feminino": set()}

    masculino = set()
    feminino = set()

    pares = [
        ("obrigado", "obrigada"),
        ("direto", "direta"),
        ("pronto", "pronta"),
        ("sozinho", "sozinha"),
        ("cansado", "cansada"),
        ("perdido", "perdida"),
        ("animado", "animada"),
        ("ocupado", "ocupada"),
        ("preocupado", "preocupada"),
        ("felizardo", "felizarda"),
        ("confuso", "confusa"),
        ("assustado", "assustada"),
        ("desculpado", "desculpada"),
        ("digno", "digna"),
    ]

    texto_lower = texto.lower()

    for masc, fem in pares:
        if re.search(rf"\b{re.escape(masc)}\b", texto_lower):
            masculino.add(masc)

        if re.search(rf"\b{re.escape(fem)}\b", texto_lower):
            feminino.add(fem)

    return {
        "masculino": masculino,
        "feminino": feminino
    }


def validar_troca_genero_primeira_pessoa(pt_antigo: str, pt_novo: str) -> tuple[bool, list]:
    antigo = extrair_generos_primeira_pessoa(pt_antigo)
    novo = extrair_generos_primeira_pessoa(pt_novo)

    problemas = []

    if antigo["masculino"] and novo["feminino"]:
        problemas.append({
            "tipo": "masculino_antigo_virou_feminino",
            "marcadores_antigos": sorted(antigo["masculino"]),
            "marcadores_novos": sorted(novo["feminino"])
        })

    if antigo["feminino"] and novo["masculino"]:
        problemas.append({
            "tipo": "feminino_antigo_virou_masculino",
            "marcadores_antigos": sorted(antigo["feminino"]),
            "marcadores_novos": sorted(novo["masculino"])
        })

    return len(problemas) == 0, problemas


def normalizar_chave_para_comparacao(chave: str) -> str:
    """
    Normaliza apenas para comparação interna.
    Não altera a chave original salva no resultado.
    Serve para reparar diferenças como:
    - NBSP real
    - \\u00a0 literal
    - \\\\u00a0 duplamente escapado
    - \\r / \\n literais
    """
    if not isinstance(chave, str):
        return chave

    chave = chave.replace("\\\\u00a0", "\u00a0")
    chave = chave.replace("\\u00a0", "\u00a0")
    chave = chave.replace("\u00a0", " ")

    chave = chave.replace("\\\\r", "\r")
    chave = chave.replace("\\r", "\r")

    chave = chave.replace("\\\\n", "\n")
    chave = chave.replace("\\n", "\n")

    return chave


def reparar_chaves_por_normalizacao(lote: dict, resposta: dict) -> tuple[dict, list]:
    """
    Repara chaves que a IA devolveu visualmente iguais,
    mas com diferença de escape/caractere invisível.
    Mantém a chave original do lote no resultado final.
    """
    resposta_reparada = dict(resposta)
    reparos = []

    chaves_lote = list(lote.keys())
    chaves_resposta = list(resposta_reparada.keys())

    faltando = [k for k in chaves_lote if k not in resposta_reparada]
    sobrando = [k for k in chaves_resposta if k not in lote]

    if not faltando or not sobrando:
        return resposta_reparada, reparos

    mapa_sobrando_normalizado = {}

    for chave_sobrando in sobrando:
        chave_norm = normalizar_chave_para_comparacao(chave_sobrando)
        mapa_sobrando_normalizado.setdefault(chave_norm, []).append(chave_sobrando)

    for chave_faltando in list(faltando):
        chave_faltando_norm = normalizar_chave_para_comparacao(chave_faltando)

        candidatas = mapa_sobrando_normalizado.get(chave_faltando_norm, [])

        if len(candidatas) == 1:
            chave_errada = candidatas[0]
            resposta_reparada[chave_faltando] = resposta_reparada.pop(chave_errada)

            reparos.append({
                "tipo": "chave_reparada_por_normalizacao",
                "chave_original_restaurada": chave_faltando,
                "chave_errada_recebida": chave_errada
            })

    return resposta_reparada, reparos


def extrair_json_da_resposta(texto: str) -> dict:
    texto = texto.strip()

    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass

    inicio = texto.find("{")
    fim = texto.rfind("}")

    if inicio == -1 or fim == -1 or fim <= inicio:
        raise ValueError("Resposta não contém JSON objeto válido.")

    trecho_json = texto[inicio:fim + 1]

    return json.loads(trecho_json)


def validar_resposta_lote(lote: dict, resposta: dict) -> tuple[bool, str, dict, list]:
    resposta_reparada, reparos = reparar_chaves_por_normalizacao(lote, resposta)

    chaves_lote = list(lote.keys())
    chaves_resposta = list(resposta_reparada.keys())

    if set(chaves_lote) != set(chaves_resposta):
        faltando = [k for k in chaves_lote if k not in resposta_reparada]
        sobrando = [k for k in chaves_resposta if k not in lote]

        return False, (
            "As chaves retornadas não batem com as chaves enviadas.\n"
            f"Faltando: {len(faltando)}\n"
            f"Sobrando: {len(sobrando)}\n\n"
            f"Chaves faltando:\n{json.dumps(faltando, ensure_ascii=False, indent=2)}\n\n"
            f"Chaves sobrando:\n{json.dumps(sobrando, ensure_ascii=False, indent=2)}"
        ), resposta_reparada, reparos

    for chave, valor in resposta_reparada.items():
        if not isinstance(valor, str):
            return False, f"Valor retornado não é string para a chave: {chave}", resposta_reparada, reparos

    return True, "", resposta_reparada, reparos


# ============================================================
# API
# ============================================================

def corrigir_lote_com_openai(lote: dict) -> dict:
    entrada = json.dumps(lote, ensure_ascii=False, indent=2)

    user_prompt = f"""
Revise conservadoramente as traduções PT-BR abaixo.

IMPORTANTE:
- Retorne somente JSON válido.
- Mantenha exatamente as mesmas chaves em inglês.
- As chaves em inglês devem voltar exatamente iguais às recebidas.
- Não normalize espaços, apóstrofos, aspas, \\r, \\n ou caracteres invisíveis nas chaves.
- Não altere nenhuma chave em inglês, nem por correção gramatical.
- Corrija apenas os valores em PT-BR.
- Corrija somente quando houver erro real de sentido, literalidade problemática, incoerência, artigo, preposição, tempo verbal, concordância ou glossário.
- Se a tradução atual já estiver natural e correta, mantenha exatamente igual.
- Não faça alteração por preferência estilística.
- Não remova informação, sujeito, objeto, pronome ou nuance importante.
- Não deixe a frase mais vaga.
- Preserve tags, placeholders, LUA, escapes e quebras de linha.
- Preserve nomes/títulos estabelecidos exatamente.
- Não altere nomes próprios de personagens.
- Se um nome já aparece na tradução atual, preserve exatamente esse nome.
- Não troque "Diane" por "Diana", nem qualquer outro nome estabelecido.
- Não mude gênero de nomes/títulos padronizados apenas por causa de pronomes no inglês.
- White Cat God deve continuar Deus Gato Branco.
- Black Cat God deve continuar Deus Gato Preto.
- Não altere gênero de primeira pessoa sem contexto explícito.
- Se for possível neutralizar gênero naturalmente sem perder sentido, pode neutralizar.
- Se a neutralização perder nuance, sentido ou tom, mantenha o gênero atual.
- Cuidado para não piorar frases naturais removendo artigos de nomes próprios.
- Evite ordem de palavras artificial, como "Que tipo de pessoa Roy era?".
- Não reinterpretar verbos ambíguos no chute, como "have", "get", "take", "make it" e "do".
- Se a tradução atual for uma interpretação possível e não houver contexto suficiente, mantenha.
- Não invente gênero para "them", "it" ou "did".
- Não transforme objeto omitido em "trazê-los", "levá-los", "eles o fizeram" etc. sem referente explícito.
- Se a omissão do objeto já estiver natural em PT-BR, mantenha.

JSON para revisar:
{entrada}
"""

    resposta = client.responses.create(
        model=OPENAI_MODEL,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        max_output_tokens=16000
    )

    texto = resposta.output_text

    if not texto or not texto.strip():
        raise ValueError("A API retornou texto vazio.")

    return extrair_json_da_resposta(texto)


def corrigir_lote_com_retry(lote: dict) -> dict:
    ultimo_erro = None

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            resposta = corrigir_lote_com_openai(lote)

            valido, motivo, resposta_reparada, reparos = validar_resposta_lote(lote, resposta)

            if reparos:
                print()
                print("  Aviso: chaves reparadas automaticamente:")
                print(json.dumps(reparos, ensure_ascii=False, indent=2))

            if not valido:
                raise ValueError(motivo)

            return resposta_reparada

        except Exception as erro:
            ultimo_erro = erro

            print()
            print(f"  Erro na tentativa {tentativa}/{MAX_RETRIES}: {erro}")

            if tentativa < MAX_RETRIES:
                tempo_espera = 2 * tentativa
                print(f"  Aguardando {tempo_espera}s antes de tentar novamente...")
                time.sleep(tempo_espera)

    raise RuntimeError(f"Lote falhou após {MAX_RETRIES} tentativas. Último erro: {ultimo_erro}")


# ============================================================
# PROCESSAMENTO
# ============================================================

def dividir_em_lotes(dados: dict, tamanho: int):
    itens = list(dados.items())

    for i in range(0, len(itens), tamanho):
        yield dict(itens[i:i + tamanho])


def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "COLE_SUA_CHAVE_AQUI":
        raise RuntimeError(
            "Configure sua chave em config_api.py ou cole em OPENAI_API_KEY."
        )

    inicio_execucao = time.time()

    print("Carregando JSON de entrada...")
    entrada_completa = carregar_json(INPUT_PATH)

    if not entrada_completa:
        raise RuntimeError(f"Nenhuma entrada encontrada em: {INPUT_PATH}")

    if LIMIT is not None:
        entrada_itens = list(entrada_completa.items())[:LIMIT]
        entrada = dict(entrada_itens)
        print(f"Modo teste ativo: processando apenas {LIMIT} frases.")
    else:
        entrada = entrada_completa
        print("Modo completo ativo: processando todas as frases.")

    print(f"Total de frases na entrada: {len(entrada)}")

    corrigidas = carregar_json(CHECKPOINT_PATH)
    antes_depois = carregar_json(BEFORE_AFTER_REPORT_PATH)
    erros = carregar_json(ERRORS_PATH)

    if corrigidas:
        print(f"Checkpoint encontrado: {len(corrigidas)} frases já corrigidas.")
    else:
        print("Nenhum checkpoint encontrado. Começando do zero.")

    pendentes = {
        chave: valor
        for chave, valor in entrada.items()
        if chave not in corrigidas
    }

    print(f"Frases pendentes: {len(pendentes)}")

    if not pendentes:
        print("Nada pendente. Tudo já foi processado pelo checkpoint.")
        return

    lotes = list(dividir_em_lotes(pendentes, BATCH_SIZE))

    print(f"Total de lotes pendentes: {len(lotes)}")
    print(f"Tamanho dos lotes: {BATCH_SIZE}")
    print()

    total_alteradas = 0
    total_inalteradas = 0
    total_com_tokens_rejeitados = 0
    total_com_termos_protegidos_rejeitados = 0
    total_com_nomes_rejeitados = 0
    total_com_genero_rejeitado = 0
    total_lotes_processados = 0

    frases_concluidas = len(entrada) - len(pendentes)

    imprimir_barra_progresso(
        atual=0,
        total=len(lotes),
        frases_concluidas=frases_concluidas,
        total_frases=len(entrada),
        inicio_execucao=inicio_execucao
    )

    for indice, lote in enumerate(lotes, start=1):
        try:
            resposta_lote = corrigir_lote_com_retry(lote)

            for en, pt_novo in resposta_lote.items():
                pt_antigo = lote[en]

                tokens_ok, tokens_ausentes = validar_tokens(en, pt_antigo, pt_novo)

                if not tokens_ok:
                    erros[en] = {
                        "erro": "tokens_ausentes",
                        "tokens_ausentes": tokens_ausentes,
                        "pt_antigo": pt_antigo,
                        "pt_sugerido": pt_novo
                    }

                    corrigidas[en] = pt_antigo
                    total_com_tokens_rejeitados += 1
                    continue

                termos_ok, problemas_termos = validar_termos_protegidos(en, pt_antigo, pt_novo)

                if not termos_ok:
                    erros[en] = {
                        "erro": "termo_protegido_alterado",
                        "problemas": problemas_termos,
                        "pt_antigo": pt_antigo,
                        "pt_sugerido": pt_novo
                    }

                    corrigidas[en] = pt_antigo
                    total_com_termos_protegidos_rejeitados += 1
                    continue

                nomes_ok, problemas_nomes = validar_nomes_personagens(pt_antigo, pt_novo)

                if not nomes_ok:
                    erros[en] = {
                        "erro": "nome_personagem_alterado",
                        "problemas": problemas_nomes,
                        "pt_antigo": pt_antigo,
                        "pt_sugerido": pt_novo
                    }

                    corrigidas[en] = pt_antigo
                    total_com_nomes_rejeitados += 1
                    continue

                genero_ok, problemas_genero = validar_troca_genero_primeira_pessoa(pt_antigo, pt_novo)

                if not genero_ok:
                    erros[en] = {
                        "erro": "genero_primeira_pessoa_alterado_sem_contexto",
                        "problemas": problemas_genero,
                        "pt_antigo": pt_antigo,
                        "pt_sugerido": pt_novo
                    }

                    corrigidas[en] = pt_antigo
                    total_com_genero_rejeitado += 1
                    continue

                corrigidas[en] = pt_novo

                if pt_novo != pt_antigo:
                    total_alteradas += 1
                    antes_depois[en] = {
                        "antes": pt_antigo,
                        "depois": pt_novo
                    }
                else:
                    total_inalteradas += 1

            frases_concluidas += len(lote)
            total_lotes_processados += 1

            salvar_json(corrigidas, CHECKPOINT_PATH)
            salvar_json(corrigidas, OUTPUT_PATH)
            salvar_json(erros, ERRORS_PATH)
            salvar_json(antes_depois, BEFORE_AFTER_REPORT_PATH)

        except Exception as erro:
            print()
            print(f"Lote {indice} falhou completamente: {erro}")

            chave_lote = f"lote_{indice}"
            erros[chave_lote] = {
                "erro": str(erro),
                "frases": lote
            }

            salvar_json(erros, ERRORS_PATH)
            total_lotes_processados += 1

        imprimir_barra_progresso(
            atual=indice,
            total=len(lotes),
            frases_concluidas=frases_concluidas,
            total_frases=len(entrada),
            inicio_execucao=inicio_execucao
        )

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print()
    print()

    tempo_total = time.time() - inicio_execucao

    relatorio = {
        "arquivo_entrada": INPUT_PATH,
        "arquivo_saida": OUTPUT_PATH,
        "arquivo_checkpoint": CHECKPOINT_PATH,
        "arquivo_erros": ERRORS_PATH,
        "arquivo_antes_depois": BEFORE_AFTER_REPORT_PATH,
        "modelo": OPENAI_MODEL,
        "batch_size": BATCH_SIZE,
        "limit": LIMIT,
        "total_entrada_processada": len(entrada),
        "total_corrigidas_salvas": len(corrigidas),
        "total_alteradas_nesta_execucao": total_alteradas,
        "total_inalteradas_nesta_execucao": total_inalteradas,
        "total_com_tokens_rejeitados_nesta_execucao": total_com_tokens_rejeitados,
        "total_com_termos_protegidos_rejeitados_nesta_execucao": total_com_termos_protegidos_rejeitados,
        "total_com_nomes_rejeitados_nesta_execucao": total_com_nomes_rejeitados,
        "total_com_genero_primeira_pessoa_rejeitado_nesta_execucao": total_com_genero_rejeitado,
        "total_erros_registrados": len(erros),
        "total_antes_depois_registrado": len(antes_depois),
        "total_lotes_processados_nesta_execucao": total_lotes_processados,
        "tempo_total_segundos": round(tempo_total, 2),
        "tempo_total_formatado": formatar_tempo(tempo_total)
    }

    salvar_json(relatorio, REPORT_PATH)

    print("Concluído.")
    print(f"Arquivo final: {OUTPUT_PATH}")
    print(f"Checkpoint: {CHECKPOINT_PATH}")
    print(f"Erros: {ERRORS_PATH}")
    print(f"Relatório: {REPORT_PATH}")
    print(f"Antes/depois: {BEFORE_AFTER_REPORT_PATH}")
    print()
    print("Resumo:")
    print(f"- Total na entrada processada: {len(entrada)}")
    print(f"- Total salvo no resultado: {len(corrigidas)}")
    print(f"- Alteradas nesta execução: {total_alteradas}")
    print(f"- Inalteradas nesta execução: {total_inalteradas}")
    print(f"- Rejeitadas por token ausente: {total_com_tokens_rejeitados}")
    print(f"- Rejeitadas por termo protegido alterado: {total_com_termos_protegidos_rejeitados}")
    print(f"- Rejeitadas por nome de personagem alterado: {total_com_nomes_rejeitados}")
    print(f"- Rejeitadas por troca indevida de gênero em primeira pessoa: {total_com_genero_rejeitado}")
    print(f"- Antes/depois registrados: {len(antes_depois)}")
    print(f"- Erros registrados: {len(erros)}")
    print(f"- Tempo total: {formatar_tempo(tempo_total)}")


if __name__ == "__main__":
    main()