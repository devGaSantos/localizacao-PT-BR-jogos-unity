import argparse
import json
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

TOKEN_RE = re.compile(
    r"(\r\n|\r|\n|\[[^\]]+\]|<[^>]+>|\{[^{}]+\}|\([a-z_][a-z0-9_]*\)|_)",
)

PUNCTUATION_NORMALIZATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }
)


def load_object(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError(f"JSON precisa ser um objeto: {path}")
    return value


def save_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(value, file, ensure_ascii=False, indent=2)
        file.write("\n")
    temporary.replace(path)


def protect_tokens(text: str):
    tokens = []

    def replace(match):
        token = f"__CHEF_TOKEN_{len(tokens)}__"
        tokens.append((token, match.group(0)))
        return token

    return TOKEN_RE.sub(replace, text), tokens


def repair_mojibake(text: str) -> str:
    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text
    return repaired if repaired.count("\ufffd") <= text.count("\ufffd") else text


def translation_variants(source: str) -> list[str]:
    variants = []
    for candidate in (source, repair_mojibake(source)):
        normalized = candidate.translate(PUNCTUATION_NORMALIZATION)
        for value in (candidate, normalized):
            if value not in variants:
                variants.append(value)
    return variants


def translate(translator, source: str) -> str:
    protected, tokens = protect_tokens(source)
    translated = translator.translate(protected)
    if not isinstance(translated, str) or not translated.strip():
        raise RuntimeError(f"Tradutor nao retornou texto para: {source!r}")
    for token, original in tokens:
        if token not in translated:
            raise RuntimeError(f"Tradutor alterou o token protegido {token}: {source!r}")
        translated = translated.replace(token, original)
    return translated


def translate_with_fallbacks(translator, source: str) -> str:
    last_error = None
    for variant in translation_variants(source):
        try:
            return translate(translator, variant)
        except Exception as error:  # noqa: BLE001
            last_error = error
    raise RuntimeError(last_error)


def main() -> None:
    parser = argparse.ArgumentParser(description="Traduz os textos faltantes do Chef RPG.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--memory", required=True)
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    memory_path = Path(args.memory).resolve()
    report = load_object(report_path)
    memory = load_object(memory_path)

    missing_by_source = {}
    for table in report.get("Tables", []):
        for item in table.get("Missing", []):
            source = item.get("Source")
            key = item.get("Key", "")
            if isinstance(source, str) and source.strip():
                missing_by_source.setdefault(source, []).append(key)

    pending = [source for source in missing_by_source if not str(memory.get(source, "")).strip()]
    if not pending:
        print("Nenhum texto faltante para traduzir.")
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = memory_path.with_name(f"{memory_path.stem}.before_auto_{timestamp}{memory_path.suffix}")
    shutil.copy2(memory_path, backup)
    needs_translator = any(
        not all(key.startswith("character_name_") for key in missing_by_source[source])
        for source in pending
    )
    translator = None
    if needs_translator:
        try:
            from deep_translator import GoogleTranslator
        except ImportError as exc:
            raise SystemExit(
                "Dependencia ausente: deep-translator. Instale com: "
                "python -m pip install deep-translator"
            ) from exc
        translator = GoogleTranslator(source="en", target="pt")
    translated_count = 0
    preserved_names = 0

    print(f"Traduzindo {len(pending)} textos unicos. Backup: {backup}")
    for index, source in enumerate(pending, start=1):
        keys = missing_by_source[source]
        if keys and all(key.startswith("character_name_") for key in keys):
            result = source
            preserved_names += 1
        else:
            last_error = None
            for attempt in range(3):
                try:
                    result = translate_with_fallbacks(translator, source)
                    break
                except Exception as error:  # noqa: BLE001
                    last_error = error
                    time.sleep(1 + attempt)
            else:
                save_atomic(memory_path, memory)
                raise RuntimeError(f"Falha ao traduzir {source!r}: {last_error}")
            translated_count += 1
            time.sleep(0.05)

        memory[source] = result
        if index % 25 == 0 or index == len(pending):
            save_atomic(memory_path, memory)
            print(f"Progresso: {index}/{len(pending)}")

    result_report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "backup": str(backup),
        "translated": translated_count,
        "preservedCharacterNames": preserved_names,
        "memoryEntries": len(memory),
    }
    output = report_path.with_name("traducao_automatica_faltantes.json")
    save_atomic(output, result_report)
    print(f"Memoria atualizada: {memory_path}")
    print(f"Relatorio: {output}")


if __name__ == "__main__":
    main()
