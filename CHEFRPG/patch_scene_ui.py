from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

PATCHES = {
    "NAME": "NOME",
    "Enter Name": "Seu nome  ",
    "Specialty": "Classe   ",
    "Rotisseur": "Assador  ",
    "Body Type": "Corpo    ",
    "Bodystyle": "Corpo    ",
    "Race": "Raca",
    "Human": "Hum. ",
    "Skin Color": "Cor pele  ",
    "Hair Color": "Cor cabelo",
    "Leggings": "Calca   ",
    "Birthday": "Anivers.",
    "Skill Points": "PONTOS HAB. ",
    "Endurance": "Vigor    ",
    "Cooking": "Cozinha",
    "Gathering": "Coleta   ",
    "Return to Menu": "Voltar ao menu",
    "Start Journey": "Comecar jogo!",
    "Meat Specialist": "ESP. DE CARNES ",
    "Begin with 3 meat recipes.": "Comece c/ 3 rec. de carne.",
}

SCENE_FILE_PATTERN = "level*"


def validate_patches() -> None:
    for source, target in PATCHES.items():
        source_bytes = source.encode("utf-8")
        target_bytes = target.encode("utf-8")
        if len(source_bytes) != len(target_bytes):
            raise ValueError(
                f"Patch precisa manter o mesmo tamanho em bytes: {source!r} -> {target!r}"
            )


def patch_bytes(data: bytes) -> tuple[bytes, dict[str, int]]:
    counts: dict[str, int] = {}
    patched = data
    for source, target in PATCHES.items():
        source_bytes = source.encode("utf-8")
        count = patched.count(source_bytes)
        counts[source] = count
        if count:
            patched = patched.replace(source_bytes, target.encode("utf-8"))
    return patched, counts


def find_scene_files(game_data: Path) -> list[Path]:
    scene_files = sorted(
        (path for path in game_data.glob(SCENE_FILE_PATTERN) if path.is_file()),
        key=lambda path: (len(path.name), path.name),
    )
    if not scene_files:
        raise FileNotFoundError(f"Nenhuma cena encontrada com o padrao {SCENE_FILE_PATTERN!r}")
    return scene_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Traduz textos fixos de UI em cenas do Chef RPG.")
    parser.add_argument("--game-data", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    validate_patches()
    game_data = Path(args.game_data).resolve()
    output = Path(args.output).resolve()
    report_path = Path(args.report).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {"sceneFiles": [], "patches": PATCHES}
    scene_files = find_scene_files(game_data)
    for source in scene_files:
        name = source.name
        destination = output / name
        shutil.copy2(source, destination)
        original = destination.read_bytes()
        patched, counts = patch_bytes(original)
        destination.write_bytes(patched)
        report["sceneFiles"].append(
            {
                "name": name,
                "source": str(source),
                "destination": str(destination),
                "bytes": len(patched),
                "changed": patched != original,
                "counts": counts,
            }
        )

    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Cenas de UI traduzidas: {len(scene_files)} arquivos level*")
    print(f"Relatorio: {report_path}")


if __name__ == "__main__":
    main()
