const fs = require("fs");
const path = require("path");

const EXPORT_DIR = path.join("dialogos", "exportados");
const OUTPUT_DIR = path.join("dialogos", "traduzidos");
const MEMORY_PATH = path.join("dialogos", "memory", "memoria.json");
const REPORT_PATH = path.join("relatorios", "relatorio_geracao_dialogos_memoria.json");

function findSingleDialogueExport() {
  const files = fs.readdirSync(EXPORT_DIR)
    .filter((name) => /^DialogueDB_en-.*\.txt$/i.test(name));
  if (files.length !== 1) {
    throw new Error(`Esperado 1 DialogueDB atual em ${EXPORT_DIR}; encontrados ${files.length}.`);
  }
  return path.join(EXPORT_DIR, files[0]);
}

function main() {
  const exportPath = findSingleDialogueExport();
  const memory = JSON.parse(fs.readFileSync(MEMORY_PATH, "utf8"));
  const sourceText = fs.readFileSync(exportPath, "utf8");
  const newline = sourceText.includes("\r\n") ? "\r\n" : "\n";
  const lines = sourceText.split(/\r?\n/);
  const missing = new Map();
  let occurrences = 0;
  let translated = 0;

  for (let index = 0; index < lines.length - 1; index += 1) {
    if (!/^\s*1 string title = "en"\s*$/.test(lines[index])) continue;
    const match = lines[index + 1].match(/^(\s*1 string value = ")(.*)("\s*)$/);
    if (!match) throw new Error(`Valor ingles ausente depois da linha ${index + 1}.`);

    occurrences += 1;
    const source = match[2];
    const target = memory[source];
    if (typeof target === "string" && target.trim()) {
      lines[index + 1] = `${match[1]}${target}${match[3]}`;
      translated += 1;
    } else if (source.trim()) {
      missing.set(source, (missing.get(source) || 0) + 1);
    }
  }

  if (occurrences === 0) throw new Error("Nenhuma entrada de dialogo em ingles foi encontrada.");

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  const outputPath = path.join(OUTPUT_DIR, `TRADUZIDO - ${path.basename(exportPath)}`);
  fs.writeFileSync(outputPath, lines.join(newline), "utf8");

  const report = {
    generatedAt: new Date().toISOString(),
    exportPath,
    outputPath,
    memoryPath: MEMORY_PATH,
    occurrences,
    translated,
    missingOccurrences: [...missing.values()].reduce((sum, count) => sum + count, 0),
    missingUnique: missing.size,
    missing: [...missing.entries()].map(([source, count]) => ({ source, count }))
  };
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
}

main();
