const fs = require("fs");

const MEMORY_PATH = "dialogos/memory/memoria.json";
const TRANSLATOR_PATH = "dialogos/memory/traduzidas_por_translator.json";
const CONTEXT_PATH = "relatorios/indice_contexto_dialogos.json";
const REPORT_JSON = "relatorios/auditoria_qualidade_linguistica_dialogos.json";
const REPORT_MD = "relatorios/auditoria_qualidade_linguistica_dialogos.md";

const VERIFIED_ACTOR_GENDER = {
  Ellie: "feminino",
  Kyla: "feminino",
  Enite: "feminino",
  Diane: "feminino",
  Aurea: "feminino",
  Arin: "feminino",
  Clala: "feminino",
  Dana: "feminino",
  Lisa: "feminino",
  Rahel: "feminino",
  Roy: "masculino",
  Alvin: "masculino",
  Theo: "masculino",
  Rubrum: "masculino",
  Rex: "masculino",
  Arden: "masculino",
  Bjorn: "masculino",
  Kent: "masculino",
  Vinch: "masculino",
  Virgil: "masculino",
  Freddie: "masculino"
};

const MASCULINE_MARKERS = "animado|cansado|preocupado|surpreso|curioso|ansioso|aliviado|ocupado|confuso|impressionado|interessado|empolgado|chocado|nervoso|sozinho|grato|certo|convencido|perdido|pronto|decepcionado|entediado|assustado|envergonhado|acostumado";
const FEMININE_MARKERS = "animada|cansada|preocupada|surpresa|curiosa|ansiosa|aliviada|ocupada|confusa|impressionada|interessada|empolgada|chocada|nervosa|sozinha|grata|certa|convencida|perdida|pronta|decepcionada|entediada|assustada|envergonhada|acostumada";

function firstPersonGenderMarker(target, gender) {
  const markers = gender === "masculino" ? MASCULINE_MARKERS : FEMININE_MARKERS;
  const copula = new RegExp(`(?<!\\p{L})(?:eu\\s+)?(?:estou|sou|fiquei|me sinto|continuo|ficarei|estarei)\\s+(?:muito\\s+|bem\\s+|realmente\\s+|tão\\s+)?(?:${markers})(?!\\p{L})`, "iu");
  const thanks = new RegExp(`(?<!\\p{L})${gender === "masculino" ? "obrigado" : "obrigada"}(?!\\p{L})`, "iu");
  return copula.test(target) || thanks.test(target);
}

function contextualGenderMismatch(target, contexts) {
  const actors = [...new Set(contexts.map((context) => context.actorName).filter(Boolean))];
  if (actors.length !== 1) return null;
  const expected = VERIFIED_ACTOR_GENDER[actors[0]];
  if (!expected) return null;
  const opposite = expected === "feminino" ? "masculino" : "feminino";
  if (!firstPersonGenderMarker(target, opposite)) return null;
  return {
    id: "verified_actor_gender_mismatch",
    category: "concordancia_genero",
    severity: "alta",
    description: `Flexão de primeira pessoa incompatível com o ator confirmado (${actors[0]}: ${expected}).`
  };
}

function secondPersonGenderMarker(target, gender) {
  const markers = gender === "masculino" ? MASCULINE_MARKERS : FEMININE_MARKERS;
  const explicitYou = new RegExp(`(?<!\\p{L})você\\s+(?:está|é|ficou|parece|anda|continua)\\s+(?:muito\\s+|bem\\s+|realmente\\s+|tão\\s+)?(?:${markers})(?!\\p{L})`, "iu");
  const imperative = new RegExp(`(?:^|[.!?]\\s+)(?:esteja|fique|seja)\\s+(?:muito\\s+|bem\\s+)?(?:${markers})(?!\\p{L})`, "iu");
  const welcome = new RegExp(`(?<!\\p{L})bem-vind${gender === "masculino" ? "o" : "a"}(?!\\p{L})`, "iu");
  return explicitYou.test(target) || imperative.test(target) || welcome.test(target);
}

function contextualConversantGenderMismatch(target, contexts) {
  const conversants = [...new Set(contexts.map((context) => context.conversantName).filter(Boolean))];
  if (conversants.length !== 1) return null;
  const expected = VERIFIED_ACTOR_GENDER[conversants[0]];
  if (!expected) return null;
  const opposite = expected === "feminino" ? "masculino" : "feminino";
  if (!secondPersonGenderMarker(target, opposite)) return null;
  return {
    id: "verified_conversant_gender_mismatch",
    category: "concordancia_genero",
    severity: "alta",
    description: `Flexão dirigida ao interlocutor incompatível com o conversante confirmado (${conversants[0]}: ${expected}).`
  };
}

function stripTechnical(text) {
  return text
    .replace(/\[lua\((?:[^()]|\([^()]*\))*\)\]/g, " ")
    .replace(/\[\/?em\d+\]/g, " ")
    .replace(/<\/?[^>]+>/g, " ")
    .replace(/\{[^}]+\}/g, " ");
}

function has(text, regex) {
  regex.lastIndex = 0;
  return regex.test(text);
}

function paired(id, category, severity, description, sourceRegex, targetRegex) {
  return {
    id,
    category,
    severity,
    description,
    test(source, target) {
      return has(source, sourceRegex) && has(target, targetRegex);
    }
  };
}

function targetOnly(id, category, severity, description, targetRegex) {
  return {
    id,
    category,
    severity,
    description,
    test(_source, target) {
      return has(target, targetRegex);
    }
  };
}

const rules = [
  targetOnly(
    "plural_pronoun_singular_verb",
    "concordancia_verbal",
    "alta",
    "Pronome plural seguido de verbo flexionado no singular.",
    /\b(?:eles|elas|vocês|nós)\s+(?:é|está|foi|tem|vai|pode|deve|parece|precisa|quer)\b/iu
  ),
  targetOnly(
    "singular_pronoun_plural_verb",
    "concordancia_verbal",
    "alta",
    "Pronome singular seguido de verbo flexionado no plural.",
    /\b(?:eu|você|ele|ela|isso|isto|aquilo|a gente)\s+(?:são|estão|foram|têm|vão|podem|devem|parecem|precisam|querem)\b/iu
  ),
  targetOnly(
    "a_gente_plural",
    "concordancia_verbal",
    "alta",
    "A expressão 'a gente' pede verbo na terceira pessoa do singular.",
    /\ba gente\s+(?:somos|estamos|fomos|temos|vamos|podemos|devemos|queremos|precisamos)\b/iu
  ),
  targetOnly(
    "existential_haver_plural",
    "concordancia_verbal",
    "media",
    "Possível uso plural de haver com sentido de existir ou ocorrer.",
    /\b(?:houveram|haviam|haverão)\b/iu
  ),
  targetOnly(
    "elapsed_time_fazer_plural",
    "concordancia_verbal",
    "alta",
    "Fazer indicando tempo decorrido deve permanecer no singular.",
    /\bfazem\s+(?:(?:mais de|quase|uns?|alguns?)\s+)?(?:\d+|dois|três|quatro|cinco|seis|sete|oito|nove|dez|muitos?)?\s*(?:dias|anos|meses|semanas|horas|minutos|tempo)\b/iu
  ),
  targetOnly(
    "article_adjective_feminine",
    "concordancia_nominal",
    "alta",
    "Artigo feminino seguido de adjetivo masculino antes do substantivo.",
    /\b(?:uma|aquela|esta|essa)\s+(?:novo|bom|mau|pequeno|bonito|certo|errado|perfeito|ótimo|estranho|outro|único|primeiro|último|mesmo|próprio)\s+[\p{L}-]+/iu
  ),
  targetOnly(
    "article_adjective_masculine",
    "concordancia_nominal",
    "alta",
    "Artigo masculino seguido de adjetivo feminino antes do substantivo.",
    /\b(?:um|aquele|este|esse)\s+(?:nova|boa|má|pequena|bonita|certa|errada|perfeita|ótima|estranha|outra|única|primeira|última|mesma|própria)\s+[\p{L}-]+/iu
  ),
  targetOnly(
    "para_mim_infinitive",
    "regencia",
    "alta",
    "Possível 'para mim' exercendo função de sujeito de um infinitivo.",
    /\bpara mim\s+(?:fazer|ir|ver|pegar|levar|trazer|dizer|dar|resolver|cuidar|usar|preparar|ajudar|conseguir|encontrar|saber|entender|aprender|decidir)\b/iu
  ),
  targetOnly(
    "entre_eu",
    "regencia",
    "alta",
    "Depois de preposição, o pronome esperado é 'mim'.",
    /\bentre eu e\b|\bentre [^,.!?]{1,30} e eu\b/iu
  ),
  targetOnly(
    "future_subjunctive_ver",
    "conjugacao",
    "alta",
    "Depois de 'se/quando/assim que', ver pode exigir futuro do subjuntivo: vir.",
    /\b(?:se|quando|assim que)\s+(?:eu|você|ele|ela|a gente|nós|vocês|eles|elas)\s+ver\b/iu
  ),
  targetOnly(
    "future_subjunctive_irregular",
    "conjugacao",
    "media",
    "Possível infinitivo no lugar do futuro do subjuntivo após conectivo temporal ou condicional.",
    /\b(?:se|quando|assim que)\s+(?:eu|você|ele|ela|a gente|nós|vocês|eles|elas)\s+(?:fazer|trazer|dizer|ter|estar|manter|obter|poder|saber|querer|pôr)\b/iu
  ),
  targetOnly(
    "esperar_indicative",
    "conjugacao",
    "media",
    "Depois de esperar/tomara que, normalmente se espera o subjuntivo.",
    /\b(?:espero|esperamos|tomara)\s+que\s+[^.!?]{0,55}\b(?:vai|vão|pode|podem|é|são|está|estão|tem|têm|fica|ficam|faz|fazem)\b/iu
  ),
  targetOnly(
    "talvez_indicative",
    "conjugacao",
    "media",
    "Talvez introduz hipótese e pode exigir subjuntivo.",
    /\btalvez\s+[^.!?]{0,45}\b(?:vai|vão|é|são|está|estão|tem|têm|fica|ficam|faz|fazem|pode|podem)\b/iu
  ),
  targetOnly(
    "redundant_direction",
    "redundancia",
    "alta",
    "Construção direcional redundante.",
    /\b(?:subir para cima|descer para baixo|entrar para dentro|sair para fora|encarar de frente)\b/iu
  ),
  targetOnly(
    "redundant_time",
    "redundancia",
    "alta",
    "Construção temporal redundante.",
    /\bhá\s+[^.!?]{0,25}\s+atrás\b/iu
  ),
  targetOnly(
    "redundant_adverb",
    "redundancia",
    "media",
    "Possível repetição desnecessária de sentido.",
    /\b(?:repetir novamente|continua ainda|apenas só|planejar antecipadamente|surpresa inesperada|outra alternativa)\b/iu
  ),
  paired(
    "literal_i_wonder",
    "traducao_literal",
    "alta",
    "'I wonder' foi mantido como o calque 'eu me pergunto'.",
    /\bI wonder\b/iu,
    /\beu me pergunto\b/iu
  ),
  paired(
    "literal_make_sure",
    "traducao_literal",
    "alta",
    "'Make sure' foi traduzido literalmente como certificar-se.",
    /\bmake sure\b/iu,
    /\bcertifi(?:que|car|cou|cado|cada|carmos|carei|cará|quem)-?se\b/iu
  ),
  paired(
    "literal_let_me",
    "traducao_literal",
    "media",
    "'Let me' pode ter sido preservado como uma estrutura artificial em PT-BR.",
    /\blet me\b/iu,
    /\bdeix(?:a|e|em)-?me\b|\bdeixa eu\b/iu
  ),
  paired(
    "literal_sound",
    "traducao_literal",
    "alta",
    "Sounds/sound pode significar 'parece', não necessariamente 'soa'.",
    /\bsounds?\b/iu,
    /\bsoa(?:m|va|vam|ria|riam)?\b/iu
  ),
  paired(
    "literal_take_a_look",
    "traducao_literal",
    "media",
    "'Take a look' pode ter sido traduzido mecanicamente como 'dar uma olhada'.",
    /\btake a look\b/iu,
    /\b(?:dar|dê|dá|dando|dei|demos|vamos dar) uma olhada\b/iu
  ),
  paired(
    "literal_look_at",
    "traducao_literal",
    "media",
    "'Look at' pode pedir uma formulação contextual mais natural.",
    /\blook at\b/iu,
    /\bolh(?:e|a|ar|ando) para\b/iu
  ),
  paired(
    "literal_check_out",
    "traducao_literal",
    "media",
    "'Check out' foi possivelmente reduzido ao formal 'verificar'.",
    /\bcheck(?:ed|ing)? out\b/iu,
    /\bverific(?:ar|a|e|ando|ou|amos)\b/iu
  ),
  paired(
    "literal_feel_free",
    "traducao_literal",
    "alta",
    "'Feel free' não costuma ser natural como 'sinta-se livre' neste registro.",
    /\bfeel free\b/iu,
    /\bsinta-se livre\b/iu
  ),
  paired(
    "literal_take_your_time",
    "traducao_literal",
    "alta",
    "'Take your time' foi traduzido literalmente.",
    /\btake your time\b/iu,
    /\btome seu tempo\b|\bleve o seu tempo\b/iu
  ),
  paired(
    "literal_good_time",
    "traducao_literal",
    "alta",
    "'Have a good time' foi traduzido literalmente em vez de 'divirta-se'.",
    /\bhave a good time\b/iu,
    /\btenha um bom tempo\b/iu
  ),
  paired(
    "literal_here_you_go",
    "traducao_literal",
    "alta",
    "'Here you go' pode ter sido traduzido palavra por palavra.",
    /\bhere you go\b/iu,
    /\baqui (?:vai|está) você\b/iu
  ),
  paired(
    "literal_good_for_you",
    "traducao_literal",
    "alta",
    "'Good for you' pode ter sido traduzido palavra por palavra.",
    /\bgood for you\b/iu,
    /\bbom para você\b/iu
  ),
  paired(
    "literal_you_bet",
    "traducao_literal",
    "alta",
    "'You bet' pode ter sido interpretado como aposta literal.",
    /\byou bet\b/iu,
    /\bvocê aposta\b/iu
  ),
  paired(
    "literal_i_see",
    "traducao_literal",
    "media",
    "'I see' discursivo pode significar 'entendo', não visão física.",
    /^I see[,.!]?$/iu,
    /\beu vejo\b/iu
  ),
  paired(
    "literal_for_now",
    "traducao_literal",
    "alta",
    "'For now' costuma ser 'por enquanto', não 'por agora'.",
    /\bfor now\b/iu,
    /\bpor agora\b/iu
  ),
  paired(
    "false_friend_actually",
    "falso_cognato",
    "alta",
    "Actually não significa atualmente.",
    /\bactually\b/iu,
    /\batualmente\b/iu
  ),
  paired(
    "false_friend_eventually",
    "falso_cognato",
    "alta",
    "Eventually não significa eventualmente.",
    /\beventually\b/iu,
    /\beventualmente\b/iu
  ),
  paired(
    "false_friend_realize",
    "falso_cognato",
    "alta",
    "Realize, no sentido de perceber, não significa realizar.",
    /\breali[sz](?:e|ed|ing|es)\b/iu,
    /\brealiz(?:ar|ei|ou|ando|amos|aram|a|e)\b/iu
  ),
  paired(
    "false_friend_library",
    "falso_cognato",
    "alta",
    "Library significa biblioteca, não livraria.",
    /\blibrar(?:y|ies)\b/iu,
    /\blivraria(?:s)?\b/iu
  ),
  paired(
    "false_friend_parents",
    "falso_cognato",
    "alta",
    "Parents significa pais, não parentes.",
    /\bparents\b/iu,
    /\bparentes\b/iu
  ),
  targetOnly(
    "awkward_ser_capaz",
    "traducao_literal",
    "baixa",
    "Uso frequente de 'ser capaz de' pode ser calque de can/be able to.",
    /\b(?:ser|sou|é|somos|são|era|eram|foi|foram|serei|será|serão|seja|sejam|seria|seriam) capaz(?:es)? de\b/iu
  ),
  targetOnly(
    "awkward_no_need",
    "traducao_literal",
    "baixa",
    "'Não há necessidade de' pode estar formal demais para diálogo.",
    /\bnão há necessidade de\b/iu
  ),
  targetOnly(
    "awkward_de_alguma_forma",
    "traducao_literal",
    "baixa",
    "'De alguma forma' pode ser calque contextual de somehow.",
    /\bde alguma forma\b/iu
  ),
  targetOnly(
    "gendered_first_person",
    "genero_contextual",
    "baixa",
    "Forma de primeira pessoa marcada por gênero; exige confirmação do falante.",
    /\b(?:estou|estava|fiquei|ficarei|sou|me sinto|continuo)\s+(?:animad[oa]|cansad[oa]|preocupad[oa]|surpres[oa]|curios[oa]|ansios[oa]|aliviad[oa]|ocupad[oa]|confus[oa]|impressionad[oa]|interessad[oa]|empolgad[oa]|chocad[oa]|nervos[oa]|sozinh[oa]|grat[oa]|cert[oa]|convencid[oa]|perdid[oa]|pront[oa])\b/iu
  )
];

function markdown(value) {
  return String(value)
    .replace(/\|/g, "\\|")
    .replace(/\r/g, "`\\r`")
    .replace(/\n/g, "<br>");
}

function main() {
  const memory = JSON.parse(fs.readFileSync(MEMORY_PATH, "utf8"));
  const translator = JSON.parse(fs.readFileSync(TRANSLATOR_PATH, "utf8"));
  const contextIndex = fs.existsSync(CONTEXT_PATH)
    ? JSON.parse(fs.readFileSync(CONTEXT_PATH, "utf8"))
    : { contexts: {} };
  const candidates = [];
  const ruleCounts = Object.fromEntries(rules.map((rule) => [rule.id, 0]));
  const categoryCounts = {};

  for (const [source, rawTarget] of Object.entries(memory)) {
    const target = String(rawTarget);
    const cleanSource = stripTechnical(source);
    const cleanTarget = stripTechnical(target);
    const contexts = contextIndex.contexts[source] || [];
    const reasons = rules
      .filter((rule) => rule.test(cleanSource, cleanTarget))
      .map(({ id, category, severity, description }) => ({ id, category, severity, description }));

    const genderMismatch = contextualGenderMismatch(cleanTarget, contexts);
    if (genderMismatch) reasons.push(genderMismatch);
    const conversantGenderMismatch = contextualConversantGenderMismatch(cleanTarget, contexts);
    if (conversantGenderMismatch) reasons.push(conversantGenderMismatch);

    if (!reasons.length) continue;
    for (const reason of reasons) {
      ruleCounts[reason.id] = (ruleCounts[reason.id] || 0) + 1;
      categoryCounts[reason.category] = (categoryCounts[reason.category] || 0) + 1;
    }
    candidates.push({
      source,
      target,
      inTranslatorMemory: Object.prototype.hasOwnProperty.call(translator, source),
      contexts,
      reasons
    });
  }

  const severityOrder = { alta: 0, media: 1, baixa: 2 };
  candidates.sort((a, b) => {
    const aSeverity = Math.min(...a.reasons.map((reason) => severityOrder[reason.severity]));
    const bSeverity = Math.min(...b.reasons.map((reason) => severityOrder[reason.severity]));
    return aSeverity - bSeverity || a.source.localeCompare(b.source, "en");
  });

  const report = {
    generatedAt: new Date().toISOString(),
    memoryPath: MEMORY_PATH,
    entriesReviewed: Object.keys(memory).length,
    candidates: candidates.length,
    ruleCounts,
    categoryCounts,
    items: candidates
  };

  fs.mkdirSync("relatorios", { recursive: true });
  fs.writeFileSync(REPORT_JSON, `${JSON.stringify(report, null, 2)}\n`, "utf8");

  let md = "# Auditoria de qualidade linguística dos diálogos\n\n";
  md += `Memória: \`${MEMORY_PATH}\`  \n`;
  md += `Entradas examinadas: ${report.entriesReviewed}  \n`;
  md += `Candidatos para revisão humana: ${report.candidates}\n\n`;
  md += "## Contagens por regra\n\n";
  for (const rule of rules) md += `- \`${rule.id}\`: ${ruleCounts[rule.id]}\n`;
  md += "\n## Candidatos\n\n";
  md += "| Severidade | Regra | Original | Tradução atual | No lote Translator |\n";
  md += "| --- | --- | --- | --- | --- |\n";
  for (const item of candidates) {
    const severity = item.reasons.map((reason) => reason.severity).join(", ");
    const ids = item.reasons.map((reason) => `\`${reason.id}\``).join(", ");
    md += `| ${severity} | ${ids} | ${markdown(item.source)} | ${markdown(item.target)} | ${item.inTranslatorMemory ? "sim" : "não"} |\n`;
  }
  fs.writeFileSync(REPORT_MD, md, "utf8");

  console.log(JSON.stringify({
    entriesReviewed: report.entriesReviewed,
    candidates: report.candidates,
    categoryCounts: report.categoryCounts,
    ruleCounts: Object.fromEntries(Object.entries(ruleCounts).filter(([, count]) => count > 0))
  }, null, 2));
}

main();
