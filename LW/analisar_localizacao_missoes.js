const fs = require("fs");
const path = require("path");

const OLD_MISSIONS_DIR = path.resolve("..", "missoes", "exportados");
const CURRENT_EXPORTS_DIR = path.resolve("exportados");
const GAME_ADDRESSABLES_DIR = "C:/Program Files (x86)/Steam/steamapps/common/Little Witch in the Woods/LWIW_Data/StreamingAssets/aa";
const BUNDLES_DIR = path.join(GAME_ADDRESSABLES_DIR, "StandaloneWindows64");
const CATALOG_PATH = path.join(GAME_ADDRESSABLES_DIR, "catalog.json");
const DEFAULT_BUNDLE_PATH = path.join(BUNDLES_DIR, "defaultlocalgroup_assets_all.bundle");
const DIALOGUE_BUNDLE_PATH = path.join(BUNDLES_DIR, "dialoguedb_assets_all.bundle");
const RESOURCES_PATH = "C:/Program Files (x86)/Steam/steamapps/common/Little Witch in the Woods/LWIW_Data/resources.assets";
const REPORT_PATH = "relatorios/analise_localizacao_missoes_atual.json";

function parseEnglishFields(text) {
  const fields = [];
  const starts = [...text.matchAll(/^\s*0 TextTableField data\s*$/gm)].map((match) => match.index);
  for (let index = 0; index < starts.length; index += 1) {
    const block = text.slice(starts[index], starts[index + 1] ?? text.length);
    const fieldName = block.match(/^\s*1 string m_fieldName = "(.*)"\s*$/m)?.[1];
    const valuesMarker = block.indexOf("0 string m_values");
    if (!fieldName || valuesMarker < 0) continue;
    const keyPart = block.slice(0, valuesMarker);
    const valuePart = block.slice(valuesMarker);
    const keys = [...keyPart.matchAll(/^\s*0 int data = (-?\d+)\s*$/gm)].map((match) => Number(match[1]));
    const values = [...valuePart.matchAll(/^\s*1 string data = "(.*)"\s*$/gm)].map((match) => match[1]);
    const englishIndex = keys.indexOf(2);
    if (englishIndex < 0 || values[englishIndex] === undefined || !values[englishIndex].trim()) continue;
    fields.push({ fieldName, english: values[englishIndex] });
  }
  return fields;
}

function containsUtf8(buffer, value) {
  return value.length > 0 && buffer.includes(Buffer.from(value, "utf8"));
}

function main() {
  const oldFiles = fs.readdirSync(OLD_MISSIONS_DIR)
    .filter((name) => /-resources\.assets-\d+\.txt$/i.test(name))
    .sort();
  const currentExportFiles = fs.readdirSync(CURRENT_EXPORTS_DIR).filter((name) => name.endsWith(".txt")).sort();
  const currentExports = currentExportFiles.map((name) => ({
    name,
    text: fs.readFileSync(path.join(CURRENT_EXPORTS_DIR, name), "utf8")
  }));
  for (const entry of currentExports) {
    entry.values = new Set([...entry.text.matchAll(/m_Localized = "(.*)"/g)].map((match) => match[1]));
  }
  const catalog = JSON.parse(fs.readFileSync(CATALOG_PATH, "utf8"));
  const currentTextTables = catalog.m_InternalIds
    .filter((value) => value.includes("/Storyline/Data/TextTable/") && value.endsWith(".asset"))
    .map((value) => path.basename(value, ".asset"))
    .sort((a, b) => a.localeCompare(b));
  const defaultBundle = fs.readFileSync(DEFAULT_BUNDLE_PATH);
  const dialogueBundle = fs.readFileSync(DIALOGUE_BUNDLE_PATH);
  const resourcesAssets = fs.readFileSync(RESOURCES_PATH);

  const assets = oldFiles.map((fileName) => {
    const assetName = fileName.replace(/-resources\.assets-\d+\.txt$/i, "");
    const fields = parseEnglishFields(fs.readFileSync(path.join(OLD_MISSIONS_DIR, fileName), "utf8"));
    const strings = fields.map((field) => {
      const currentFiles = currentExports
        .filter((entry) => entry.values.has(field.english))
        .map((entry) => entry.name);
      const referenceFiles = currentExports
        .filter((entry) => !entry.values.has(field.english) && entry.text.includes(field.english))
        .map((entry) => entry.name);
      return {
        ...field,
        inDefaultLocalGroup: containsUtf8(defaultBundle, field.english),
        inDialogueDB: containsUtf8(dialogueBundle, field.english),
        inResourcesAssets: containsUtf8(resourcesAssets, field.english),
        currentLocalizationFiles: currentFiles,
        currentReferenceFiles: referenceFiles
      };
    });
    return {
      assetName,
      oldFile: fileName,
      existsAsCurrentTextTable: currentTextTables.includes(assetName),
      stringCount: strings.length,
      stringsInDefaultLocalGroup: strings.filter((entry) => entry.inDefaultLocalGroup).length,
      stringsInDialogueDB: strings.filter((entry) => entry.inDialogueDB).length,
      stringsInCurrentLocalization: strings.filter((entry) => entry.currentLocalizationFiles.length > 0).length,
      currentLocalizationFiles: [...new Set(strings.flatMap((entry) => entry.currentLocalizationFiles))].sort(),
      currentReferenceFiles: [...new Set(strings.flatMap((entry) => entry.currentReferenceFiles))].sort(),
      stringsNotFoundExactly: strings.filter((entry) =>
        !entry.inDefaultLocalGroup && !entry.inDialogueDB && !entry.inResourcesAssets && entry.currentLocalizationFiles.length === 0
      ),
      strings
    };
  });

  const stringsToFindInOtherBundles = [...new Set(assets
    .filter((asset) => !asset.existsAsCurrentTextTable)
    .flatMap((asset) => asset.strings)
    .filter((entry) => !entry.inDefaultLocalGroup && !entry.inDialogueDB && !entry.inResourcesAssets && entry.currentLocalizationFiles.length === 0)
    .map((entry) => entry.english))];
  const otherBundleMatches = new Map(stringsToFindInOtherBundles.map((value) => [value, []]));
  const bundleFiles = fs.readdirSync(BUNDLES_DIR)
    .filter((name) => name.endsWith(".bundle"))
    .filter((name) => ![path.basename(DEFAULT_BUNDLE_PATH), path.basename(DIALOGUE_BUNDLE_PATH)].includes(name));
  for (const bundleName of bundleFiles) {
    const buffer = fs.readFileSync(path.join(BUNDLES_DIR, bundleName));
    for (const value of stringsToFindInOtherBundles) {
      if (containsUtf8(buffer, value)) otherBundleMatches.get(value).push(bundleName);
    }
  }
  for (const asset of assets) {
    for (const entry of asset.strings) {
      entry.otherBundleFiles = otherBundleMatches.get(entry.english) || [];
    }
    asset.otherBundleFiles = [...new Set(asset.strings.flatMap((entry) => entry.otherBundleFiles))].sort();
    asset.stringsNotFoundExactly = asset.strings.filter((entry) =>
      !entry.inDefaultLocalGroup &&
      !entry.inDialogueDB &&
      !entry.inResourcesAssets &&
      entry.currentLocalizationFiles.length === 0 &&
      entry.otherBundleFiles.length === 0
    );
  }

  const oldAssetNames = assets.map((asset) => asset.assetName);
  const report = {
    generatedAt: new Date().toISOString(),
    paths: {
      oldMissions: OLD_MISSIONS_DIR,
      currentExports: CURRENT_EXPORTS_DIR,
      catalog: CATALOG_PATH,
      defaultLocalGroup: DEFAULT_BUNDLE_PATH,
      dialogueDB: DIALOGUE_BUNDLE_PATH,
      resourcesAssets: RESOURCES_PATH
    },
    summary: {
      oldTextTables: oldAssetNames.length,
      currentTextTables: currentTextTables.length,
      oldTablesStillPresent: oldAssetNames.filter((name) => currentTextTables.includes(name)).length,
      oldTablesRemovedOrMoved: oldAssetNames.filter((name) => !currentTextTables.includes(name)).length,
      newCurrentTables: currentTextTables.filter((name) => !oldAssetNames.includes(name)).length
    },
    currentTextTables,
    oldTablesStillPresent: oldAssetNames.filter((name) => currentTextTables.includes(name)),
    oldTablesRemovedOrMoved: oldAssetNames.filter((name) => !currentTextTables.includes(name)),
    newCurrentTables: currentTextTables.filter((name) => !oldAssetNames.includes(name)),
    assets
  };

  fs.mkdirSync(path.dirname(REPORT_PATH), { recursive: true });
  fs.writeFileSync(REPORT_PATH, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify({
    ...report.summary,
    currentTextTables,
    oldTablesRemovedOrMoved: report.oldTablesRemovedOrMoved,
    newCurrentTables: report.newCurrentTables,
    movedContent: assets
      .filter((asset) => !asset.existsAsCurrentTextTable)
      .map((asset) => ({
        assetName: asset.assetName,
        stringCount: asset.stringCount,
        stringsInCurrentLocalization: asset.stringsInCurrentLocalization,
        stringsInDialogueDB: asset.stringsInDialogueDB,
        currentLocalizationFiles: asset.currentLocalizationFiles,
        currentReferenceFiles: asset.currentReferenceFiles,
        otherBundleFiles: asset.otherBundleFiles,
        stringsNotFoundExactly: asset.stringsNotFoundExactly.length
      }))
  }, null, 2));
}

main();
