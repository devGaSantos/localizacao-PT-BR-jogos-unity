import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from deep_translator import GoogleTranslator
except ImportError as exc:
    raise SystemExit(
        "Dependencia ausente: deep-translator. Instale com: python -m pip install deep-translator"
    ) from exc


FLOW_GENERAL = "localization-string-tables-english(en)_assets_all"
FLOW_DIALOGUE = "dialoguedb_assets_all"
FLOW_MISSION_BUNDLE = "defaultlocalgroup_assets_all"
FLOW_MISSION_RESOURCES = "missoes_resources_assets"

TOKEN_RE = re.compile(
    r"(\r\n|\r|\n|\[lua\(.*?\)\]|\[[^\]]+\]|<[^>]+>|\{[^{}]+\})",
    re.DOTALL,
)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON precisa ser um objeto: {path}")
    return data


def save_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    temp.replace(path)


def escape_unity_dump(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def protect_tokens(text: str):
    tokens = []

    def repl(match):
        token = f"__LW_TOKEN_{len(tokens)}__"
        tokens.append((token, match.group(0)))
        return token

    return TOKEN_RE.sub(repl, text), tokens


def restore_tokens(text: str, tokens):
    restored = text
    for token, original in tokens:
        if token not in restored:
            raise RuntimeError(f"Translator alterou o token protegido {token}.")
        restored = restored.replace(token, original)
    return restored


def translate_text(translator: GoogleTranslator, source: str) -> str:
    if not source or not source.strip():
        return source

    leading = source[: len(source) - len(source.lstrip())]
    trailing = source[len(source.rstrip()) :]
    core_end = len(source) - len(trailing) if trailing else len(source)
    core = source[len(leading) : core_end]

    protected, tokens = protect_tokens(core)
    translated = translator.translate(protected)
    if not isinstance(translated, str) or not translated.strip():
        raise RuntimeError(f"Translator nao retornou traducao para: {source!r}")

    translated = restore_tokens(translated, tokens)
    return leading + translated + trailing


def memory_path_for_flow(flow: str, project: Path, missions_root: Path):
    if flow == FLOW_GENERAL:
        return project / "memoria_revisado.json", False
    if flow == FLOW_DIALOGUE:
        return project / "dialogos" / "memory" / "memoria.json", True
    if flow in (FLOW_MISSION_BUNDLE, FLOW_MISSION_RESOURCES):
        return missions_root / "memoria_missoes.json", False
    raise ValueError(f"Flow desconhecido no relatorio: {flow}")


def main():
    parser = argparse.ArgumentParser(
        description="Traduz somente os textos Missing do AssetPipeline e atualiza as memorias corretas."
    )
    parser.add_argument("--report", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--missions-root", required=True)
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    project = Path(args.project).resolve()
    missions_root = Path(args.missions_root).resolve()

    with report_path.open("r", encoding="utf-8") as f:
        report = json.load(f)

    flows = report.get("Flows")
    if not isinstance(flows, list):
        raise ValueError("Relatorio do AssetPipeline sem Flows valido.")

    jobs = []
    for flow_report in flows:
        flow = flow_report.get("Flow")
        missing = flow_report.get("Missing") or []
        memory_path, dump_escaped = memory_path_for_flow(flow, project, missions_root)
        for item in missing:
            source = item.get("Source")
            if isinstance(source, str) and source.strip():
                jobs.append((flow, source, memory_path, dump_escaped))

    if not jobs:
        print("Nenhum texto faltante para traduzir.")
        return

    memories = {}
    for _, _, memory_path, _ in jobs:
        if memory_path not in memories:
            memories[memory_path] = load_json(memory_path)

    translator = GoogleTranslator(source="en", target="pt")
    translated_cache = {}
    audit_entries = []

    total = len(jobs)
    for index, (flow, source, memory_path, dump_escaped) in enumerate(jobs, start=1):
        if source not in translated_cache:
            translated_cache[source] = translate_text(translator, source)
            time.sleep(0.05)

        translation = translated_cache[source]
        memory = memories[memory_path]
        key = escape_unity_dump(source) if dump_escaped else source
        value = escape_unity_dump(translation) if dump_escaped else translation

        existing = memory.get(key)
        if not isinstance(existing, str) or not existing.strip():
            memory[key] = value

        audit_entries.append(
            {
                "flow": flow,
                "memory": str(memory_path),
                "source": source,
                "translation": translation,
            }
        )
        print(f"[{index}/{total}] {flow}: traduzido")

    for path, memory in memories.items():
        save_json_atomic(path, memory)
        print(f"Memoria atualizada: {path}")

    audit_path = project / "relatorios" / "traducoes_automaticas_pipeline.json"
    audit = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceReport": str(report_path),
        "count": len(audit_entries),
        "translations": audit_entries,
    }
    save_json_atomic(audit_path, audit)
    print(f"Relatorio das traducoes automaticas: {audit_path}")


if __name__ == "__main__":
    main()
