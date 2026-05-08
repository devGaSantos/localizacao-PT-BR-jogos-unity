import json
import shutil
import re
from pathlib import Path
from datetime import datetime

# =========================
# CONFIG
# =========================

ARQUIVO_MEMORIA_ATUAL = Path("memoria.json")
ARQUIVO_MEMORIA_EXTRAIDA = Path("memoria_extraida.json")

ARQUIVO_SAIDA = Path("memoria_atualizada.json")
ARQUIVO_FALTANTES = Path("memoria_faltantes.json")
ARQUIVO_RELATORIO = Path("relatorio_atualizacao_memoria.txt")

CRIAR_BACKUP = True

# Se True, não substitui por valores vazios/null
IGNORAR_VALOR_EXTRAIDO_VAZIO = True

# Se True, ignora traduções extraídas com caracteres asiáticos
IGNORAR_VALOR_EXTRAIDO_COM_CJK = True

# Se True, ignora quando o valor extraído é igual à chave em inglês
IGNORAR_VALOR_EXTRAIDO_IGUAL_CHAVE = True

# Se True, também salva em memoria_faltantes.json as entradas ignoradas por validação
# Ex: chave existe na extraída, mas valor extraído está vazio/CJK/igual à chave
INCLUIR_IGNORADOS_NOS_FALTANTES = True


# =========================
# REGEX / VALIDAÇÕES
# =========================

CJK_PATTERN = re.compile(r"[\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7AF]")


def tem_cjk(texto: str) -> bool:
    return bool(CJK_PATTERN.search(texto or ""))


def carregar_json(caminho: Path) -> dict:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    with open(caminho, "r", encoding="utf-8-sig") as f:
        dados = json.load(f)

    if not isinstance(dados, dict):
        raise ValueError(f"O arquivo {caminho} precisa ser um JSON de objeto/chave-valor.")

    return dados


def valor_valido_para_substituir(chave: str, valor: str) -> tuple[bool, str]:
    if valor is None:
        return False, "valor extraído é null"

    if not isinstance(valor, str):
        return False, "valor extraído não é string"

    if IGNORAR_VALOR_EXTRAIDO_VAZIO and valor.strip() == "":
        return False, "valor extraído vazio"

    if IGNORAR_VALOR_EXTRAIDO_COM_CJK and tem_cjk(valor):
        return False, "valor extraído contém CJK"

    if IGNORAR_VALOR_EXTRAIDO_IGUAL_CHAVE and valor.strip() == chave.strip():
        return False, "valor extraído igual à chave"

    return True, ""


def criar_backup(caminho: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = caminho.with_name(f"{caminho.stem}.backup-{timestamp}{caminho.suffix}")
    shutil.copy2(caminho, backup)
    return backup


def main():
    print("📖 Carregando arquivos...")

    memoria_atual = carregar_json(ARQUIVO_MEMORIA_ATUAL)
    memoria_extraida = carregar_json(ARQUIVO_MEMORIA_EXTRAIDA)

    if CRIAR_BACKUP:
        backup = criar_backup(ARQUIVO_MEMORIA_ATUAL)
        print(f"🛡️ Backup criado: {backup}")
    else:
        backup = None

    memoria_resultado = dict(memoria_atual)

    # Aqui entram as chaves que NÃO foram atualizadas pela extraída
    memoria_faltantes = {}

    total_chaves_atual = len(memoria_atual)
    total_chaves_extraida = len(memoria_extraida)

    encontradas = 0
    substituidas = 0
    iguais = 0
    ignoradas = 0
    nao_encontradas = 0
    faltantes_por_nao_existir = 0
    faltantes_por_ignorado = 0

    relatorio = []
    relatorio.append("RELATÓRIO DE ATUALIZAÇÃO DE MEMÓRIA")
    relatorio.append("=" * 80)
    relatorio.append(f"Memória atual:      {ARQUIVO_MEMORIA_ATUAL}")
    relatorio.append(f"Memória extraída:   {ARQUIVO_MEMORIA_EXTRAIDA}")
    relatorio.append(f"Saída atualizada:   {ARQUIVO_SAIDA}")
    relatorio.append(f"Saída faltantes:    {ARQUIVO_FALTANTES}")

    if backup:
        relatorio.append(f"Backup:             {backup}")

    relatorio.append("")
    relatorio.append(f"Chaves na memória atual:    {total_chaves_atual}")
    relatorio.append(f"Chaves na memória extraída: {total_chaves_extraida}")
    relatorio.append("")

    for chave, valor_atual in memoria_atual.items():
        # Caso 1: chave não existe na memória extraída
        # Vai para memoria_faltantes.json para você traduzir depois
        if chave not in memoria_extraida:
            nao_encontradas += 1
            faltantes_por_nao_existir += 1
            memoria_faltantes[chave] = valor_atual
            continue

        encontradas += 1
        valor_extraido = memoria_extraida[chave]

        valido, motivo = valor_valido_para_substituir(chave, valor_extraido)

        # Caso 2: chave existe na extraída, mas o valor extraído não é confiável
        if not valido:
            ignoradas += 1

            if INCLUIR_IGNORADOS_NOS_FALTANTES:
                faltantes_por_ignorado += 1
                memoria_faltantes[chave] = valor_atual

            relatorio.append("-" * 80)
            relatorio.append("[IGNORADO]")
            relatorio.append(f"Motivo: {motivo}")
            relatorio.append(f"Chave: {chave}")
            relatorio.append(f"Valor atual: {valor_atual}")
            relatorio.append(f"Valor extraído: {valor_extraido}")
            continue

        # Caso 3: chave existe e tradução já é igual
        if valor_atual == valor_extraido:
            iguais += 1
            continue

        # Caso 4: chave existe, valor extraído é válido e diferente
        memoria_resultado[chave] = valor_extraido
        substituidas += 1

        relatorio.append("-" * 80)
        relatorio.append("[SUBSTITUÍDO]")
        relatorio.append(f"Chave: {chave}")
        relatorio.append(f"Antes: {valor_atual}")
        relatorio.append(f"Depois: {valor_extraido}")

    # =========================
    # SALVA ARQUIVOS
    # =========================

    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(memoria_resultado, f, ensure_ascii=False, indent=2)

    with open(ARQUIVO_FALTANTES, "w", encoding="utf-8") as f:
        json.dump(memoria_faltantes, f, ensure_ascii=False, indent=2)

    # =========================
    # RELATÓRIO FINAL
    # =========================

    relatorio.append("")
    relatorio.append("=" * 80)
    relatorio.append("RESUMO")
    relatorio.append("=" * 80)
    relatorio.append(f"Chaves na memória atual:             {total_chaves_atual}")
    relatorio.append(f"Chaves na memória extraída:          {total_chaves_extraida}")
    relatorio.append(f"Chaves encontradas nas duas:         {encontradas}")
    relatorio.append(f"Valores substituídos:                {substituidas}")
    relatorio.append(f"Valores já eram iguais:              {iguais}")
    relatorio.append(f"Valores ignorados por validação:     {ignoradas}")
    relatorio.append(f"Chaves não encontradas na extraída:  {nao_encontradas}")
    relatorio.append("")
    relatorio.append(f"Entradas salvas em faltantes:        {len(memoria_faltantes)}")
    relatorio.append(f"  - Por não existirem na extraída:   {faltantes_por_nao_existir}")
    relatorio.append(f"  - Por valor extraído ignorado:     {faltantes_por_ignorado}")

    with open(ARQUIVO_RELATORIO, "w", encoding="utf-8") as f:
        f.write("\n".join(relatorio))

    print("\n🔥 Atualização concluída!")
    print(f"🧠 Memória atual original: {ARQUIVO_MEMORIA_ATUAL}")
    print(f"📦 Memória extraída usada: {ARQUIVO_MEMORIA_EXTRAIDA}")
    print(f"✅ Arquivo atualizado salvo em: {ARQUIVO_SAIDA}")
    print(f"📝 Faltantes salvos em: {ARQUIVO_FALTANTES}")
    print(f"📄 Relatório salvo em: {ARQUIVO_RELATORIO}")
    print("")
    print(f"🔎 Chaves encontradas nas duas: {encontradas}")
    print(f"🔁 Valores substituídos: {substituidas}")
    print(f"🟰 Valores já iguais: {iguais}")
    print(f"⚠️ Ignorados por validação: {ignoradas}")
    print(f"❌ Não encontradas na extraída: {nao_encontradas}")
    print(f"📝 Total em faltantes: {len(memoria_faltantes)}")


if __name__ == "__main__":
    main()