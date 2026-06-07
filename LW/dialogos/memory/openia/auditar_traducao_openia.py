import json
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

INPUT_PATH = "relatorio_antes_depois_corrigidas.json"

OUTPUT_APROVADAS_REPLACE_PATH = "alteracoes_aprovadas_para_replace.json"
OUTPUT_REPROVADAS_ANTES_DEPOIS_PATH = "alteracoes_reprovadas_com_sugestao.json"

CHECKPOINT_PATH = "checkpoint_auditoria_antes_depois.json"
ERRORS_PATH = "erros_auditoria_antes_depois.json"
REPORT_PATH = "relatorio_resumo_auditoria.json"

# Auditoria manda inglês + antes + depois, então lote menor é mais seguro.
BATCH_SIZE = 25

# LIMIT = 100 para teste.
# LIMIT = None para auditar tudo.
LIMIT = None

SLEEP_BETWEEN_REQUESTS = 0.5
MAX_RETRIES = 3
PROGRESS_BAR_WIDTH = 30


# ============================================================
# CLIENTE
# ============================================================

client = OpenAI(api_key=OPENAI_API_KEY)


# ============================================================
# PROMPT DE AUDITORIA
# ============================================================

SYSTEM_PROMPT = """
Você é um auditor profissional de localização PT-BR de jogos.

Você NÃO está traduzindo tudo do zero.
Você está auditando alterações feitas por outra IA na localização PT-BR de Little Witch in the Woods.

Sua tarefa:
- Receber o texto original em inglês, a tradução antiga em PT-BR e a tradução nova em PT-BR.
- Comparar cuidadosamente inglês, antes e depois.
- Decidir se a tradução nova deve ser APROVADA ou REPROVADA.
- Se reprovar, sugerir uma versão melhor e segura em PT-BR.
- Ser extremamente conservador.
- Na dúvida, REPROVE.

DECISÕES:
Use exatamente uma destas decisões:

1. APROVAR
Use quando a tradução nova é claramente melhor que a antiga e não quebra nenhuma regra.

2. REPROVAR
Use quando a tradução nova quebrou alguma regra, piorou a frase, inventou contexto, mudou sentido, removeu informação, formalizou demais, ou quando não há certeza suficiente.

REGRAS PARA APROVAR:
Aprove somente se a tradução nova:
- Corrige erro claro de sentido.
- Corrige literalidade ruim.
- Corrige concordância, regência, artigo, preposição ou tempo verbal claramente errado.
- Melhora naturalidade sem mudar sentido.
- Preserva tom, informação, tags, nomes, lore e referentes.
- Não inventa contexto.
- Não inventa gênero.
- Não deixa a frase mais vaga.
- Não altera nome próprio estabelecido.
- Não altera termo de lore sem prova clara.

REGRAS PARA REPROVAR:
Reprove se a tradução nova:
- Muda o sentido do inglês.
- Remove informação importante.
- Deixa a frase mais vaga.
- Reinterpreta uma frase ambígua sem contexto.
- Inventa gênero sem contexto.
- Inventa referente para "them", "it", "did", "have", "make it", "get", "take".
- Transforma "them" em "levá-los", "trazê-los", "eles", "elas", "os", "as" sem referente claro.
- Traduz "did" como "o fez", "o fizeram", "morreu" ou "morreram" sem contexto explícito.
- Muda nome próprio estabelecido.
- Muda "Diane" para "Diana" ou qualquer nome de personagem já estabelecido.
- Altera termo de lore sem prova clara.
- Troca "moedas" por "pies" quando pies é moeda.
- Troca "Deus Gato Branco" por "Deusa Gata Branca".
- Troca "Deus Gato Preto" por "Deusa Gata Preta".
- Remove pronomes/referentes importantes como "ela", "ele", "isso", "juntas", "delas".
- Formaliza demais o diálogo.
- Troca PT-BR natural por norma culta artificial.
- Troca "Vi ele" por "O vi" apenas por formalidade.
- Usa "jamais", "o fiz", "o fizeram", "habitual", "a que", "de que" quando o tom fica formal demais.
- Reposiciona tags, símbolos ou placeholders de forma que mudem função sintática.
- Quebra tags, placeholders, LUA, escapes, \\n ou \\r.
- Altera infinitivo para gerúndio em texto curto de UI sem contexto.
- Altera singular/plural de termo de lore sem confirmação.
- Troca "knowledge of the star" para singular/plural no chute. Se não houver certeza, preserve a tradução antiga.

REGRAS PARA SUGESTÃO QUANDO REPROVAR:
- Ao reprovar, forneça uma sugestão em "sugestao".
- A sugestão deve ser melhor que o "depois" reprovado.
- Se o "antes" já for a opção mais segura, use o próprio "antes" como sugestão.
- Não invente contexto.
- Não invente gênero.
- Não altere nomes próprios.
- Não remova informação.
- Não formalize demais.
- Preserve tags, placeholders, LUA, escapes, \\n e \\r.

NOMES DE PERSONAGENS:
- Nunca altere nomes próprios de personagens já presentes na tradução antiga.
- Não corrija nomes de personagens com base apenas no inglês.
- Se a tradução antiga usa "Diane", mantenha "Diane", mesmo que o inglês diga "Diana".
- Se a tradução antiga usa "Roy", "Ellie", "Kyla", "Aurea", "Enite", "Arden", "Rubrum", "Clala", "Vinch", "Lisa", "Kate", "Alvin", "Virgil", mantenha exatamente igual.
- Só altere nome próprio se houver regra explícita no glossário dizendo para alterar.

GÊNERO:
- O inglês muitas vezes não marca gênero.
- Não altere gênero sem contexto explícito.
- Se não for possível identificar com segurança, use formulação neutra apenas se preservar sentido, tom e informação.
- Se neutralizar deixar a frase vaga ou fraca, mantenha a tradução antiga.

VERBOS E REFERENTES AMBÍGUOS:
- Não troque verbos ambíguos como "have", "get", "take", "make it", "bring", "carry", "go", "do" sem contexto claro.
- Se a tradução antiga escolhe uma interpretação possível e não está claramente errada, mantenha.
- Não troque "Thank you for making it" para "Obrigado por ter vindo" sem contexto claro de chegada/presença.
- Não transforme automaticamente "them" em "eles", "elas", "os", "as", "trazê-los", "levá-los" etc. quando o referente não estiver claro.
- Em PT-BR, muitas vezes é mais natural e seguro omitir o objeto quando ele já está implícito pelo contexto.
- Se a tradução antiga omite o objeto de forma natural, não adicione pronome de gênero sem contexto explícito.
- Não traduza "did" literalmente como "o fez", "o fizeram", "morreu" ou "morreram" sem contexto explícito.

TOM EM DIÁLOGO PT-BR:
- Priorize PT-BR natural de diálogo.
- Não transforme diálogo natural em norma culta artificial.
- Não troque palavras comuns por termos formais sem necessidade.
- Não troque tom casual por formal sem motivo.

LORE E GLOSSÁRIO:
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
- Diane = Diane. Não trocar para Diana.
- pies, quando usado como moeda = moedas. Nunca deixar "pies" em inglês.

PRESERVAÇÃO TÉCNICA:
- Preserve tags e placeholders exatamente:
  [em], [em1], [em2], [/em], [/em1], [/em2],
  <shake>, </shake>, <wave>, </wave>,
  <color=#...>, </color>,
  {0}, {1}, %s, \\n, \\r,
  [lua(GetLocalizedString(...))],
  [lua(GetItemName(...))]
- Nunca apague, quebre ou traduza funções LUA.
- Nunca remova escapes.
- Nunca remova quebras de linha representadas como \\n ou \\r.

FORMATO DE SAÍDA:
Retorne somente JSON válido.
Não escreva comentários fora do JSON.
Use exatamente os mesmos IDs recebidos.

Para cada ID, retorne:
{
  "decisao": "APROVAR" | "REPROVAR",
  "sugestao": "texto final sugerido em PT-BR",
  "motivo": "motivo curto"
}

Regras:
- Se APROVAR: "sugestao" deve ser igual ao "depois".
- Se REPROVAR: "sugestao" deve ser uma versão segura. Se não houver melhoria óbvia, use o "antes".
"""


# ============================================================
# FUNÇÕES UTILITÁRIAS
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


def imprimir_barra_progresso(atual, total, itens_concluidos, total_itens, inicio_execucao):
    if total <= 0:
        return

    porcentagem = atual / total
    preenchido = int(PROGRESS_BAR_WIDTH * porcentagem)
    vazio = PROGRESS_BAR_WIDTH - preenchido
    barra = "█" * preenchido + "░" * vazio

    tempo_decorrido = time.time() - inicio_execucao

    if atual > 0:
        media_por_lote = tempo_decorrido / atual
        eta = media_por_lote * (total - atual)
    else:
        media_por_lote = 0
        eta = 0

    texto = (
        f"\r[{barra}] "
        f"{porcentagem * 100:6.2f}% | "
        f"Lotes: {atual}/{total} | "
        f"Itens: {itens_concluidos}/{total_itens} | "
        f"Decorrido: {formatar_tempo(tempo_decorrido)} | "
        f"ETA: {formatar_tempo(eta)} | "
        f"Média/lote: {formatar_tempo(media_por_lote)}"
    )

    sys.stdout.write(texto)
    sys.stdout.flush()


def carregar_json(caminho: str) -> dict:
    path = Path(caminho)
    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def salvar_json(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def dividir_em_lotes(dados: dict, tamanho: int):
    itens = list(dados.items())
    for i in range(0, len(itens), tamanho):
        yield dict(itens[i:i + tamanho])


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

    return json.loads(texto[inicio:fim + 1])


# ============================================================
# PREPARAÇÃO DO LOTE
# ============================================================

def preparar_lote_com_ids(lote: dict) -> tuple[dict, dict]:
    """
    Envia IDs para a IA não ter que devolver a chave em inglês.
    Os arquivos finais continuam usando as chaves originais.
    """

    lote_com_ids = {}
    mapa_id_para_chave = {}

    for indice, (en, dados) in enumerate(lote.items()):
        id_item = str(indice)

        antes = dados.get("antes", "")
        depois = dados.get("depois", "")

        lote_com_ids[id_item] = {
            "en": en,
            "antes": antes,
            "depois": depois
        }

        mapa_id_para_chave[id_item] = en

    return lote_com_ids, mapa_id_para_chave


def validar_resposta_auditoria(lote_com_ids: dict, resposta: dict) -> tuple[bool, str]:
    ids_esperados = set(lote_com_ids.keys())
    ids_recebidos = set(resposta.keys())

    if ids_esperados != ids_recebidos:
        faltando = sorted(ids_esperados - ids_recebidos, key=lambda x: int(x) if x.isdigit() else x)
        sobrando = sorted(ids_recebidos - ids_esperados)

        return False, (
            "IDs retornados não batem com IDs enviados.\n"
            f"Faltando: {faltando}\n"
            f"Sobrando: {sobrando}"
        )

    decisoes_validas = {"APROVAR", "REPROVAR"}

    for id_item, obj in resposta.items():
        if not isinstance(obj, dict):
            return False, f"Item {id_item} não retornou objeto."

        decisao = obj.get("decisao")
        sugestao = obj.get("sugestao")
        motivo = obj.get("motivo")

        if decisao not in decisoes_validas:
            return False, f"Item {id_item} tem decisão inválida: {decisao}"

        if not isinstance(sugestao, str):
            return False, f"Item {id_item} tem sugestao inválida."

        if not isinstance(motivo, str):
            return False, f"Item {id_item} tem motivo inválido."

    return True, ""


# ============================================================
# API
# ============================================================

def auditar_lote_com_openai(lote: dict) -> dict:
    lote_com_ids, mapa_id_para_chave = preparar_lote_com_ids(lote)

    entrada = json.dumps(lote_com_ids, ensure_ascii=False, indent=2)

    user_prompt = f"""
Audite as alterações de localização abaixo.

Para cada item:
- Compare "en", "antes" e "depois".
- Aprove somente se "depois" for claramente melhor e não quebrar nenhuma regra.
- Reprove se "depois" mudou sentido, inventou contexto, inventou gênero, removeu referente, formalizou demais, alterou nome/lore/moeda, ou piorou a frase.
- Se reprovar, forneça uma sugestão segura em "sugestao".
- Se o "antes" já for a opção mais segura, use o próprio "antes" como sugestão.
- Retorne somente JSON válido com os mesmos IDs.

Itens:
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

    resposta_por_id = extrair_json_da_resposta(texto)

    valido, motivo = validar_resposta_auditoria(lote_com_ids, resposta_por_id)

    if not valido:
        raise ValueError(motivo)

    resultado = {}

    for id_item, obj in resposta_por_id.items():
        en_original = mapa_id_para_chave[id_item]

        antes = lote[en_original].get("antes", "")
        depois = lote[en_original].get("depois", "")

        decisao = obj["decisao"]
        sugestao = obj["sugestao"]
        motivo = obj["motivo"]

        # Segurança:
        # Se aprovar, a sugestão precisa ser exatamente o depois.
        # Se a IA tentar mudar algo ao aprovar, força o depois original.
        if decisao == "APROVAR":
            sugestao = depois

        # Se reprovar e vier sugestão vazia, usa o antes por segurança.
        if decisao == "REPROVAR" and not sugestao.strip():
            sugestao = antes

        resultado[en_original] = {
            "antes": antes,
            "depois_original": depois,
            "decisao": decisao,
            "sugestao": sugestao,
            "motivo": motivo
        }

    return resultado


def auditar_lote_com_retry(lote: dict) -> dict:
    ultimo_erro = None

    for tentativa in range(1, MAX_RETRIES + 1):
        try:
            return auditar_lote_com_openai(lote)

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
# GERAÇÃO DOS ARQUIVOS FINAIS
# ============================================================

def gerar_arquivos_finais(auditoria: dict):
    aprovadas_para_replace = {}
    reprovadas_antes_depois = {}

    for en, item in auditoria.items():
        decisao = item["decisao"]

        original = item["antes"]
        alteracao_primeiro_script = item["depois_original"]
        sugestao_auditoria = item["sugestao"]

        if decisao == "APROVAR":
            aprovadas_para_replace[en] = alteracao_primeiro_script

        elif decisao == "REPROVAR":
            reprovadas_antes_depois[en] = {
                "original": original,
                "antes": alteracao_primeiro_script,
                "depois": sugestao_auditoria
            }

    salvar_json(aprovadas_para_replace, OUTPUT_APROVADAS_REPLACE_PATH)
    salvar_json(reprovadas_antes_depois, OUTPUT_REPROVADAS_ANTES_DEPOIS_PATH)

    return aprovadas_para_replace, reprovadas_antes_depois


# ============================================================
# MAIN
# ============================================================

def main():
    if not OPENAI_API_KEY or OPENAI_API_KEY == "COLE_SUA_CHAVE_AQUI":
        raise RuntimeError("Configure sua chave em config_api.py ou em OPENAI_API_KEY.")

    inicio_execucao = time.time()

    print("Carregando relatório antes/depois...")
    entrada_completa = carregar_json(INPUT_PATH)

    if not entrada_completa:
        raise RuntimeError(f"Nenhuma entrada encontrada em: {INPUT_PATH}")

    if LIMIT is not None:
        entrada_itens = list(entrada_completa.items())[:LIMIT]
        entrada = dict(entrada_itens)
        print(f"Modo teste ativo: auditando apenas {LIMIT} alterações.")
    else:
        entrada = entrada_completa
        print("Modo completo ativo: auditando todas as alterações.")

    print(f"Total de alterações na entrada: {len(entrada)}")

    auditoria = carregar_json(CHECKPOINT_PATH)
    erros = carregar_json(ERRORS_PATH)

    if auditoria:
        print(f"Checkpoint encontrado: {len(auditoria)} alterações já auditadas.")
    else:
        print("Nenhum checkpoint encontrado. Começando do zero.")

    pendentes = {
        chave: valor
        for chave, valor in entrada.items()
        if chave not in auditoria
    }

    print(f"Alterações pendentes: {len(pendentes)}")

    if not pendentes:
        print("Nada pendente. Gerando arquivos finais com o checkpoint existente...")

        aprovadas, reprovadas = gerar_arquivos_finais(auditoria)

        print()
        print("Resumo:")
        print(f"- Auditoria total: {len(auditoria)}")
        print(f"- Aprovadas para replace: {len(aprovadas)}")
        print(f"- Reprovadas com sugestão: {len(reprovadas)}")
        return

    lotes = list(dividir_em_lotes(pendentes, BATCH_SIZE))

    print(f"Total de lotes pendentes: {len(lotes)}")
    print(f"Tamanho dos lotes: {BATCH_SIZE}")
    print()

    total_lotes_processados = 0
    itens_concluidos = len(entrada) - len(pendentes)

    imprimir_barra_progresso(
        atual=0,
        total=len(lotes),
        itens_concluidos=itens_concluidos,
        total_itens=len(entrada),
        inicio_execucao=inicio_execucao
    )

    for indice, lote in enumerate(lotes, start=1):
        try:
            resultado_lote = auditar_lote_com_retry(lote)

            auditoria.update(resultado_lote)
            itens_concluidos += len(lote)
            total_lotes_processados += 1

            # Salva o checkpoint completo da auditoria
            salvar_json(auditoria, CHECKPOINT_PATH)

            # Atualiza os arquivos finais a cada lote,
            # para você conseguir acompanhar enquanto processa.
            gerar_arquivos_finais(auditoria)

        except Exception as erro:
            print()
            print(f"Lote {indice} falhou completamente: {erro}")

            erros[f"lote_{indice}"] = {
                "erro": str(erro),
                "itens": lote
            }

            salvar_json(erros, ERRORS_PATH)

            # Mantém os arquivos finais atualizados mesmo se um lote falhar.
            gerar_arquivos_finais(auditoria)

            total_lotes_processados += 1

        imprimir_barra_progresso(
            atual=indice,
            total=len(lotes),
            itens_concluidos=itens_concluidos,
            total_itens=len(entrada),
            inicio_execucao=inicio_execucao
        )

        time.sleep(SLEEP_BETWEEN_REQUESTS)

    print()
    print()

    # Garante uma última geração completa no final.
    aprovadas, reprovadas = gerar_arquivos_finais(auditoria)

    contagem_decisoes = {
        "APROVAR": 0,
        "REPROVAR": 0
    }

    for item in auditoria.values():
        decisao = item.get("decisao")
        if decisao in contagem_decisoes:
            contagem_decisoes[decisao] += 1

    tempo_total = time.time() - inicio_execucao

    relatorio = {
        "arquivo_entrada": INPUT_PATH,
        "arquivo_aprovadas_replace": OUTPUT_APROVADAS_REPLACE_PATH,
        "arquivo_reprovadas_antes_depois": OUTPUT_REPROVADAS_ANTES_DEPOIS_PATH,
        "arquivo_checkpoint": CHECKPOINT_PATH,
        "arquivo_erros": ERRORS_PATH,
        "modelo": OPENAI_MODEL,
        "batch_size": BATCH_SIZE,
        "limit": LIMIT,
        "total_entrada_processada": len(entrada),
        "total_auditadas_salvas": len(auditoria),
        "total_aprovadas_para_replace": len(aprovadas),
        "total_reprovadas_com_sugestao": len(reprovadas),
        "decisoes": contagem_decisoes,
        "total_erros_registrados": len(erros),
        "total_lotes_processados_nesta_execucao": total_lotes_processados,
        "tempo_total_segundos": round(tempo_total, 2),
        "tempo_total_formatado": formatar_tempo(tempo_total)
    }

    salvar_json(relatorio, REPORT_PATH)

    print("Concluído.")
    print(f"Aprovadas para -replace: {OUTPUT_APROVADAS_REPLACE_PATH}")
    print(f"Reprovadas com sugestão: {OUTPUT_REPROVADAS_ANTES_DEPOIS_PATH}")
    print(f"Checkpoint: {CHECKPOINT_PATH}")
    print(f"Erros: {ERRORS_PATH}")
    print(f"Resumo: {REPORT_PATH}")
    print()
    print("Resumo:")
    print(f"- Total auditado: {len(auditoria)}")
    print(f"- APROVAR: {contagem_decisoes['APROVAR']}")
    print(f"- REPROVAR: {contagem_decisoes['REPROVAR']}")
    print(f"- Aprovadas para -replace: {len(aprovadas)}")
    print(f"- Reprovadas com sugestão: {len(reprovadas)}")
    print(f"- Erros registrados: {len(erros)}")
    print(f"- Tempo total: {formatar_tempo(tempo_total)}")


if __name__ == "__main__":
    main()