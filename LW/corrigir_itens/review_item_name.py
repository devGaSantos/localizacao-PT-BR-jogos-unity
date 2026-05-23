import json
import re
from pathlib import Path


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ARQUIVO_ENTRADA = Path("memoria_revisado.json")
ARQUIVO_SAIDA = Path("memoria_revisado_corrigido.json")
ARQUIVO_RELATORIO = Path("relatorio_ordem_placeholders.json")


# ============================================================
# PADRÕES
# ============================================================

PADRAO_INTERIOR_THEME = re.compile(
    r'\{InteriorPropTheme\.[^{}]+\}'
)

PADRAO_BROOMSTICK_THEME = re.compile(
    r'\{BroomstickTheme\.[^{}]+\}'
)

PADRAO_INTERIOR_PROP = re.compile(
    r'\{InteriorProp(?:Theme|BasicName)\.[^{}]+\}'
)

PADRAO_BROOMSTICK = re.compile(
    r'\{Broomstick(?:Theme|Common)\.[^{}]+\}'
)

# ------------------------------------------------------------
# INTERIORPROP
# ------------------------------------------------------------

PADRAO_FISH_COM_INTERIOR_PROP = re.compile(
    r'\{Fish(?:Name|Grade)\.[^{}]+\}.*\{InteriorPropBasicName\.[^{}]+\}'
)

PADRAO_REFERENCIA_ANTES_INTERIOR_BASIC = re.compile(
    r'^\s*(\{(?:People|CreatureName|PotionName|CandyName)\.[^{}]+\})\s+(\{InteriorPropBasicName\.[^{}]+\})\s*$'
)

PADRAO_INTERIOR_BASIC_DE_REFERENCIA = re.compile(
    r'^\s*(\{InteriorPropBasicName\.[^{}]+\})\s+de\s+(\{(?:People|CreatureName|PotionName|CandyName)\.[^{}]+\})\s*$'
)

PADRAO_TEXTO_ANTES_INTERIOR_BASIC = re.compile(
    r'^\s*(.+?)\s+(\{InteriorPropBasicName\.[^{}]+\})\s*$'
)

# ------------------------------------------------------------
# BROOMSTICK
# ------------------------------------------------------------

# Ex:
# {BroomstickCommon.Broomstick_Type_Balanced} {BroomstickTheme.LuckyLeaf} {BroomstickCommon.Broomstick_Name}
# -> {BroomstickCommon.Broomstick_Name} {BroomstickTheme.LuckyLeaf} {BroomstickCommon.Broomstick_Type_Balanced}
PADRAO_BROOMSTICK_TIPO_THEME_NOME = re.compile(
    r'^\s*(\{BroomstickCommon\.Broomstick_Type_[^{}]+\})\s+'
    r'(\{BroomstickTheme\.[^{}]+\})\s+'
    r'(\{BroomstickCommon\.Broomstick_Name\})\s*$'
)

# Ex já correto:
# {BroomstickCommon.Broomstick_Name} {BroomstickTheme.LuckyLeaf} {BroomstickCommon.Broomstick_Type_Balanced}
PADRAO_BROOMSTICK_NOME_THEME_TIPO = re.compile(
    r'^\s*(\{BroomstickCommon\.Broomstick_Name\})\s+'
    r'(\{BroomstickTheme\.[^{}]+\})\s+'
    r'(\{BroomstickCommon\.Broomstick_Type_[^{}]+\})\s*$'
)

# Ex:
# {BroomstickTheme.Basic} {BroomstickCommon.Broomstick_Name}
# -> {BroomstickCommon.Broomstick_Name} {BroomstickTheme.Basic}
PADRAO_BROOMSTICK_THEME_NOME = re.compile(
    r'^\s*(\{BroomstickTheme\.[^{}]+\})\s+'
    r'(\{BroomstickCommon\.Broomstick_Name\})\s*$'
)

# Ex já correto:
# {BroomstickCommon.Broomstick_Name} {BroomstickTheme.Basic}
PADRAO_BROOMSTICK_NOME_THEME = re.compile(
    r'^\s*(\{BroomstickCommon\.Broomstick_Name\})\s+'
    r'(\{BroomstickTheme\.[^{}]+\})\s*$'
)

# Descrições de vassoura. Detecta, mas não altera automaticamente.
PADRAO_BROOMSTICK_DESCRICAO_COMPOSTA = re.compile(
    r'^\s*(\{BroomstickTheme\.[^{}]+_Description\})\\n'
    r'(\{BroomstickCommon\.Broomstick_Type_[^{}]+_Description\})\s*$'
)

# ------------------------------------------------------------
# EFFECT FOOD
# ------------------------------------------------------------

# Qualidades de comida que funcionam como adjetivo em inglês:
# {EffectFoodCommon.Food_Perfect} Green Tea
# {EffectFoodCommon.Food_Delicious} Meat Kebab
# {EffectFoodCommon.Food_Normal} Black Tea
PADRAO_EFFECT_FOOD_QUALIDADE = re.compile(
    r'\{EffectFoodCommon\.Food_(?:Perfect|Delicious|Normal)\}'
)

# Caso invertido:
# {EffectFoodCommon.Food_Perfect} Green Tea
# -> Green Tea {EffectFoodCommon.Food_Perfect}
#
# {EffectFoodCommon.Food_Delicious} {EffectFoodCommon.BeefBread_Name}
# -> {EffectFoodCommon.BeefBread_Name} {EffectFoodCommon.Food_Delicious}
PADRAO_EFFECT_FOOD_QUALIDADE_ANTES_NOME = re.compile(
    r'^\s*(\{EffectFoodCommon\.Food_(?:Perfect|Delicious|Normal)\})\s+(.+?)\s*$'
)

# Caso já correto:
# Green Tea {EffectFoodCommon.Food_Perfect}
# {EffectFoodCommon.BeefBread_Name} {EffectFoodCommon.Food_Delicious}
PADRAO_EFFECT_FOOD_NOME_ANTES_QUALIDADE = re.compile(
    r'^\s*(.+?)\s+(\{EffectFoodCommon\.Food_(?:Perfect|Delicious|Normal)\})\s*$'
)

# Placeholders de descrição de comida. Não alterar.
PADRAO_EFFECT_FOOD_DESCRIPTION = re.compile(
    r'^\s*\{EffectFoodCommon\.[^{}]*_Description\}\s*$'
)

PADRAO_EFFECT_FOOD_GERAL = re.compile(
    r'\{EffectFoodCommon\.[^{}]+\}'
)


# ============================================================
# FUNÇÕES BÁSICAS
# ============================================================

def carregar_json(caminho: Path):
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho.resolve()}")

    with caminho.open("r", encoding="utf-8") as f:
        return json.load(f)


def salvar_json(caminho: Path, dados):
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def normalizar_espacos(texto: str) -> str:
    return re.sub(r'\s+', ' ', texto).strip()


def tem_fish(texto: str) -> bool:
    return "{FishName." in texto or "{FishGrade." in texto


# ============================================================
# CORREÇÕES EFFECT FOOD
# ============================================================

def corrigir_effect_food_qualidade_antes_nome(valor_strip: str):
    """
    Corrige nomes compostos de comida:

      {EffectFoodCommon.Food_Perfect} Green Tea
      -> Green Tea {EffectFoodCommon.Food_Perfect}

      {EffectFoodCommon.Food_Delicious} Meat Kebab
      -> Meat Kebab {EffectFoodCommon.Food_Delicious}

      {EffectFoodCommon.Food_Normal} {EffectFoodCommon.BeefBread_Name}
      -> {EffectFoodCommon.BeefBread_Name} {EffectFoodCommon.Food_Normal}

    Não altera descrições:
      {EffectFoodCommon.Food_StaminaReduceConsume_Description}
    """

    if PADRAO_EFFECT_FOOD_DESCRIPTION.match(valor_strip):
        return None

    match = PADRAO_EFFECT_FOOD_QUALIDADE_ANTES_NOME.match(valor_strip)
    if not match:
        return None

    qualidade = match.group(1).strip()
    nome = match.group(2).strip()

    if not nome:
        return None

    # Segurança: não mexe se o "nome" for descrição.
    if "_Description}" in nome:
        return None

    # Segurança: se por algum motivo houver quebra de linha, não altera.
    # Isso evita mexer em blocos descritivos compostos.
    if "\n" in valor_strip or "\\n" in valor_strip:
        return None

    return f"{nome} {qualidade}"


# ============================================================
# CORREÇÕES INTERIORPROP
# ============================================================

def corrigir_referencia_antes_interior_basic(valor_strip: str):
    match = PADRAO_REFERENCIA_ANTES_INTERIOR_BASIC.match(valor_strip)
    if not match:
        return None

    referencia = match.group(1)
    basic_name = match.group(2)

    return f"{basic_name} de {referencia}"


def corrigir_interior_theme_no_inicio(valor_strip: str):
    """
    Corrige:

      {InteriorPropTheme.RoyalGreen} {InteriorPropBasicName.Sofa}
      -> {InteriorPropBasicName.Sofa} {InteriorPropTheme.RoyalGreen}

      {InteriorPropTheme.StarryNight} Telescope
      -> Telescope {InteriorPropTheme.StarryNight}

      {InteriorPropTheme.ThanksGiving} Small {InteriorPropBasicName.Storage}
      -> Small {InteriorPropBasicName.Storage} {InteriorPropTheme.ThanksGiving}
    """

    if not valor_strip.startswith("{InteriorPropTheme."):
        return None

    temas = []
    resto = valor_strip

    while True:
        match = PADRAO_INTERIOR_THEME.match(resto)
        if not match:
            break

        temas.append(match.group(0))
        resto = resto[match.end():].strip()

    if not temas or not resto:
        return None

    return normalizar_espacos(f"{resto} {' '.join(temas)}")


def corrigir_texto_antes_interior_basic(valor_strip: str):
    """
    Corrige:

      Mar {InteriorPropBasicName.PictureFrame}
      -> {InteriorPropBasicName.PictureFrame} de Mar

      Garota de Chapéu Azul {InteriorPropBasicName.PictureFrame}
      -> {InteriorPropBasicName.PictureFrame} de Garota de Chapéu Azul
    """

    match = PADRAO_TEXTO_ANTES_INTERIOR_BASIC.match(valor_strip)
    if not match:
        return None

    texto_antes = match.group(1).strip()
    basic_name = match.group(2).strip()

    if not texto_antes:
        return None

    if tem_fish(texto_antes):
        return None

    if texto_antes.startswith("{InteriorPropBasicName."):
        return None

    if texto_antes.startswith("{InteriorPropTheme."):
        return None

    if PADRAO_INTERIOR_BASIC_DE_REFERENCIA.match(valor_strip):
        return None

    return f"{basic_name} de {texto_antes}"


# ============================================================
# CORREÇÕES BROOMSTICK
# ============================================================

def corrigir_broomstick_tipo_theme_nome(valor_strip: str):
    """
    Corrige:

      {BroomstickCommon.Broomstick_Type_Balanced} {BroomstickTheme.LuckyLeaf} {BroomstickCommon.Broomstick_Name}
      -> {BroomstickCommon.Broomstick_Name} {BroomstickTheme.LuckyLeaf} {BroomstickCommon.Broomstick_Type_Balanced}
    """

    match = PADRAO_BROOMSTICK_TIPO_THEME_NOME.match(valor_strip)
    if not match:
        return None

    tipo = match.group(1)
    theme = match.group(2)
    nome = match.group(3)

    return f"{nome} {theme} {tipo}"


def corrigir_broomstick_theme_nome(valor_strip: str):
    """
    Corrige:

      {BroomstickTheme.Basic} {BroomstickCommon.Broomstick_Name}
      -> {BroomstickCommon.Broomstick_Name} {BroomstickTheme.Basic}
    """

    match = PADRAO_BROOMSTICK_THEME_NOME.match(valor_strip)
    if not match:
        return None

    theme = match.group(1)
    nome = match.group(2)

    return f"{nome} {theme}"


def corrigir_broomstick_theme_no_inicio_generico(valor_strip: str):
    """
    Correção genérica para casos de BroomstickTheme no começo que não
    entraram nas regras específicas.

    Ex:
      {BroomstickTheme.X} Alguma Coisa
      -> Alguma Coisa {BroomstickTheme.X}

    Não mexe em descrições.
    """

    if not valor_strip.startswith("{BroomstickTheme."):
        return None

    if "_Description}" in valor_strip:
        return None

    temas = []
    resto = valor_strip

    while True:
        match = PADRAO_BROOMSTICK_THEME.match(resto)
        if not match:
            break

        temas.append(match.group(0))
        resto = resto[match.end():].strip()

    if not temas or not resto:
        return None

    return normalizar_espacos(f"{resto} {' '.join(temas)}")


# ============================================================
# CORREÇÃO PRINCIPAL
# ============================================================

def corrigir_valor(valor):
    """
    Corrige somente valores, nunca chaves.
    """

    if not isinstance(valor, str):
        return valor, False, "valor_nao_string"

    valor_original = valor
    valor_strip = valor.strip()

    if not valor_strip:
        return valor, False, "valor_vazio"

    # ------------------------------------------------------------
    # EFFECT FOOD: descrições isoladas, detectar mas não alterar
    # ------------------------------------------------------------
    if PADRAO_EFFECT_FOOD_DESCRIPTION.match(valor_strip):
        return valor, False, "effectfood_descricao_nao_alterada"

    # ------------------------------------------------------------
    # EFFECT FOOD: já correto
    # ------------------------------------------------------------
    if PADRAO_EFFECT_FOOD_NOME_ANTES_QUALIDADE.match(valor_strip):
        # Só considera "já correto" se a qualidade estiver no final,
        # e o valor não começar com ela.
        if not valor_strip.startswith("{EffectFoodCommon.Food_"):
            return valor, False, "ja_estava_correto_effectfood_nome_qualidade"

    # ------------------------------------------------------------
    # EFFECT FOOD: qualidade + nome
    # ------------------------------------------------------------
    novo_effect_food = corrigir_effect_food_qualidade_antes_nome(valor_strip)
    if novo_effect_food is not None:
        novo_effect_food = normalizar_espacos(novo_effect_food)

        if novo_effect_food != valor_original:
            return novo_effect_food, True, "effectfood_qualidade_movida_para_o_final"

        return valor, False, "sem_mudanca_effectfood"

    # ------------------------------------------------------------
    # BROOMSTICK: descrições compostas, detectar mas não alterar
    # ------------------------------------------------------------
    if PADRAO_BROOMSTICK_DESCRICAO_COMPOSTA.match(valor_strip):
        return valor, False, "broomstick_descricao_composta_nao_alterada"

    # ------------------------------------------------------------
    # BROOMSTICK: já correto
    # ------------------------------------------------------------
    if PADRAO_BROOMSTICK_NOME_THEME_TIPO.match(valor_strip):
        return valor, False, "ja_estava_correto_broomstick_nome_theme_tipo"

    if PADRAO_BROOMSTICK_NOME_THEME.match(valor_strip):
        return valor, False, "ja_estava_correto_broomstick_nome_theme"

    # ------------------------------------------------------------
    # BROOMSTICK: tipo + tema + nome
    # ------------------------------------------------------------
    novo_broom_tipo_theme_nome = corrigir_broomstick_tipo_theme_nome(valor_strip)
    if novo_broom_tipo_theme_nome is not None:
        novo_broom_tipo_theme_nome = normalizar_espacos(novo_broom_tipo_theme_nome)

        if novo_broom_tipo_theme_nome != valor_original:
            return novo_broom_tipo_theme_nome, True, "broomstick_tipo_theme_nome_corrigido_para_nome_theme_tipo"

        return valor, False, "sem_mudanca_broomstick_tipo_theme_nome"

    # ------------------------------------------------------------
    # BROOMSTICK: tema + nome
    # ------------------------------------------------------------
    novo_broom_theme_nome = corrigir_broomstick_theme_nome(valor_strip)
    if novo_broom_theme_nome is not None:
        novo_broom_theme_nome = normalizar_espacos(novo_broom_theme_nome)

        if novo_broom_theme_nome != valor_original:
            return novo_broom_theme_nome, True, "broomstick_theme_nome_corrigido_para_nome_theme"

        return valor, False, "sem_mudanca_broomstick_theme_nome"

    # ------------------------------------------------------------
    # INTERIORPROP: peixes, detectar mas não alterar
    # ------------------------------------------------------------
    if PADRAO_FISH_COM_INTERIOR_PROP.search(valor_strip):
        return valor, False, "fish_com_interiorprop_nao_alterado"

    # ------------------------------------------------------------
    # INTERIORPROP: já corrigido
    # ------------------------------------------------------------
    if PADRAO_INTERIOR_BASIC_DE_REFERENCIA.match(valor_strip):
        return valor, False, "ja_estava_correto_interiorbasic_de_referencia"

    # ------------------------------------------------------------
    # INTERIORPROP: referências específicas antes do item
    # ------------------------------------------------------------
    novo_referencia = corrigir_referencia_antes_interior_basic(valor_strip)
    if novo_referencia is not None:
        novo_referencia = normalizar_espacos(novo_referencia)

        if novo_referencia != valor_original:
            return novo_referencia, True, "referencia_antes_interiorbasic_corrigida_com_de"

        return valor, False, "sem_mudanca_referencia"

    # ------------------------------------------------------------
    # INTERIORPROP: theme no começo
    # ------------------------------------------------------------
    novo_interior_theme = corrigir_interior_theme_no_inicio(valor_strip)
    if novo_interior_theme is not None:
        novo_interior_theme = normalizar_espacos(novo_interior_theme)

        if novo_interior_theme != valor_original:
            return novo_interior_theme, True, "interiorprop_theme_movido_para_o_final"

        return valor, False, "sem_mudanca_interiorprop_theme"

    # ------------------------------------------------------------
    # INTERIORPROP: texto comum antes do item
    # ------------------------------------------------------------
    novo_texto = corrigir_texto_antes_interior_basic(valor_strip)
    if novo_texto is not None:
        novo_texto = normalizar_espacos(novo_texto)

        if novo_texto != valor_original:
            return novo_texto, True, "texto_antes_interiorbasic_corrigido_com_de"

        return valor, False, "sem_mudanca_texto_antes_interiorbasic"

    # ------------------------------------------------------------
    # BROOMSTICK: fallback genérico para theme no começo
    # ------------------------------------------------------------
    novo_broom_generico = corrigir_broomstick_theme_no_inicio_generico(valor_strip)
    if novo_broom_generico is not None:
        novo_broom_generico = normalizar_espacos(novo_broom_generico)

        if novo_broom_generico != valor_original:
            return novo_broom_generico, True, "broomstick_theme_movido_para_o_final_generico"

        return valor, False, "sem_mudanca_broomstick_theme_generico"

    # ------------------------------------------------------------
    # Diagnósticos
    # ------------------------------------------------------------
    if PADRAO_EFFECT_FOOD_QUALIDADE.search(valor_strip):
        return valor, False, "effectfood_qualidade_existe_mas_nao_entrou_nas_regras"

    if PADRAO_EFFECT_FOOD_GERAL.search(valor_strip):
        return valor, False, "tem_effectfood_mas_nao_entrou_nas_regras"

    if PADRAO_INTERIOR_THEME.search(valor_strip):
        return valor, False, "interiorprop_theme_existe_mas_nao_esta_no_inicio"

    if PADRAO_INTERIOR_PROP.search(valor_strip):
        return valor, False, "tem_interiorprop_mas_nao_entrou_nas_regras"

    if PADRAO_BROOMSTICK_THEME.search(valor_strip):
        return valor, False, "broomstick_theme_existe_mas_nao_entrou_nas_regras"

    if PADRAO_BROOMSTICK.search(valor_strip):
        return valor, False, "tem_broomstick_mas_nao_entrou_nas_regras"

    return valor, False, "sem_placeholder_relevante"


# ============================================================
# EXECUÇÃO
# ============================================================

def main():
    print("======================================")
    print("Corrigir ordem de placeholders")
    print("======================================")
    print(f"Arquivo de entrada: {ARQUIVO_ENTRADA.resolve()}")
    print()

    dados = carregar_json(ARQUIVO_ENTRADA)

    if not isinstance(dados, dict):
        raise ValueError("O JSON precisa ter um objeto/dicionário na raiz.")

    dados_corrigidos = {}

    mudancas = []
    detectados_nao_alterados = []

    total_chaves = len(dados)
    total_corrigidos = 0

    contadores_motivo = {}

    for chave, valor in dados.items():
        novo_valor, alterado, motivo = corrigir_valor(valor)

        # Chave permanece exatamente igual.
        dados_corrigidos[chave] = novo_valor

        contadores_motivo[motivo] = contadores_motivo.get(motivo, 0) + 1

        if alterado:
            total_corrigidos += 1
            mudancas.append({
                "chave": chave,
                "antes": valor,
                "depois": novo_valor,
                "motivo": motivo
            })
        else:
            if motivo != "sem_placeholder_relevante":
                detectados_nao_alterados.append({
                    "chave": chave,
                    "valor": valor,
                    "motivo": motivo
                })

    relatorio = {
        "arquivo_entrada": ARQUIVO_ENTRADA.name,
        "arquivo_saida": ARQUIVO_SAIDA.name,
        "total_chaves": total_chaves,
        "total_corrigidos": total_corrigidos,
        "observacao": (
            "As chaves foram preservadas exatamente como estavam. "
            "O script corrige apenas valores. "
            "EffectFoodCommon.Food_Perfect, Food_Delicious e Food_Normal no começo são movidos para o final do nome da comida. "
            "InteriorPropTheme no começo é movido para o final sem 'de'. "
            "BroomstickTheme + BroomstickCommon.Broomstick_Name é reordenado para nome + tema. "
            "BroomstickCommon.Broomstick_Type + BroomstickTheme + BroomstickCommon.Broomstick_Name é reordenado para nome + tema + tipo. "
            "Descrições compostas de vassoura são detectadas, mas não alteradas automaticamente. "
            "People, CreatureName, PotionName e CandyName antes de InteriorPropBasicName viram 'InteriorPropBasicName de Referencia'. "
            "Texto comum antes de InteriorPropBasicName também vira 'InteriorPropBasicName de Texto'. "
            "FishName e FishGrade com InteriorPropBasicName são detectados, mas não alterados automaticamente."
        ),
        "contadores_motivo": contadores_motivo,
        "mudancas": mudancas,
        "detectados_nao_alterados": detectados_nao_alterados
    }

    salvar_json(ARQUIVO_SAIDA, dados_corrigidos)
    salvar_json(ARQUIVO_RELATORIO, relatorio)

    print("Finalizado.")
    print()
    print(f"Total de chaves: {total_chaves}")
    print(f"Valores corrigidos: {total_corrigidos}")
    print()
    print("Resumo por motivo:")
    for motivo, total in sorted(contadores_motivo.items()):
        print(f"  {motivo}: {total}")
    print()
    print(f"Arquivo corrigido gerado em: {ARQUIVO_SAIDA.resolve()}")
    print(f"Relatório gerado em: {ARQUIVO_RELATORIO.resolve()}")


if __name__ == "__main__":
    main()