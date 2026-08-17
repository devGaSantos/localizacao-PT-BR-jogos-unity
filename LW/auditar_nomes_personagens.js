const fs = require("fs");
const path = require("path");

const EXPORT_DIR = "dialogos/exportados";
const MEMORIES = [
  "dialogos/memory/memoria.json",
  "dialogos/memory/traduzidas_por_translator.json",
  "memoria_revisado.json"
];

// Nomes pessoais confirmados pelo DialogueDB, wiki e personagens históricos
// mencionados no corpus. Rótulos descritivos (Bartender, Train Crew etc.) ficam fora.
const PERSONAL_NAMES = [
  "Ellie", "Virgil", "Enite", "Rubrum", "Arden", "Kyla", "Freddie", "Vinch", "Diane", "Aurea",
  "Roy", "Kent", "Arin", "Rex", "Alvin", "Aria", "Clala", "Dana", "Bjorn", "Theo", "Pax", "Lisa",
  "Laurel", "Baobab", "Rahel", "Brave", "Aiden", "William", "Jenny", "Stephan", "Felix", "Tanis",
  "Janifer", "Brad", "Lucerine", "Mila", "Parks", "Blueriver", "Silverrain", "Whitegarden",
  "Redember", "Rustystone", "Greenvine", "Ortu", "Windknot", "SilverRain"
];

const CANONICAL_ALIASES = [
  { canonical: "Theo", aliases: ["Theo", "Teo"] }
];

function dialogueFile() {
  const files = fs.readdirSync(EXPORT_DIR).filter((name) => name.includes("DialogueDB_en-") && name.endsWith(".txt"));
  if (files.length !== 1) throw new Error(`Esperado 1 DialogueDB; encontrados ${files.length}.`);
  return path.join(EXPORT_DIR, files[0]);
}

function actorNames(file) {
  const text = fs.readFileSync(file, "utf8");
  const actorSection = text.slice(0, text.indexOf(" 0 Conversation conversations"));
  const lines = actorSection.split(/\r?\n/);
  const names = [];
  for (let index = 0; index < lines.length - 1; index += 1) {
    if (!lines[index].includes('1 string title = "Name en"')) continue;
    const match = lines[index + 1].match(/1 string value = "(.*)"/);
    if (match && match[1].trim()) names.push(match[1].trim());
  }
  return [...new Set(names)].filter((name) => name !== "System");
}

function hasName(text, name, caseSensitive = false) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^\\p{L}])${escaped}(?=$|[^\\p{L}])`, caseSensitive ? "u" : "iu").test(text);
}

function hasDisplayedName(text, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^\\p{L}\\p{N}_])${escaped}(?=$|[^\\p{L}\\p{N}_])`, "u").test(text);
}

function stripTechnicalNames(text) {
  return text.replace(/\{[^}]+\}/g, " ").replace(/\[lua\((?:[^()]|\([^()]*\))*\)\]/g, " ");
}

function scanMemory(file, names) {
  if (!fs.existsSync(file)) return { file, missing: true, exactNameChanges: [], nameMissingFromTarget: [], canonicalNameViolations: [] };
  const memory = JSON.parse(fs.readFileSync(file, "utf8"));
  const exactNameChanges = [];
  const nameMissingFromTarget = [];
  const canonicalNameViolations = [];

  for (const [source, targetValue] of Object.entries(memory)) {
    const target = String(targetValue);
    for (const name of names) {
      if (!hasName(source, name, true)) continue;
      const item = { name, source, target };
      if (source.trim() === name && target.trim() !== name) exactNameChanges.push(item);
      else if (!hasName(target, name, true)) nameMissingFromTarget.push(item);
    }
    for (const rule of CANONICAL_ALIASES) {
      const visibleSource = stripTechnicalNames(source);
      const visibleTarget = stripTechnicalNames(target);
      if (!rule.aliases.some((alias) => hasDisplayedName(visibleSource, alias))) continue;
      if (!hasDisplayedName(visibleTarget, rule.canonical)) canonicalNameViolations.push({ canonical: rule.canonical, source, target });
    }
  }
  return { file, missing: false, entries: Object.keys(memory).length, exactNameChanges, nameMissingFromTarget, canonicalNameViolations };
}

function md(value) {
  return String(value).replace(/\|/g, "\\|").replace(/\r?\n/g, "<br>");
}

function main() {
  const exportPath = dialogueFile();
  const extractedActorNames = actorNames(exportPath);
  const names = [...new Set(PERSONAL_NAMES)];
  const files = MEMORIES.map((file) => scanMemory(file, names));
  const report = {
    generatedAt: new Date().toISOString(),
    exportPath,
    extractedActorNames,
    auditedPersonalNames: names,
    counts: {
      extractedActorNames: extractedActorNames.length,
      auditedPersonalNames: names.length,
      exactNameChanges: files.reduce((sum, file) => sum + file.exactNameChanges.length, 0),
      nameMissingFromTargetCandidates: files.reduce((sum, file) => sum + file.nameMissingFromTarget.length, 0),
      canonicalNameViolations: files.reduce((sum, file) => sum + file.canonicalNameViolations.length, 0)
    },
    files
  };

  fs.mkdirSync("relatorios", { recursive: true });
  fs.writeFileSync("relatorios/auditoria_nomes_personagens.json", `${JSON.stringify(report, null, 2)}\n`, "utf8");

  let markdown = "# Auditoria de nomes de personagens\n\n";
  markdown += "Regra: nomes próprios de personagens permanecem exatamente como no inglês. Nomes de criaturas seguem o glossário próprio.\n\n";
  markdown += `## Nomes pessoais auditados (${names.length})\n\n${names.map((name) => `\`${name}\``).join(", ")}\n\n`;
  markdown += "## Nomes exatos alterados\n\n| Arquivo | Nome | Tradução encontrada |\n| --- | --- | --- |\n";
  for (const file of files) for (const item of file.exactNameChanges) markdown += `| ${md(file.file)} | ${md(item.name)} | ${md(item.target)} |\n`;
  markdown += "\n## Nome ausente ou alterado dentro de frase\n\nEstes casos exigem revisão: também podem ser omissões naturais sem mudança do nome.\n\n| Arquivo | Nome | Original | Tradução atual |\n| --- | --- | --- | --- |\n";
  for (const file of files) for (const item of file.nameMissingFromTarget) markdown += `| ${md(file.file)} | ${md(item.name)} | ${md(item.source)} | ${md(item.target)} |\n`;
  markdown += "\n## Violações de nomes canônicos\n\n| Arquivo | Nome canônico | Original | Tradução atual |\n| --- | --- | --- | --- |\n";
  for (const file of files) for (const item of file.canonicalNameViolations) markdown += `| ${md(file.file)} | ${md(item.canonical)} | ${md(item.source)} | ${md(item.target)} |\n`;
  fs.writeFileSync("relatorios/auditoria_nomes_personagens.md", markdown, "utf8");
  console.log(JSON.stringify({ ...report.counts, auditedNames: names }, null, 2));
}

main();
