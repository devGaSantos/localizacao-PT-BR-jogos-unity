import json
import sys
import shutil
from pathlib import Path
from datetime import datetime


# ============================================================
# CONFIGURAÇÃO
# ============================================================

MEMORIA_PATH = "memoria.json"

REPORT_PATH = "substituicao_report.json"
NOT_FOUND_PATH = "substituicao_not_found.json"
BACKUP_DIR = "backups_substituicao"


# ============================================================
# FUNÇÕES DE ARQUIVO
# ============================================================

def carregar_json(caminho: str) -> dict:
    path = Path(caminho)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def salvar_json(dados: dict, caminho: str) -> None:
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def criar_backup(caminho: str) -> str:
    origem = Path(caminho)

    if not origem.exists():
        raise FileNotFoundError(f"Arquivo para backup não encontrado: {caminho}")

    Path(BACKUP_DIR).mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = Path(BACKUP_DIR) / f"{origem.stem}.backup_{timestamp}{origem.suffix}"

    shutil.copy2(origem, destino)

    return str(destino)


# ============================================================
# NORMALIZAÇÃO DO ARQUIVO DE SUBSTITUIÇÕES
# ============================================================

def extrair_valor_substituicao(valor):
    # Aceita formato direto:
    # "English key": "Texto revisado"
    #
    # Aceita formato antes/depois:
    # "English key": {
    #   "original": "...",
    #   "antes": "...",
    #   "depois": "Texto revisado"
    # }
    #
    # Também aceita campos "pt_final" ou "sugestao", se existirem.

    if isinstance(valor, str):
        return valor

    if isinstance(valor, dict):
        if "depois" in valor and isinstance(valor["depois"], str):
            return valor["depois"]

        if "pt_final" in valor and isinstance(valor["pt_final"], str):
            return valor["pt_final"]

        if "sugestao" in valor and isinstance(valor["sugestao"], str):
            return valor["sugestao"]

    raise ValueError(f"Formato de substituição inválido: {valor}")


def normalizar_substituicoes(dados: dict) -> dict:
    substituicoes = {}

    for chave, valor in dados.items():
        substituicoes[chave] = extrair_valor_substituicao(valor)

    return substituicoes


# ============================================================
# SUBSTITUIÇÃO
# ============================================================

def aplicar_substituicoes(memoria: dict, substituicoes: dict):
    memoria_atualizada = dict(memoria)

    aplicadas = {}
    nao_encontradas = {}
    inalteradas = {}
    alteradas = {}

    for chave_en, novo_pt in substituicoes.items():
        if chave_en not in memoria_atualizada:
            nao_encontradas[chave_en] = novo_pt
            continue

        antigo_pt = memoria_atualizada[chave_en]

        if antigo_pt == novo_pt:
            inalteradas[chave_en] = novo_pt
            aplicadas[chave_en] = novo_pt
            continue

        memoria_atualizada[chave_en] = novo_pt

        alteradas[chave_en] = {
            "antes": antigo_pt,
            "depois": novo_pt
        }

        aplicadas[chave_en] = novo_pt

    return memoria_atualizada, aplicadas, alteradas, inalteradas, nao_encontradas


# ============================================================
# CLI
# ============================================================

def mostrar_uso():
    print()
    print("Uso:")
    print("  python script_substituicao.py -replace arquivo_substituicoes.json")
    print()
    print("Exemplos:")
    print("  python script_substituicao.py -replace alteracoes_aprovadas_para_replace.json")
    print("  python script_substituicao.py -replace alteracoes_reprovadas_com_sugestao.json")
    print()


def main():
    if len(sys.argv) < 3:
        mostrar_uso()
        return

    comando = sys.argv[1]
    arquivo_substituicoes = sys.argv[2]

    if comando != "-replace":
        print(f"Comando inválido: {comando}")
        mostrar_uso()
        return

    print("Carregando memoria.json...")
    memoria = carregar_json(MEMORIA_PATH)

    print(f"Carregando substituições: {arquivo_substituicoes}")
    dados_substituicoes = carregar_json(arquivo_substituicoes)

    print("Normalizando substituições...")
    substituicoes = normalizar_substituicoes(dados_substituicoes)

    print(f"Total de substituições recebidas: {len(substituicoes)}")

    print("Criando backup do memoria.json...")
    backup_path = criar_backup(MEMORIA_PATH)
    print(f"Backup criado: {backup_path}")

    print("Aplicando substituições...")
    memoria_atualizada, aplicadas, alteradas, inalteradas, nao_encontradas = aplicar_substituicoes(
        memoria,
        substituicoes
    )

    print("Salvando memoria.json atualizado...")
    salvar_json(memoria_atualizada, MEMORIA_PATH)

    relatorio = {
        "arquivo_memoria": MEMORIA_PATH,
        "arquivo_substituicoes": arquivo_substituicoes,
        "backup_criado": backup_path,
        "total_memoria": len(memoria),
        "total_substituicoes_recebidas": len(substituicoes),
        "total_aplicadas": len(aplicadas),
        "total_alteradas": len(alteradas),
        "total_inalteradas": len(inalteradas),
        "total_nao_encontradas": len(nao_encontradas),
        "alteradas": alteradas,
        "inalteradas": inalteradas
    }

    salvar_json(relatorio, REPORT_PATH)
    salvar_json(nao_encontradas, NOT_FOUND_PATH)

    print()
    print("Concluído.")
    print(f"- memoria.json atualizado: {MEMORIA_PATH}")
    print(f"- Backup: {backup_path}")
    print(f"- Relatório: {REPORT_PATH}")
    print(f"- Não encontradas: {NOT_FOUND_PATH}")
    print()
    print("Resumo:")
    print(f"- Total no memoria.json: {len(memoria)}")
    print(f"- Substituições recebidas: {len(substituicoes)}")
    print(f"- Aplicadas: {len(aplicadas)}")
    print(f"- Alteradas de verdade: {len(alteradas)}")
    print(f"- Já estavam iguais: {len(inalteradas)}")
    print(f"- Não encontradas: {len(nao_encontradas)}")


if __name__ == "__main__":
    main()