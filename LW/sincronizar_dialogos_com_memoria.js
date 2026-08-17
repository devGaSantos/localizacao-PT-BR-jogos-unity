const fs = require("fs");
const path = require("path");

function findDialogueFile(directory) {
  const files = fs.readdirSync(directory).filter((name) => name.includes("DialogueDB_en-") && name.endsWith(".txt"));
  if (files.length !== 1) throw new Error(`Esperado 1 DialogueDB em ${directory}; encontrados ${files.length}.`);
  return path.join(directory, files[0]);
}

function englishValues(lines) {
  const entries = [];
  for (let index = 0; index < lines.length - 1; index += 1) {
    if (!/^\s*1 string title = "en"\s*$/.test(lines[index])) continue;
    const match = lines[index + 1].match(/^(\s*1 string value = ")(.*)("\s*)$/);
    if (!match) throw new Error(`Valor inglês não encontrado depois da linha ${index + 1}.`);
    entries.push({ lineIndex: index + 1, prefix: match[1], value: match[2], suffix: match[3] });
  }
  return entries;
}

function main() {
  const exportPath = findDialogueFile("dialogos/exportados");
  const outputPath = findDialogueFile("dialogos/traduzidos");
  const memory = JSON.parse(fs.readFileSync("dialogos/memory/memoria.json", "utf8"));
  const exportedText = fs.readFileSync(exportPath, "utf8");
  const outputText = fs.readFileSync(outputPath, "utf8");
  const newline = outputText.includes("\r\n") ? "\r\n" : "\n";
  const exportedLines = exportedText.split(/\r?\n/);
  const outputLines = outputText.split(/\r?\n/);
  const exported = englishValues(exportedLines);
  const output = englishValues(outputLines);
  if (exported.length !== output.length) throw new Error(`Entradas desalinhadas: ${exported.length} exportadas e ${output.length} na saída.`);

  let changed = 0;
  let missing = 0;
  for (let index = 0; index < exported.length; index += 1) {
    const source = exported[index].value;
    if (!(source in memory)) {
      if (source.trim()) missing += 1;
      continue;
    }
    const target = String(memory[source]);
    if (output[index].value === target) continue;
    outputLines[output[index].lineIndex] = `${output[index].prefix}${target}${output[index].suffix}`;
    changed += 1;
  }

  fs.writeFileSync(outputPath, outputLines.join(newline), "utf8");
  console.log(JSON.stringify({ exportPath, outputPath, entries: exported.length, changed, missing }, null, 2));
}

main();
