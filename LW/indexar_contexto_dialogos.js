const fs = require("fs");
const path = require("path");
const readline = require("readline");

const EXPORT_DIR = "dialogos/exportados";
const REPORT_PATH = "relatorios/indice_contexto_dialogos.json";

function findDialogueFile(directory) {
  const files = fs.readdirSync(directory)
    .filter((name) => name.includes("DialogueDB_en-") && name.endsWith(".txt"));
  if (files.length !== 1) {
    throw new Error(`Esperado 1 DialogueDB em ${directory}; encontrados ${files.length}.`);
  }
  return path.join(directory, files[0]);
}

function addField(entity, title, value) {
  if (!entity || !title) return;
  entity.fields[title] = value;
}

async function main() {
  const exportPath = findDialogueFile(EXPORT_DIR);
  const rl = readline.createInterface({
    input: fs.createReadStream(exportPath, { encoding: "utf8" }),
    crlfDelay: Infinity
  });

  const actors = new Map();
  const contexts = new Map();
  let currentActor = null;
  let currentConversation = null;
  let currentEntry = null;
  let waitingField = null;
  let lineNumber = 0;

  function finishActor() {
    if (!currentActor || currentActor.id === null) return;
    actors.set(String(currentActor.id), {
      id: currentActor.id,
      name: currentActor.fields["Name en"] || currentActor.fields.Name || `Actor ${currentActor.id}`,
      internalName: currentActor.fields.Name || null
    });
  }

  function finishEntry() {
    if (!currentEntry || !currentConversation) return;
    const source = currentEntry.fields.en;
    if (source === undefined) return;
    if (!contexts.has(source)) contexts.set(source, []);
    contexts.get(source).push({
      actorId: currentEntry.fields.Actor ?? currentConversation.fields.Actor ?? null,
      conversantId: currentEntry.fields.Conversant ?? currentConversation.fields.Conversant ?? null,
      conversationId: currentConversation.id,
      conversationTitle: currentConversation.fields.Title || null,
      entryId: currentEntry.id,
      exportLine: currentEntry.enLine
    });
  }

  for await (const line of rl) {
    lineNumber += 1;

    if (/^\s*0 Actor data\s*$/.test(line)) {
      finishActor();
      currentActor = { id: null, fields: {} };
      currentConversation = null;
      currentEntry = null;
      waitingField = null;
      continue;
    }

    if (/^\s*0 Conversation data\s*$/.test(line)) {
      finishActor();
      finishEntry();
      currentActor = null;
      currentConversation = { id: null, fields: {} };
      currentEntry = null;
      waitingField = null;
      continue;
    }

    if (/^\s*0 DialogueEntry data\s*$/.test(line)) {
      finishEntry();
      currentEntry = { id: null, fields: {}, enLine: null };
      waitingField = null;
      continue;
    }

    const idMatch = line.match(/^\s*0 int id = (-?\d+)\s*$/);
    if (idMatch) {
      const id = Number(idMatch[1]);
      if (currentEntry && currentEntry.id === null) currentEntry.id = id;
      else if (currentConversation && currentConversation.id === null) currentConversation.id = id;
      else if (currentActor && currentActor.id === null) currentActor.id = id;
      continue;
    }

    const titleMatch = line.match(/^\s*1 string title = "(.*)"\s*$/);
    if (titleMatch) {
      waitingField = titleMatch[1];
      continue;
    }

    if (waitingField) {
      const valueMatch = line.match(/^\s*1 string value = "(.*)"\s*$/);
      if (valueMatch) {
        const value = valueMatch[1];
        const entity = currentEntry || currentConversation || currentActor;
        addField(entity, waitingField, value);
        if (currentEntry && waitingField === "en") currentEntry.enLine = lineNumber;
      }
      waitingField = null;
    }
  }

  finishActor();
  finishEntry();

  const actorObject = Object.fromEntries([...actors.entries()].sort((a, b) => Number(a[0]) - Number(b[0])));
  const contextObject = {};
  for (const [source, occurrences] of contexts) {
    contextObject[source] = occurrences.map((occurrence) => ({
      ...occurrence,
      actorName: actorObject[String(occurrence.actorId)]?.name || null,
      conversantName: actorObject[String(occurrence.conversantId)]?.name || null
    }));
  }

  const report = {
    generatedAt: new Date().toISOString(),
    exportPath,
    actors: actorObject,
    counts: {
      actors: actors.size,
      uniqueLocalizedStrings: contexts.size,
      localizedOccurrences: [...contexts.values()].reduce((total, values) => total + values.length, 0)
    },
    contexts: contextObject
  };

  fs.mkdirSync("relatorios", { recursive: true });
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report.counts, null, 2));
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
