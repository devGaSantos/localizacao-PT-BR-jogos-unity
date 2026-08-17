const fs = require("fs");
const path = require("path");
const readline = require("readline");

const EXPORT_DIR = "dialogos/exportados";
const OUTPUT_DIR = "dialogos/traduzidos";
const MEMORY_PATH = "dialogos/memory/memoria.json";

const STRONG_ENGLISH = new Set([
  "the", "of", "and", "or", "to", "from", "with", "without", "for", "is", "are", "was", "were",
  "be", "been", "being", "you", "your", "yours", "you're", "you've", "you'll", "we", "our", "ours",
  "they", "their", "theirs", "they're", "them", "he", "his", "him", "she", "her", "hers", "this",
  "that", "these", "those", "not", "can", "could", "will", "would", "should", "do", "does", "did",
  "have", "has", "had", "in", "on", "at", "by", "as", "but", "if", "when", "where", "what", "why",
  "how", "who", "which", "whose", "through", "into", "about", "before", "after", "first", "then", "now",
  "also", "just", "really", "something", "anything", "everything", "nothing", "there", "here", "only",
  "don't", "doesn't", "didn't", "isn't", "aren't", "wasn't", "weren't", "won't", "wouldn't", "shouldn't",
  "can't", "cannot", "haven't", "hasn't", "let's", "keep", "reading", "bored", "daughter", "son",
  "mother", "father", "witch", "workshop", "broomstick", "museum", "recipe", "candy", "book", "train",
  "ticket", "village", "house", "white", "prickly", "vine"
]);

// Exclui palavras que tambem sao portuguesas, como "as", "do", "no" e "a".
const PARTIAL_ENGLISH = new Set([
  "the", "and", "or", "to", "from", "with", "without", "is", "are", "was", "were", "been",
  "being", "you", "your", "yours", "you're", "you've", "you'll", "we", "our", "ours", "they", "their",
  "theirs", "they're", "them", "his", "him", "she", "her", "hers", "this", "that", "these",
  "those", "not", "can", "could", "would", "should", "does", "did", "have", "has", "had",
  "but", "if", "when", "where", "what", "why", "how", "who", "which", "whose", "through", "into",
  "about", "before", "after", "first", "then", "now", "also", "just", "really", "something",
  "anything", "everything", "nothing", "there", "here", "only", "don't", "doesn't", "didn't", "isn't",
  "aren't", "wasn't", "weren't", "won't", "wouldn't", "shouldn't", "can't", "cannot", "haven't",
  "hasn't", "daughter", "son", "mother", "father", "witch", "workshop", "broomstick", "museum",
  "recipe", "candy", "book", "train", "ticket", "village", "house"
]);

function findDialogueFile(directory) {
  const files = fs.readdirSync(directory).filter((name) => name.includes("DialogueDB_en-") && name.endsWith(".txt"));
  if (files.length !== 1) throw new Error(`Esperado 1 DialogueDB em ${directory}; encontrados ${files.length}.`);
  return path.join(directory, files[0]);
}

async function parseEnglishFields(filePath) {
  const stream = fs.createReadStream(filePath, { encoding: "utf8" });
  const rl = readline.createInterface({ input: stream, crlfDelay: Infinity });
  const entries = [];
  let waitingForValue = false;
  let lineNumber = 0;

  for await (const line of rl) {
    lineNumber += 1;
    if (/^\s*1 string title = "en"\s*$/.test(line)) {
      waitingForValue = true;
      continue;
    }
    if (!waitingForValue) continue;
    const match = line.match(/^\s*1 string value = "(.*)"\s*$/);
    if (match) entries.push({ value: match[1], line: lineNumber });
    waitingForValue = false;
  }
  return entries;
}

function stripTechnical(text) {
  return text
    .replace(/\[lua\((?:[^()]|\([^()]*\))*\)\]/g, " ")
    .replace(/\[\/?em\d+\]/g, " ")
    .replace(/<\/?[^>]+>/g, " ")
    .replace(/\{[^}]+\}/g, " ");
}

function words(text) {
  return stripTechnical(text).toLowerCase().match(/[\p{L}]+(?:['\u2019][\p{L}]+)?/gu) || [];
}

function isTechnicalOrNonlinguistic(text) {
  const trimmed = text.trim();
  return !/[A-Za-z]{2}/.test(trimmed)
    || /^(?:GetQuest|SetQuest|SendMessage|SetFace|Variable|Actor|Conversation|Sequencer|Lua|\[lua|\{|\()/i.test(trimmed)
    || /^[_A-Z0-9.:-]+$/.test(trimmed);
}

function classifyIdentical(source) {
  if (isTechnicalOrNonlinguistic(source)) return { category: "technical_or_nonlinguistic", matchedEnglish: [] };
  if (/^Magna cum laude,? Ellie Blueriver\.$/.test(source)
    || source === "<shake>A-aaah!</shake> R-Rahel...?"
    || source === "Vine Deli") {
    return { category: "ambiguous_identity", matchedEnglish: [] };
  }
  if (source === "<wave>Do-do-fa! Sol-la! Sol-fa!</wave>") {
    return { category: "technical_or_nonlinguistic", matchedEnglish: [] };
  }
  const tokens = words(source);
  const strong = [...new Set(tokens.filter((token) => STRONG_ENGLISH.has(token)))];
  if (tokens.length >= 4 || strong.length) return { category: "untranslated", matchedEnglish: strong };
  return { category: "ambiguous_identity", matchedEnglish: [] };
}

function partialEnglish(target) {
  return [...new Set(words(target).filter((token) => PARTIAL_ENGLISH.has(token)))];
}

function md(value) {
  return String(value).replace(/\|/g, "\\|").replace(/\\r/g, "`\\r`").replace(/\n/g, "<br>");
}

async function main() {
  const exportPath = findDialogueFile(EXPORT_DIR);
  const outputPath = findDialogueFile(OUTPUT_DIR);
  const memory = JSON.parse(fs.readFileSync(MEMORY_PATH, "utf8"));
  const exported = await parseEnglishFields(exportPath);
  const output = await parseEnglishFields(outputPath);
  const unique = new Map();

  for (let index = 0; index < exported.length; index += 1) {
    const source = exported[index].value;
    if (!source.trim()) continue;
    if (!unique.has(source)) unique.set(source, { source, occurrences: [], outputValues: new Set() });
    const item = unique.get(source);
    item.occurrences.push({ exportLine: exported[index].line, outputLine: output[index]?.line ?? null });
    if (output[index]) item.outputValues.add(output[index].value);
  }

  const missingMemory = [];
  const emptyTranslation = [];
  const untranslated = [];
  const ambiguousIdentity = [];
  const technicalIdentity = [];
  const partialEnglishCandidates = [];
  const outputStillEnglish = [];
  const translatedInMemoryButNotOutput = [];

  for (const item of unique.values()) {
    const source = item.source;
    const target = memory[source];
    const base = {
      source,
      target: target ?? null,
      occurrences: item.occurrences.length,
      firstExportLine: item.occurrences[0].exportLine,
      outputValues: [...item.outputValues]
    };

    if (!(source in memory)) {
      missingMemory.push(base);
    } else if (!String(target).trim()) {
      emptyTranslation.push(base);
    } else if (target === source) {
      const classification = classifyIdentical(source);
      if (classification.category === "technical_or_nonlinguistic") technicalIdentity.push(base);
      else if (classification.category === "untranslated") {
        untranslated.push({ ...base, matchedEnglish: classification.matchedEnglish });
        if ([...item.outputValues].some((value) => value === source)) outputStillEnglish.push(base);
      } else ambiguousIdentity.push(base);
    } else {
      const matches = partialEnglish(target);
      if (matches.length) partialEnglishCandidates.push({ ...base, matchedEnglish: matches });
      if ([...item.outputValues].some((value) => value === source)) translatedInMemoryButNotOutput.push(base);
    }
  }

  const report = {
    generatedAt: new Date().toISOString(),
    exportPath,
    outputPath,
    memoryPath: MEMORY_PATH,
    counts: {
      exportedOccurrences: exported.length,
      outputOccurrences: output.length,
      uniqueNonemptyExportedStrings: unique.size,
      missingMemory: missingMemory.length,
      emptyTranslation: emptyTranslation.length,
      confirmedUntranslatedIdentity: untranslated.length,
      ambiguousIdentity: ambiguousIdentity.length,
      technicalOrNonlinguisticIdentity: technicalIdentity.length,
      partialEnglishCandidates: partialEnglishCandidates.length,
      confirmedOutputStillEnglish: outputStillEnglish.length,
      translatedInMemoryButNotOutput: translatedInMemoryButNotOutput.length
    },
    missingMemory,
    emptyTranslation,
    confirmedUntranslatedIdentity: untranslated,
    partialEnglishCandidates,
    ambiguousIdentity,
    technicalOrNonlinguisticIdentity: technicalIdentity,
    confirmedOutputStillEnglish: outputStillEnglish,
    translatedInMemoryButNotOutput
  };

  fs.mkdirSync("relatorios", { recursive: true });
  fs.writeFileSync("relatorios/auditoria_dialogos_nao_traduzidos.json", `${JSON.stringify(report, null, 2)}\n`, "utf8");

  let markdown = "# Auditoria de diálogos não traduzidos\n\n";
  markdown += `Exportado: \`${exportPath}\`  \nMemória: \`${MEMORY_PATH}\`  \nSaída: \`${outputPath}\`\n\n`;
  markdown += "## Contagens\n\n";
  for (const [name, count] of Object.entries(report.counts)) markdown += `- ${name}: ${count}\n`;
  markdown += "\n## Não traduzidos confirmados\n\n| Original | Valor atual | Ocorrências | Linha exportada |\n| --- | --- | --- | --- |\n";
  for (const item of untranslated) markdown += `| ${md(item.source)} | ${md(item.target)} | ${item.occurrences} | ${item.firstExportLine} |\n`;
  markdown += "\n## Ausentes da memória\n\n| Original | Ocorrências | Linha exportada |\n| --- | --- | --- |\n";
  for (const item of missingMemory) markdown += `| ${md(item.source)} | ${item.occurrences} | ${item.firstExportLine} |\n`;
  markdown += "\n## Possível inglês em traduções parciais\n\n| Original | Tradução atual | Palavras detectadas |\n| --- | --- | --- |\n";
  for (const item of partialEnglishCandidates) markdown += `| ${md(item.source)} | ${md(item.target)} | ${item.matchedEnglish.join(", ")} |\n`;
  markdown += "\n## Identidades ambíguas\n\nNomes, interjeições, efeitos ou textos curtos que precisam de decisão humana.\n\n| Texto | Ocorrências | Linha exportada |\n| --- | --- | --- |\n";
  for (const item of ambiguousIdentity) markdown += `| ${md(item.source)} | ${item.occurrences} | ${item.firstExportLine} |\n`;
  markdown += "\n## Identidades técnicas ou não linguísticas\n\n| Texto | Ocorrências | Linha exportada |\n| --- | --- | --- |\n";
  for (const item of technicalIdentity) markdown += `| ${md(item.source)} | ${item.occurrences} | ${item.firstExportLine} |\n`;
  markdown += "\n## Traduzidas na memória, mas não aplicadas\n\n| Original | Tradução da memória | Linha exportada |\n| --- | --- | --- |\n";
  for (const item of translatedInMemoryButNotOutput) markdown += `| ${md(item.source)} | ${md(item.target)} | ${item.firstExportLine} |\n`;
  markdown += "\nO JSON contém as mesmas listas com os valores encontrados na saída e metadados completos.\n";
  fs.writeFileSync("relatorios/auditoria_dialogos_nao_traduzidos.md", markdown, "utf8");

  console.log(JSON.stringify(report.counts, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
