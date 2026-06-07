import json
import subprocess
from pathlib import Path


COMMIT_BASE = "9c3fa1d4322f1f547216e01ac80c3d65b176ce9c"

# Nome do arquivo atual, considerando que o script está na mesma pasta do memoria.json
MEMORIA_LOCAL = "memoria.json"

# Arquivo de saída
OUTPUT_PATH = "frases_nao_modificadas_desde_commit.json"


def rodar_git(args, cwd=None):
    resultado = subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=cwd
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "Erro ao executar comando Git.\n\n"
            f"Comando: git {' '.join(args)}\n"
            f"Erro:\n{resultado.stderr}"
        )

    return resultado.stdout.strip()


def obter_raiz_git():
    """
    Descobre a raiz do repositório Git.
    Funciona mesmo rodando o script dentro de subpastas.
    """
    raiz = rodar_git(["rev-parse", "--show-toplevel"])
    return Path(raiz)


def obter_caminho_relativo_ao_git(arquivo_local: Path, raiz_git: Path):
    """
    Converte o caminho local do memoria.json para o caminho que o Git entende.
    Exemplo:
    C:/repo/LW/dialogos/memory/memoria.json
    vira:
    LW/dialogos/memory/memoria.json
    """
    caminho_relativo = arquivo_local.resolve().relative_to(raiz_git.resolve())

    # Git prefere barra normal mesmo no Windows
    return caminho_relativo.as_posix()


def carregar_json_atual(caminho: Path) -> dict:
    if not caminho.exists():
        raise FileNotFoundError(f"Arquivo atual não encontrado: {caminho}")

    with caminho.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def carregar_json_do_commit(commit: str, caminho_git: str, raiz_git: Path) -> dict:
    """
    Lê o memoria.json exatamente como ele estava em um commit específico.
    Usa o caminho relativo à raiz do repositório.
    """

    comando = ["show", f"{commit}:{caminho_git}"]

    resultado = subprocess.run(
        ["git"] + comando,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=raiz_git
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "Não foi possível ler o arquivo no commit informado.\n\n"
            f"Comando: git {' '.join(comando)}\n"
            f"Caminho usado no Git: {caminho_git}\n"
            f"Erro:\n{resultado.stderr}"
        )

    conteudo = resultado.stdout
    return json.loads(conteudo)


def salvar_json(dados: dict, caminho: Path) -> None:
    with caminho.open("w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def main():
    pasta_script = Path(__file__).resolve().parent
    caminho_memoria_atual = pasta_script / MEMORIA_LOCAL
    caminho_saida = pasta_script / OUTPUT_PATH

    print("Detectando raiz do repositório Git...")
    raiz_git = obter_raiz_git()

    print(f"Raiz Git: {raiz_git}")

    caminho_memoria_git = obter_caminho_relativo_ao_git(
        caminho_memoria_atual,
        raiz_git
    )

    print(f"Caminho do memoria.json no Git: {caminho_memoria_git}")

    print()
    print("Carregando memoria.json atual...")
    memoria_atual = carregar_json_atual(caminho_memoria_atual)

    print(f"Carregando memoria.json do commit {COMMIT_BASE}...")
    memoria_antiga = carregar_json_do_commit(
        COMMIT_BASE,
        caminho_memoria_git,
        raiz_git
    )

    nao_modificadas = {}
    modificadas = {}
    novas = {}
    removidas = {}

    for chave, valor_atual in memoria_atual.items():
        if chave not in memoria_antiga:
            novas[chave] = valor_atual
            continue

        valor_antigo = memoria_antiga[chave]

        if valor_atual == valor_antigo:
            nao_modificadas[chave] = valor_atual
        else:
            modificadas[chave] = {
                "antes": valor_antigo,
                "agora": valor_atual
            }

    for chave, valor_antigo in memoria_antiga.items():
        if chave not in memoria_atual:
            removidas[chave] = valor_antigo

    salvar_json(nao_modificadas, caminho_saida)

    print()
    print("Concluído.")
    print(f"Arquivo gerado: {caminho_saida}")
    print()
    print("Resumo:")
    print(f"- Frases no memoria.json atual: {len(memoria_atual)}")
    print(f"- Frases no memoria.json do commit: {len(memoria_antiga)}")
    print(f"- Não modificadas desde o commit: {len(nao_modificadas)}")
    print(f"- Modificadas desde o commit: {len(modificadas)}")
    print(f"- Novas depois do commit: {len(novas)}")
    print(f"- Existiam no commit, mas não existem mais agora: {len(removidas)}")


if __name__ == "__main__":
    main()