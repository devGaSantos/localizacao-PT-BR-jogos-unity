const fs = require("fs");
const crypto = require("crypto");
const { TextDecoder } = require("util");

const FILES = [
  "dialogos/memory/memoria.json",
  "memoria_revisado.json"
];

const FORMAT_CHAR = /[\u00AD\u061C\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]/gu;
const EMBEDDED_QUESTION = /(?:\p{L}\?+\p{L}|\?+\p{Ll})/gu;
const MOJIBAKE = /(?:\u00C3[\u0080-\u00BF]|\u00C2[\u0080-\u00BF]|\u00E2(?:[\u0080-\u00BF]|\u20AC|\u2122|\u201A|\u0192|\u201E|\u2026|\u2020|\u2021|\u02C6|\u2030|\u0160|\u2039|\u0152|\u017D|\u2018|\u2019|\u201C|\u201D|\u2022|\u2013|\u2014|\u02DC|\u0161|\u203A|\u0153|\u017E|\u0178)|\u00F0\u0178|\u00EF\u00BB\u00BF)/gu;
const LITERAL_ESCAPE = /\\(?:u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2})/g;
const PRIVATE_USE = /[\uE000-\uF8FF]|[\u{F0000}-\u{FFFFD}]|[\u{100000}-\u{10FFFD}]/gu;
const NONCHARACTER = /[\uFDD0-\uFDEF]|[\u{FFFE}\u{FFFF}\u{1FFFE}\u{1FFFF}\u{2FFFE}\u{2FFFF}\u{3FFFE}\u{3FFFF}\u{4FFFE}\u{4FFFF}\u{5FFFE}\u{5FFFF}\u{6FFFE}\u{6FFFF}\u{7FFFE}\u{7FFFF}\u{8FFFE}\u{8FFFF}\u{9FFFE}\u{9FFFF}\u{AFFFE}\u{AFFFF}\u{BFFFE}\u{BFFFF}\u{CFFFE}\u{CFFFF}\u{DFFFE}\u{DFFFF}\u{EFFFE}\u{EFFFF}\u{FFFFE}\u{FFFFF}\u{10FFFE}\u{10FFFF}]/gu;

function context(text, index, length) {
  return text
    .slice(Math.max(0, index - 35), Math.min(text.length, index + length + 35))
    .replace(/\r/g, "\\r")
    .replace(/\n/g, "\\n");
}

function regexFindings(text, regex, type) {
  return [...text.matchAll(regex)].map((match) => ({
    type,
    match: match[0],
    codePoints: [...match[0]].map((char) => `U+${char.codePointAt(0).toString(16).toUpperCase().padStart(4, "0")}`),
    context: context(text, match.index, match[0].length)
  }));
}

function invalidCodeUnits(text) {
  const findings = [];
  for (let index = 0; index < text.length; index += 1) {
    const code = text.charCodeAt(index);
    const invalidControl = (code < 0x20 && ![0x09, 0x0a, 0x0d].includes(code)) || (code >= 0x7f && code <= 0x9f);
    const loneHigh = code >= 0xd800 && code <= 0xdbff && !(text.charCodeAt(index + 1) >= 0xdc00 && text.charCodeAt(index + 1) <= 0xdfff);
    const loneLow = code >= 0xdc00 && code <= 0xdfff && !(text.charCodeAt(index - 1) >= 0xd800 && text.charCodeAt(index - 1) <= 0xdbff);
    if (invalidControl || loneHigh || loneLow) {
      findings.push({
        type: invalidControl ? "invalid_control" : "lone_surrogate",
        codePoint: `U+${code.toString(16).toUpperCase().padStart(4, "0")}`,
        context: context(text, index, 1)
      });
    }
  }
  return findings;
}

function scanString(text) {
  const findings = [
    ...regexFindings(text, /\uFFFD/gu, "replacement_character"),
    ...regexFindings(text, FORMAT_CHAR, "format_or_invisible"),
    ...regexFindings(text, EMBEDDED_QUESTION, "question_mark_inside_word"),
    ...regexFindings(text, MOJIBAKE, "common_mojibake"),
    ...regexFindings(text, LITERAL_ESCAPE, "literal_unicode_escape"),
    ...regexFindings(text, PRIVATE_USE, "private_use"),
    ...regexFindings(text, NONCHARACTER, "unicode_noncharacter"),
    ...invalidCodeUnits(text)
  ];
  if (text !== text.normalize("NFC")) {
    findings.push({ type: "not_nfc_normalized", context: text.slice(0, 100) });
  }
  return findings;
}

function audit(path) {
  const bytes = fs.readFileSync(path);
  const hasBom = bytes.length >= 3 && bytes[0] === 0xef && bytes[1] === 0xbb && bytes[2] === 0xbf;
  const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  const json = JSON.parse(text.replace(/^\uFEFF/, ""));
  const keyFindings = [];
  const valueFindings = [];
  const punctuationWarnings = [];

  for (const [source, target] of Object.entries(json)) {
    for (const finding of scanString(source)) keyFindings.push({ source, ...finding });
    for (const finding of scanString(target)) valueFindings.push({ source, target, ...finding });

    const sourceQuestions = (source.match(/\?/g) || []).length;
    const targetQuestions = (target.match(/\?/g) || []).length;
    if (targetQuestions > sourceQuestions && !valueFindings.some((item) => item.source === source && item.type === "question_mark_inside_word")) {
      punctuationWarnings.push({ source, target, sourceQuestions, targetQuestions });
    }
  }

  return {
    path,
    entries: Object.keys(json).length,
    bytes: bytes.length,
    sha256: crypto.createHash("sha256").update(bytes).digest("hex"),
    utf8FatalDecode: "ok",
    jsonParse: "ok",
    bom: hasBom,
    valueFindings,
    keyFindings,
    punctuationWarnings
  };
}

const audits = FILES.map(audit);
const result = {
  generatedAt: new Date().toISOString(),
  cleanValues: audits.every((item) => !item.bom && item.valueFindings.length === 0),
  files: audits
};

fs.mkdirSync("relatorios", { recursive: true });
fs.writeFileSync("relatorios/auditoria_encoding_completa.json", `${JSON.stringify(result, null, 2)}\n`, "utf8");

console.log(JSON.stringify({
  cleanValues: result.cleanValues,
  files: audits.map((item) => ({
    path: item.path,
    entries: item.entries,
    bom: item.bom,
    valueFindings: item.valueFindings.length,
    keyFindings: item.keyFindings.length,
    punctuationWarnings: item.punctuationWarnings.length,
    sha256: item.sha256
  }))
}, null, 2));

if (!result.cleanValues) process.exitCode = 1;
