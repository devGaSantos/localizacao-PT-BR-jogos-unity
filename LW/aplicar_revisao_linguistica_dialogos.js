const fs = require("fs");

const MEMORY_PATH = "dialogos/memory/memoria.json";
const TRANSLATOR_PATH = "dialogos/memory/traduzidas_por_translator.json";
const AUDIT_PATH = "relatorios/auditoria_qualidade_linguistica_dialogos.json";
const CONTEXT_PATH = "relatorios/indice_contexto_dialogos.json";
const REPORT_PATH = "relatorios/revisao_linguistica_dialogos_20260815.json";
const BACKUP_MEMORY = "dialogos/memory/memoria.before_revisao_linguistica_20260815.json";
const BACKUP_TRANSLATOR = "dialogos/memory/traduzidas_por_translator.before_revisao_linguistica_20260815.json";

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

const GENDER_PAIRS = [
  ["obrigado", "obrigada"],
  ["animado", "animada"],
  ["cansado", "cansada"],
  ["preocupado", "preocupada"],
  ["surpreso", "surpresa"],
  ["curioso", "curiosa"],
  ["ansioso", "ansiosa"],
  ["aliviado", "aliviada"],
  ["ocupado", "ocupada"],
  ["confuso", "confusa"],
  ["impressionado", "impressionada"],
  ["interessado", "interessada"],
  ["empolgado", "empolgada"],
  ["chocado", "chocada"],
  ["nervoso", "nervosa"],
  ["sozinho", "sozinha"],
  ["grato", "grata"],
  ["certo", "certa"],
  ["convencido", "convencida"],
  ["perdido", "perdida"],
  ["pronto", "pronta"],
  ["decepcionado", "decepcionada"],
  ["entediado", "entediada"],
  ["assustado", "assustada"],
  ["envergonhado", "envergonhada"],
  ["acostumado", "acostumada"]
];

// Nestas falas, a flexão aparece dentro de uma citação e não descreve Ellie.
const GENDER_EXCLUSIONS = new Set([
  "Arden... Arden says thank you for \"you know what,\" although he didn't specify the favor.",
  "You could have simply said \"thank you.\""
]);

const manual = new Map();

function add(source, target, reason) {
  if (manual.has(source)) throw new Error(`Correção manual duplicada: ${source}`);
  manual.set(source, { target, reason });
}

add(
  "If you see a puzzle, you should solve it. It's manners.",
  "Se você vir um quebra-cabeça, deve resolvê-lo. É uma questão de educação.",
  "Corrige o futuro do subjuntivo de 'ver' e torna a segunda frase natural."
);
add(
  "I may travel around with A-Arin, but those are <wave>adventures.</wave>",
  "Posso até viajar por aí com a A-Arin, mas o que fazemos são <wave>aventuras.</wave>",
  "Corrige a concordância de 'isso são' sem alterar a ênfase."
);

add("But what made the first graduation ceremony different, I wonder?", "Mas o que será que tornou a primeira cerimônia de formatura diferente?", "Remove o calque de 'I wonder'.");
add("I wonder if the star the First Witch found was even brighter than this?", "Será que a estrela encontrada pela Primeira Bruxa era ainda mais brilhante que esta?", "Remove o calque de 'I wonder'.");
add("Right? I wonder how much Dana will love it.", "Né? A Dana vai adorar.", "Substitui uma tradução literal sem sentido por uma reação natural.");

add("And make sure to finish the preparations listed on [em1][lua(GetLocalizedString(\"Item\", \"FirstGraduationCeremonyForm_Name\"))][/em1].", "E não deixe de concluir os preparativos listados no [em1][lua(GetLocalizedString(\"Item\", \"FirstGraduationCeremonyForm_Name\"))][/em1].", "Naturaliza 'make sure'.");
add("Have you eaten? Make sure you keep your strength up.", "Você já comeu? Precisa se alimentar bem para manter as forças.", "Naturaliza 'make sure' e a recomendação sobre alimentação.");
add("It's for the village's wisteria tree. Please make sure they are informed.", "É para a glicínia da vila. Por favor, não deixe de avisar o pessoal.", "Evita voz passiva artificial e não presume gênero do grupo.");
add("Then please, make sure you never bring them near me.", "Então, por favor, nunca chegue perto de mim com isso.", "Remove o calque de 'make sure' e evita pronome sem referente claro.");

add("I'll put this [em1]book[/em1] at my [em1]flower shop[/em1]. Feel free to check it anytime.", "Vou deixar este [em1]livro[/em1] na minha [em1]floricultura[/em1]. Você pode consultá-lo quando quiser.", "Remove o calque de 'feel free'.");
add("Take your time and think it over.", "Pense com calma.", "Remove o calque de 'take your time'.");
add("Take your time to walk around, and let me know when you're leaving.", "Passeie com calma e me avise quando for embora.", "Remove o calque de 'take your time'.");
add("If it's difficult to decide, take some time.", "Se estiver difícil decidir, pense com calma.", "Substitui uma formulação literal por português natural.");

add("But for now...", "Mas, por enquanto...", "Traduz corretamente 'for now'.");
add("Do what you can for now.", "Faça o que puder por enquanto.", "Traduz corretamente 'for now'.");
add("For now, at least.", "Pelo menos por enquanto.", "Traduz corretamente 'for now'.");
add("Haha! I'm good for now!", "Haha! Estou bem por enquanto!", "Traduz corretamente 'for now'.");
add("I wanted to get that restored too, but that project's too big for now.", "Eu também queria restaurar aquilo, mas esse projeto é grande demais para encarar agora.", "Naturaliza 'for now' no contexto do projeto.");
add("Let's concentrate on what we're doing for now.", "Por enquanto, vamos nos concentrar no que estamos fazendo.", "Traduz corretamente 'for now'.");
add("Let's do what we can for now!", "Vamos fazer o que pudermos por enquanto!", "Traduz corretamente 'for now'.");
add("Let's forget about those people for now.", "Vamos esquecer essas pessoas por enquanto.", "Traduz corretamente 'for now'.");
add("Maybe they're just away for now.", "Talvez só tenham saído.", "Naturaliza a ausência temporária sem calque.");
add("Maybe... for now.", "Talvez... por enquanto.", "Traduz corretamente 'for now'.");
add("That's enough for now.", "Por enquanto, basta.", "Traduz corretamente 'for now'.");

add("But the Blue Fairy found out eventually and also turned into an apple — to deceive people.", "Mas, no fim, a Fada Azul descobriu e também se transformou numa maçã — para enganar as pessoas.", "Corrige o falso cognato 'eventually'.");
add("Haha, no need to rush. You'll get to meet everyone eventually.", "Haha, não tenha pressa. Você vai acabar conhecendo todo mundo.", "Corrige o falso cognato 'eventually'.");
add("I'll ask Freddie to make a smaller version just for you. He did mention he'd stop by your place eventually.\\r", "Vou pedir ao Freddie que faça uma versão menor só para você. Ele disse que passaria na sua casa uma hora dessas.\\r", "Corrige o falso cognato 'eventually'.");
add("Really? But if you treat them with a sincere heart, they'll eventually come to you.", "Sério? Mas, se tratar essas criaturas com carinho, um dia elas vão se aproximar de você.", "Corrige o falso cognato e evita um pronome sem referente claro.");
add("So eventually I picked it up myself, haha!", "No fim, aprendi por conta própria, haha!", "Corrige o falso cognato e mantém a frase neutra quanto ao gênero.");
add("Uncle Alvin says if you stick to the usual stuff, your customers will eventually grow tired of it!", "O tio Alvin diz que, se você ficar sempre no mesmo, com o tempo seus clientes vão se cansar!", "Corrige o falso cognato e naturaliza a expressão.");
add("When you do this work for hundreds of years, the materials eventually pile up into a mountain.", "Quando se faz esse trabalho por centenas de anos, com o tempo os materiais se acumulam até formar uma montanha.", "Corrige o falso cognato 'eventually'.");
add("Witches were free. And so, they lived to realize their own wishes.", "As bruxas eram livres. Assim, viviam para realizar os próprios desejos.", "Melhora tempo verbal, coesão e elimina repetição pronominal.");

add("...You sound really like a grown-up.", "...Você está falando como gente grande.", "Traduz 'sound like' pelo sentido contextual.");
add("(The bouncing of the quill sounds like bird chirping)", "(A pena quica com um som parecido com o canto de pássaros.)", "Descreve o som físico com naturalidade.");
add("(The pages rustle, sounds like leaves falling)", "(As páginas farfalham como folhas caindo.)", "Substitui o calque e usa o verbo adequado para páginas.");
add("[em1][lua(GetLocalizedString(\"Common\", \"BusStation\"))][/em1]... That sounds familiar...", "[em1][lua(GetLocalizedString(\"Common\", \"BusStation\"))][/em1]... Esse nome me parece familiar...", "Traduz 'sounds familiar' pelo sentido correto.");
add("[em1][lua(GetLocalizedString(\"Common\", \"WitchStation\"))][/em1]... That sounds familiar...", "[em1][lua(GetLocalizedString(\"Common\", \"WitchStation\"))][/em1]... Esse nome me parece familiar...", "Traduz 'sounds familiar' pelo sentido correto.");
add("[em1]The dessert contest[/em1]? That sounds familiar...", "[em1]O concurso de sobremesas[/em1]? Isso me parece familiar...", "Traduz 'sounds familiar' pelo sentido correto.");
add("A [em1]Cat Exercise Wheel[/em1]! Sounds cool, doesn't it?", "Uma [em1]Roda de Exercícios para Gatos[/em1]! Parece legal, não é?", "Remove o calque de 'sounds'.");
add("A phantom thief witch sounds cool!", "Uma bruxa ladra fantasma parece incrível!", "Remove o calque de 'sounds'.");
add("Alvin, when you say it like that, it just sounds like teasing.", "Alvin, quando você fala assim, parece provocação.", "Remove o calque de 'sounds like'.");
add("And the name \"Tanis\" sounds familiar...", "E o nome \"Tanis\" me parece familiar...", "Traduz 'sounds familiar' pelo sentido correto.");
add("Catching fish sounds cooler than eating them. ", "Pegar peixes parece mais legal do que comê-los.", "Remove o calque de 'sounds'.");
add("Enite, you don't sound like you're joking...", "Enite, não parece que você está brincando...", "Remove o calque de 'sound like'.");
add("Hmmm... Sounds like a riddle.", "Hmmm... Parece um enigma.", "Remove o calque de 'sounds like'.");
add("It's been very well preserved. Looks like something from very long ago... But the exterior's very clean and it sounds good.", "Está muito bem preservada. Parece ser muito antiga... Mas o exterior está bem limpo, e o som é bonito.", "O contexto mostra que Roy avalia uma caixa de música; preserva o sentido sonoro.");
add("Mm... that sounds complicated.", "Mm... isso parece complicado.", "Remove o calque de 'sounds'.");
add("Really? That sounds like a very convenient way to learn things. I want a marionette like this too.", "Sério? Parece uma forma muito conveniente de aprender. Também quero uma marionete assim.", "Remove o calque e a repetição de 'coisas'.");
add("Sounds like a guess.", "Parece um palpite.", "Remove o calque de 'sounds like'.");
add("Sounds like the prologue to a story where you awaken a terrible demon.", "Parece o prólogo de uma história em que você desperta um demônio terrível.", "Remove o calque e troca 'onde' por 'em que'.");
add("That doesn't sound quite logical...", "Isso não parece muito lógico...", "Remove o calque de 'sound'.");
add("That sounds familiar...", "Isso me parece familiar...", "Traduz 'sounds familiar' pelo sentido correto.");
add("That sounds like a tongue twister.", "Parece um trava-línguas.", "Remove o calque de 'sounds like'.");
add("That sounds more like a dragon.", "Isso parece mais um dragão.", "Remove o calque de 'sounds like'.");
add("That sounds ominous.", "Isso parece sinistro.", "Remove o calque de 'sounds'.");
add("That sounds ominous...", "Isso parece sinistro...", "Remove o calque de 'sounds'.");
add("That sounds... somewhat strange.", "Isso parece... um tanto estranho.", "Remove o calque de 'sounds'.");
add("This sounds complicated.", "Isso parece complicado.", "Remove o calque de 'sounds'.");
add("Virgil, you sound like the White Cat God.", "Virgil, você está falando igual ao Deus Gato Branco.", "Traduz 'sound like' pelo modo de falar.");
add("Well... It sounds nice, but it may change the materials' colors, so I need to do some testing.", "Bem... Parece uma boa ideia, mas pode mudar a cor dos materiais, então preciso fazer alguns testes.", "Traduz 'sounds nice' como avaliação de uma ideia.");
add("Whoa, that sounds just like the legends of flowers you told me about before!", "Uau, isso parece muito com as lendas sobre flores que você me contou!", "Remove o calque de 'sounds like'.");
add("Wow, that sounds like something out of a legend.", "Uau, isso parece ter saído de uma lenda.", "Remove o calque de 'sounds like'.");
add("Wow, that sounds unique and cool!", "Uau, parece diferente e legal!", "Naturaliza a avaliação sem traduzir 'unique' mecanicamente.");
add("Yeah, that definitely sounds like Clala's style.", "Sim, isso tem mesmo a cara da Clala.", "Usa uma expressão natural para estilo pessoal.");
add("Yeah! That sounds nice! Go ahead!", "Sim! Parece ótimo! Pode fazer!", "Theo aprova que Kyla faça o sofá; remove os calques de 'sounds' e 'go ahead'.");
add("You sound just like the Black Cat God...", "Você está falando igual ao Deus Gato Preto...", "Traduz 'sound like' pelo modo de falar.");

add("I need to check out the [em1]other floors[/em1].", "Preciso explorar os [em1]outros andares[/em1].", "Traduz 'check out' conforme a exploração do local.");
add("I'll check out Lisa's campsite first.", "Primeiro, vou dar uma olhada no acampamento da Lisa.", "Traduz 'check out' conforme a inspeção do local.");
add("I'll check out the portraits first.", "Primeiro, vou examinar os retratos.", "Traduz 'check out' conforme a inspeção dos retratos.");
add("If that doesn't work out, you'll have to check out the bookcases and shelves.", "Se isso não funcionar, você terá que procurar nas estantes e prateleiras.", "Traduz 'check out' conforme a busca por algo.");
add("Let's check out the [lua(GetLocalizedString(\"Map\", \"Museum_Brewing\"))] first.", "Vamos visitar primeiro o [lua(GetLocalizedString(\"Map\", \"Museum_Brewing\"))].", "Traduz 'check out' conforme a visita ao museu.");
add("Let's check out the [lua(GetLocalizedString(\"Map\", \"Museum_ThemeGreenForest\"))] first.", "Vamos visitar primeiro o [lua(GetLocalizedString(\"Map\", \"Museum_ThemeGreenForest\"))].", "Traduz 'check out' conforme a visita ao museu.");
add("Let's check out the place with the [em1]ladder[/em1] down there.", "Vamos investigar o lugar com a [em1]escada[/em1] lá embaixo.", "Traduz 'check out' conforme a investigação.");
add("Let's check out the place.", "Vamos investigar o lugar.", "Traduz 'check out' conforme a investigação.");
add("No, but we haven't checked out everywhere.", "Não, ainda não olhamos em todos os lugares.", "Naturaliza 'checked out' no contexto da busca.");

add("Even for an ordinary human to be able to read that much text in ancient witch language would shock the Witch Association.", "O fato de um humano comum conseguir ler tanto texto na língua antiga das bruxas chocaria a Associação das Bruxas.", "Remove a construção pesada com 'ser capaz de'.");
add("Good work. You'll be able to make more potions.", "Bom trabalho. Agora você poderá fazer mais poções.", "Simplifica a construção com 'ser capaz de'.");
add("I never thought you'd be able to recreate the potion from the [lua(GetLocalizedString(\"Common\", \"Common_Theme_StarSeaCave\"))].", "Nunca imaginei que você conseguiria recriar a poção da [lua(GetLocalizedString(\"Common\", \"Common_Theme_StarSeaCave\"))].", "Simplifica a construção com 'ser capaz de'.");
add("I tell you, that's a mythic book, said to be able to grant any wish.", "Pois saiba que esse é um livro mítico que, dizem, concede qualquer desejo.", "Remove a construção pesada com 'ser capaz de'.");
add("I won't be able to face her again if I keep living with a curse on me.", "Não conseguirei encará-la novamente se continuar vivendo sob uma maldição.", "Simplifica a construção e corrige a regência.");
add("It's my [em1]<wave>lifelong dream</wave>[/em1] to be able to breathe fire!", "Meu [em1]<wave>sonho de toda a vida</wave>[/em1] é poder soltar fogo!", "Simplifica a construção com 'ser capaz de'.");
add("Now that the [em1]Extractor[/em1] has been fixed, you'll be able to make potions from the [em1]basic recipes[/em1].", "Agora que o [em1]Extrator[/em1] foi consertado, você poderá preparar poções com as [em1]receitas básicas[/em1].", "Simplifica a construção e corrige a preposição.");
add("Shouldn't he be able to sense the noises?", "Ele não deveria perceber os barulhos?", "Simplifica a construção com 'ser capaz de'.");
add("The purpose is to encourage deliveries, so we need to make sure you are capable of deliveries.", "O objetivo é incentivar as entregas, então precisamos garantir que você consiga fazê-las.", "Remove repetição e construção mecânica.");
add("They keep saying I'm young and full of \"fresh ideas,\" so I should be able to top their old recipes.", "Vivem dizendo que sou jovem e cheia de \"ideias novas\", então devo conseguir superar as receitas antigas.", "Simplifica a construção e preserva o gênero da falante.");
add("To me, a witch should be able to handle many tasks, with many different solutions.", "Para mim, uma bruxa deve saber lidar com muitas tarefas e encontrar soluções diferentes.", "Remove repetição e construção pesada.");
add("Why are witches capable of so many things?", "Como as bruxas conseguem fazer tantas coisas?", "Naturaliza a pergunta.");
add("Will you be able to make new wines using these?", "Você vai conseguir fazer novos vinhos com isso?", "Naturaliza a pergunta.");
add("You’ll be able to make a potion if you have the ingredients.", "Você poderá preparar uma poção se tiver os ingredientes.", "Simplifica a construção com 'ser capaz de'.");
add("You've brought about countless miracles, but will you be able to turn the tides of a story already falling apart?", "Você realizou incontáveis milagres, mas será que consegue mudar o rumo de uma história que já está desmoronando?", "Naturaliza a pergunta e a metáfora.");

add("But there's no need to be stealthy. Just let me know when you want to get in.\\r", "Mas você não precisa agir às escondidas. É só me avisar quando quiser entrar.\\r", "Remove uma construção nominal pesada e evita gênero presumido.");
add("But there's no need to feel sad.", "Mas não precisa ficar triste.", "Naturaliza 'there's no need'.");
add("Honestly, I'm just an old man. There's no need to get everyone here so early to meet me.", "Sinceramente, sou só um velho. Não precisava reunir todo mundo tão cedo só para me conhecer.", "Naturaliza 'there's no need'.");
add("No need to overthink. Just follow your imagination.", "Não precisa pensar demais. É só usar a imaginação.", "Naturaliza a orientação.");
add("She said there's no need to feel shame about what the family did, but to record the true history and convey the truth.", "Ela disse que a família não precisava se envergonhar do que fez, mas sim registrar a história verdadeira e transmitir a verdade.", "Naturaliza a construção e explicita o sujeito já presente na fonte.");
add("There's no need to investigate the curse further.", "Não precisa continuar investigando a maldição.", "Naturaliza 'there's no need'.");
add("There's no need to put off your adventure. You can collect the items in your free time, and you always have my support!", "Não precisa adiar sua aventura. Você pode coletar os itens no tempo livre e sempre terá meu apoio!", "Naturaliza a construção e remove repetição pronominal.");
add("Yeah. No need to attract attention.", "É. Melhor não chamar atenção.", "Naturaliza a recomendação.");

add("It might help you in some way with what you two are doing.\\r", "Talvez isso ajude no que vocês estão fazendo.\\r", "Remove uma locução vaga desnecessária.");
add("And I somehow feel wronged...", "E sinto como se isso fosse injusto comigo...", "Naturaliza 'somehow' conforme o contexto emocional.");
add("And it somewhat makes you look cool.", "E ainda deixa você com um ar legal.", "Naturaliza 'somewhat' e evita repetição de 'parecer'.");
add("Arden seemed to be convinced somehow...", "Parece que o Arden se convenceu...", "Remove uma locução vaga desnecessária.");
add("But it somehow [em1]feels heartwarming[/em1].", "Mas isso [em1]aquece o coração[/em1].", "Substitui duas construções literais por uma expressão natural.");
add("Can I help in any way?", "Posso fazer algo para ajudar?", "Naturaliza a oferta de ajuda.");
add("Even though she's always smiling, she somehow always gives me the creeps.", "Mesmo sempre sorrindo, ela me dá arrepios.", "Remove advérbios redundantes.");
add("Good, I got out somehow.", "Ainda bem, consegui sair daqui.", "Naturaliza 'somehow' conforme o alívio expresso.");
add("Hmm... It looks somehow familiar. Where have I seen such a thing?", "Hmm... Isso me parece familiar. Onde já vi algo assim?", "Remove a locução vaga e naturaliza a pergunta.");
add("I see that Bjorn still remembers the way back here somehow.", "Pelo visto, Bjorn ainda se lembra do caminho de volta.", "Remove a locução vaga e o calque de 'I see'.");
add("In that case, you should somehow let the cats know that you are the one providing the fish.", "Nesse caso, você precisa dar um jeito de mostrar aos gatos que é você quem fornece o peixe.", "Traduz 'somehow' como busca de uma maneira concreta.");
add("It will work out somehow.", "No fim, vai dar certo.", "Naturaliza a expressão de confiança.");
add("Maybe it's the necklace... I somehow know it wants to return to the village.", "Talvez seja o colar... Tenho a impressão de que ele quer voltar para a vila.", "Naturaliza uma percepção incerta.");
add("Since it's a plant, the prickly vine and the core must be connected in some way.", "Como é uma planta, a vinha espinhosa e o núcleo devem ter algum tipo de ligação.", "Remove uma locução vaga.");
add("Then I need to somehow power my throw further.", "Então preciso encontrar um jeito de arremessar mais longe.", "Naturaliza a ação pretendida.");

add("But why are you so excited...?", "Mas por que você está tão animado...?", "Rex é o interlocutor masculino confirmado.");
add("Heh, I can't tease you when you're so sincerely worried about me.", "Hehe, não consigo provocar você quando está tão preocupada comigo de verdade.", "A fala é dirigida a Ellie.");
add("I'm sure you're curious about what I want to say... <shake>First of all, thank you!</shake>", "Tenho certeza de que você está curiosa para saber o que quero dizer... <shake>Antes de tudo, obrigado!</shake>", "Ellie é a interlocutora; o agradecimento continua masculino porque é dito por Rex.");
add("Oh... I suppose you're right.", "Ah... Acho que você está certa.", "A fala é dirigida a Ellie.");
add("So you're worried about Honey Bear.", "Então você está preocupada com o Ursinho de Mel.", "A fala é dirigida a Ellie.");
add("Welcome back.", "Bem-vinda de volta.", "A saudação de Roy é dirigida a Ellie.");
add("Welcome back. Have you got the feedback?", "Bem-vinda de volta. Conseguiu a opinião deles?", "A saudação é dirigida a Ellie e a pergunta foi naturalizada.");
add("Welcome to the Records Museum of Wisteria.", "Bem-vinda ao Museu dos Registros de Wisteria.", "A saudação é dirigida a Ellie.");
add("Welcome!", "Bem-vinda!", "A saudação de Rubrum é dirigida a Ellie.");
add("What, you scared? Cover your ears then, cuz I want to hear it.", "O quê, está assustada? Então tape os ouvidos, porque eu quero ouvir.", "Virgil fala com Ellie.");
add("You're right, and this very book has been cursed.", "Você está certa, e este mesmo livro foi amaldiçoado.", "Aurea fala com Ellie.");
add("You're right. I've got nothing left to be afraid of. Let's do it.", "Você está certa. Não tenho mais nada a temer. Vamos fazer isso.", "Clala responde a Ellie apesar do metadado interno ambíguo.");
add("You're right. This can be dangerous.", "Você está certa. Isso pode ser perigoso.", "Kyla fala com Ellie.");

add("And you can find such a creative application for [lua(GetLocalizedString(\"Item\", \"NoiseCandy_Name\"))]. I'm impressed.", "Você encontrou um uso muito criativo para [lua(GetLocalizedString(\"Item\", \"NoiseCandy_Name\"))]. Estou impressionada.", "Naturaliza 'creative application' e corrige o gênero de Arin.");
add("I worry that I was too harsh on him.", "Estou preocupada por ter sido severa demais com ele.", "Corrige as duas flexões referentes a Enite.");
add("Thank you, as always. Do be careful.", "Obrigada, como sempre. Tome cuidado.", "Corrige o gênero de Enite sem presumir gênero do destinatário.");
add("N-No, thank you. I can't handle bitter things... Haha.", "N-Não, obrigada. Não aguento coisas amargas... Haha.", "Corrige o gênero de Ellie e remove uma escolha lexical mecânica.");

add("Brad's pranks haven't changed at all. Let me see them.", "As pegadinhas do Brad continuam as mesmas. Quero vê-las.", "Corrige a tradução literal de ambas as orações.");
add("Are you heading to the village right away? Let me walk you there.\\r", "Está indo para a vila agora? Vou com você até lá.\\r", "Naturaliza 'let me' e evita pronome com gênero presumido.");
add("Emm... There're some strange plants around here. Let me see which ones can be used for bookmarks.", "Hmm... Há algumas plantas estranhas por aqui. Vou ver quais podem ser usadas como marcadores de página.", "Naturaliza 'let me' e esclarece 'bookmarks'.");
add("Let me put it back on you.", "Vou colocá-lo de volta em você.", "Ellie recoloca o Símbolo de Amizade em Virgil; remove a construção artificial.");
add("Let me see. \"[em1]Ellie's donut[/em1] perfectly captures her personality.\"", "Vamos ver. \"[em1]O donut da Ellie[/em1] representa perfeitamente a personalidade dela.\"", "Traduz o trecho que permaneceu em inglês e naturaliza a frase.");
add("Let me see... A sweet wine... That would be [em1][lua(GetLocalizedString(\"Item\", \"Cranapple_Name\"))][/em1].", "Vamos ver... Um vinho doce... Então seria [em1][lua(GetLocalizedString(\"Item\", \"Cranapple_Name\"))][/em1].", "Naturaliza a fala de raciocínio.");
add("Let me tell you, Ellie. That's because you never know what you will run into during an exploration.", "É que nunca se sabe o que pode aparecer durante uma exploração, Ellie.", "Remove o calque de 'let me tell you'.");
add("Let me tell you. There are also potions that make you smart.", "Pois saiba que também existem poções que deixam a pessoa mais inteligente.", "Remove o calque e evita pronome genérico.");
add("Me neither. Anyway, let me [em1]deliver the donuts to Roy first[/em1].", "Eu também não. Enfim, primeiro vou [em1]entregar os donuts ao Roy[/em1].", "Naturaliza 'let me'.");
add("Oh, Ellie. Let me talk to you for a minute before you go.", "Ah, Ellie. Preciso falar com você antes que vá embora.", "Remove a construção artificial e a repetição de 'você'.");
add("Since Kyla is responsible for repairing the stage, let me go ask her first.", "Já que a Kyla é responsável pelo conserto do palco, vou perguntar a ela primeiro.", "Naturaliza a fala e evita repetição de verbos.");
add("Wait a minute. Let me check my memo.", "Um minuto. Vou conferir minhas anotações.", "Naturaliza 'let me' e a escolha lexical.");
add("Well then, let me see, let's eat some drinking snacks then.", "Bem... então vamos comer alguns petiscos.", "Remove redundância e uma tradução literal sem sentido.");

add("I've left the [em1]Compendium of Legends[/em1] in my flower shop. Feel free to take a look anytime.", "Deixei o [em1]Compêndio de Lendas[/em1] na minha floricultura. Você pode consultá-lo quando quiser.", "Remove os calques de 'feel free' e 'take a look'.");
add("If I find it, be sure to come take a look.", "Se eu encontrar, não deixe de vir ver.", "Naturaliza o convite.");
add("If you're lucky, you might occasionally find some [em1]rare furnishings[/em1], so be sure to come take a look often.", "Se tiver sorte, talvez encontre [em1]móveis raros[/em1] de vez em quando, então passe por aqui com frequência para conferir.", "Naturaliza a frase e remove advérbios redundantes.");
add("People said that he's never at home at [em1]night[/em1]. Let's take a look inside during that time.", "Diziam que ele nunca fica em casa à [em1]noite[/em1]. Vamos entrar nesse horário.", "Corrige tempo verbal e naturaliza a sugestão.");

add("I see. You really do look like you're enjoying yourself.", "Entendo. Você realmente parece estar se divertindo.", "Traduz 'I see' como marcador discursivo.");
add("I see. But why do you need a Glass Bottle?", "Entendo. Mas por que você precisa de uma garrafa de vidro?", "Traduz 'I see' como marcador discursivo.");
add("I see. It's my first time heading this way, so I didn't know.", "Entendi. É a primeira vez que venho por aqui, então não sabia.", "Traduz 'I see' como marcador discursivo e naturaliza o deslocamento.");
add("I see. Do you want another cupcake?", "Entendi. Quer outro bolinho?", "Traduz 'I see' como marcador discursivo e remove pronome desnecessário.");
add("First thing’s first, let’s get the [em1]Recipe[/em1].", "Primeiro, vamos pegar a [em1]Receita[/em1].", "Naturaliza a expressão introdutória.");
add("First things first. Let's get Rubrum his toy back.", "Antes de tudo, vamos devolver o brinquedo do Rubrum.", "Naturaliza a expressão introdutória.");
add("What! Why are you staring at me like that!", "O QUÊ?! Por que está me olhando assim?!", "Corrige pontuação e naturaliza a reação.");
add("What! I'm so jealous! I wish I had a broom.", "O quê?! Que inveja! Queria ter uma vassoura.", "Corrige pontuação e remove tradução mecânica.");
add("<shake>What!?</shake> Are you actually reluctant to follow such an honorable cause of wonders with me!?", "<shake>O quê?!</shake> Você realmente não quer me acompanhar numa causa tão nobre e maravilhosa?!", "Corrige pontuação e naturaliza a pergunta.");
add("A blue rose... a blue rose... It rings a bell...", "Uma rosa azul... uma rosa azul... Isso me parece familiar...", "Traduz a expressão idiomática pelo sentido.");
add("Copycat... Marionettes? That rings a bell... Oh, I've probably heard about them in the broom lessons.", "Marionetes... imitadoras? Isso me parece familiar... Ah, provavelmente ouvi falar delas nas aulas de vassoura.", "Traduz a expressão idiomática pelo sentido.");
add("Well, let's see. Those fellows usually prefer [em1]large trees[/em1] or [em1]old caves[/em1]. It would do you well to search there.", "Bem, vamos ver. Essas criaturas costumam preferir [em1]árvores grandes[/em1] ou [em1]cavernas antigas[/em1]. Vale a pena procurar nesses lugares.", "Remove uma construção literal e formal demais.");
add("Don't go in someone else's room again like yesterday.", "Não volte a entrar no quarto de outra pessoa, como fez ontem.", "Corrige a ordem e a referência temporal.");
add("It looks ordinary. I don't think it does anything unusual.", "Parece comum. Acho que não faz nada de especial.", "Corrige o falso sentido de 'ordinária'.");
add("Everything must be recorded! Bring us everything! Intactly! <shake>And at top speed!</shake>", "Tudo deve ser registrado! Traga tudo para nós! Inteiro! <shake>E o mais rápido possível!</shake>", "Corrige concordância com 'tudo' e mantém o ritmo enfático.");
add("It's okay. My highest delivery record at Highlion was ten trees.", "Tudo bem. Meu maior recorde de entregas em Highlion foi de dez árvores.", "Corrige uma construção nominal traduzida literalmente.");
add("According to what we currently know about the books, this witch named Lisa...", "Até onde sabemos pelos livros, essa bruxa chamada Lisa...", "Naturaliza a introdução da informação.");

add("<wave>Take your time to make your decision.</wave> I look forward to hearing your answer tomorrow.", "<wave>Pense com calma antes de decidir.</wave> Aguardo sua resposta amanhã.", "Remove o calque de 'take your time' e evita presumir o gênero de Laurel.");
add("Sure. I'm the one asking for a favor. Take your time.", "Claro. Sou eu que estou pedindo um favor. Não tenha pressa.", "Remove o calque de 'take your time'.");
add("Take your time. You'll [em1]need a recipe[/em1] if you want to actually make a sample.", "Sem pressa. Você [em1]precisará de uma receita[/em1] se quiser preparar uma amostra de verdade.", "Remove o calque de 'take your time'.");
add("I have no idea what you're up to, but take your time. There's no need to rush.", "Não faço ideia do que você está tramando, mas faça no seu tempo. Não precisa ter pressa.", "Remove o calque e a repetição sobre pressa.");
add("Maven Ostyr. It doesn't ring a bell.", "Maven Ostyr. Esse nome não me parece familiar.", "Traduz a expressão idiomática pelo sentido.");
add("Doesn't ring a bell. I don't think that's a witch or a school staff member.", "Não me parece familiar. Acho que não é uma bruxa nem alguém da equipe da escola.", "Traduz a expressão idiomática e evita gênero genérico.");

add("It's hard for me to go and see you, Ms. Witch. Thank you for visiting me often.", "Tenho dificuldade para ir vê-la, Srta. Bruxa. Obrigada por me visitar com frequência.", "Naturaliza a regência e preserva a flexão confirmada de Enite.");
add("Ah, if Dana is going, perhaps you might also consider inviting Clala.", "Ah, se a Dana for, talvez você também possa convidar a Clala.", "Corrige a conjugação condicional e naturaliza a sugestão.");
add("Maybe the reason that he can't live in the village is because he's too into fishing?", "Talvez ele não consiga morar na vila por gostar demais de pescar?", "Corrige o uso do subjuntivo e remove uma construção causal redundante.");
add("Witches can enter dreams, right? I wondered if maybe I could too.\\r", "As bruxas podem entrar em sonhos, não é? Fiquei pensando se eu também conseguiria.\\r", "Remove o calque de 'I wondered' e melhora a correlação verbal.");
add("But once I take this, there's really no turning back!", "Mas, depois que eu pegar isso, não tem volta!", "Corrige a oração temporal e remove uma formulação literal.");

add("I admit it. Ellie Blueriver, <wave>I'm impressed by your skills.</wave> You're now a member of my Records Museum.", "Admito. Ellie Blueriver, <wave>suas habilidades me impressionaram.</wave> Agora você faz parte do meu Museu dos Registros.", "Evita presumir o gênero de Laurel e naturaliza a admissão.");
add("Staring at the same candies and potions day after day... I've grown tired of them.", "Olhar para os mesmos doces e poções todos os dias... Já me cansei disso.", "Evita presumir o gênero de Laurel.");
add("I'm eager to see where our partnership takes us, Ellie.", "Mal posso esperar para ver aonde nossa parceria vai nos levar, Ellie.", "Evita presumir o gênero do Deus Gato Branco.");
add("Looking forward to your progress at the [lua(GetLocalizedString(\"Common\", \"Common_Theme_StarSeaCave\"))].", "Quero ver seu progresso na [lua(GetLocalizedString(\"Common\", \"Common_Theme_StarSeaCave\"))].", "Evita presumir o gênero de Baobab.");
add("I don't feel lonely now, because I've got Arden. I hope the Flower of Love feels the same.", "Agora não sinto solidão, porque tenho Arden. Espero que a Flor do Amor sinta o mesmo.", "Evita atribuir gênero a uma narração sem ator identificado.");

add("If Rex is an explorer, are you also an explorer?", "Se Rex é explorador, você também é exploradora?", "Vinch dirige a pergunta a Ellie.");
add("Nice idea. You're a genius, Ellie.", "Boa ideia. Você é genial, Ellie.", "Evita o substantivo masculino ao elogiar Ellie.");
add("Ellie... You must be a genius!", "Ellie... Você só pode ser genial!", "Evita o substantivo masculino ao elogiar Ellie.");
add("So... were you a human to begin with?", "Então... você era humana desde o começo?", "Ellie dirige a pergunta a Lisa.");
add("You're always so encouraging.", "Você é sempre tão encorajadora.", "Clala dirige a fala a Ellie.");
add("But look at the dishes you cooked today. You've become a real chef.", "Mas veja os pratos que você preparou hoje. Já cozinha como gente profissional.", "Naturaliza a frase sem presumir o gênero de Brave.");
add("The one who created you, [em1]Pax[/em1]... what truths were you instructed to protect, and when were you commanded to remain silent?", "A pessoa que criou você, [em1]Pax[/em1]... que verdades você recebeu a instrução de proteger e quando recebeu a ordem de permanecer em silêncio?", "Evita atribuir gênero ao Guardião Silencioso.");
add("But it's really a problem I should solve myself. Please don't let me take up your valuable time, heh.", "Mas é um problema que devo resolver sozinha. Não quero ocupar seu tempo precioso, hehe.", "Remove o calque de 'take up your valuable time' e a repetição de 'realmente'.");

function replaceWord(text, from, to) {
  return text.replace(new RegExp(`(?<!\\p{L})${from}(?!\\p{L})`, "giu"), (match) => {
    if (match === match.toUpperCase()) return to.toUpperCase();
    if (match[0] === match[0].toUpperCase()) return to[0].toUpperCase() + to.slice(1);
    return to;
  });
}

function flexGender(text, gender) {
  let result = text;
  for (const [masculine, feminine] of GENDER_PAIRS) {
    result = gender === "feminino"
      ? replaceWord(result, masculine, feminine)
      : replaceWord(result, feminine, masculine);
  }
  return result;
}

function technicalTokens(text) {
  return [
    ...(text.match(/\[(?:\/?em\d+|lua\([^\]]+\))\]/g) || []),
    ...(text.match(/<\/?[A-Za-z][^>]*>/g) || []),
    ...(text.match(/\\r/g) || [])
  ];
}

function assertTechnicalTokens(source, target) {
  const sourceTokens = technicalTokens(source);
  const targetTokens = technicalTokens(target);
  if (JSON.stringify(sourceTokens) !== JSON.stringify(targetTokens)) {
    throw new Error(`Tokens técnicos alterados em: ${source}\nFonte: ${sourceTokens}\nAlvo: ${targetTokens}`);
  }
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function main() {
  if (!fs.existsSync(BACKUP_MEMORY)) fs.copyFileSync(MEMORY_PATH, BACKUP_MEMORY);
  if (!fs.existsSync(BACKUP_TRANSLATOR)) fs.copyFileSync(TRANSLATOR_PATH, BACKUP_TRANSLATOR);

  const memory = JSON.parse(fs.readFileSync(MEMORY_PATH, "utf8"));
  const translator = JSON.parse(fs.readFileSync(TRANSLATOR_PATH, "utf8"));
  const baselineMemory = JSON.parse(fs.readFileSync(BACKUP_MEMORY, "utf8"));
  const baselineTranslator = JSON.parse(fs.readFileSync(BACKUP_TRANSLATOR, "utf8"));
  const audit = JSON.parse(fs.readFileSync(AUDIT_PATH, "utf8"));
  const contextIndex = JSON.parse(fs.readFileSync(CONTEXT_PATH, "utf8"));
  const pending = new Map();

  for (const item of audit.items) {
    if (!item.reasons.some((reason) => reason.id === "verified_actor_gender_mismatch")) continue;
    if (GENDER_EXCLUSIONS.has(item.source)) continue;
    const actors = [...new Set(item.contexts.map((context) => context.actorName).filter(Boolean))];
    if (actors.length !== 1 || !VERIFIED_ACTOR_GENDER[actors[0]]) continue;
    const target = flexGender(memory[item.source], VERIFIED_ACTOR_GENDER[actors[0]]);
    if (target !== memory[item.source]) {
      pending.set(item.source, {
        target,
        reasons: [`Corrige a flexão de primeira pessoa de ${actors[0]} (${VERIFIED_ACTOR_GENDER[actors[0]]}).`]
      });
    }
  }

  const missing = [];
  for (const [source, correction] of manual) {
    if (!Object.prototype.hasOwnProperty.call(memory, source)) {
      missing.push(source);
      continue;
    }
    const existing = pending.get(source);
    pending.set(source, {
      target: correction.target,
      reasons: [...(existing?.reasons || []), correction.reason]
    });
  }
  if (missing.length) {
    throw new Error(`Chaves manuais ausentes na memória (${missing.length}):\n${missing.join("\n")}`);
  }

  const changes = [];
  for (const [source, correction] of pending) {
    const before = memory[source];
    const after = correction.target;
    if (before === after) continue;
    assertTechnicalTokens(source, after);
    const contexts = audit.items.find((item) => item.source === source)?.contexts || [];
    const inTranslatorMemory = Object.prototype.hasOwnProperty.call(translator, source);
    memory[source] = after;
    changes.push({ source, before, after, reasons: correction.reasons, inTranslatorMemory, contexts });
  }

  writeJson(MEMORY_PATH, memory);

  const cumulativeChanges = [];
  for (const [source, after] of Object.entries(memory)) {
    const before = baselineMemory[source];
    if (before === undefined || before === after) continue;
    const contexts = contextIndex.contexts[source] || [];
    const reasons = [];
    const correction = manual.get(source);
    if (correction) reasons.push(correction.reason);
    const actors = [...new Set(contexts.map((context) => context.actorName).filter(Boolean))];
    if (!correction && actors.length === 1 && VERIFIED_ACTOR_GENDER[actors[0]]) {
      reasons.push(`Corrige a flexão de primeira pessoa de ${actors[0]} (${VERIFIED_ACTOR_GENDER[actors[0]]}).`);
    }
    cumulativeChanges.push({
      source,
      before,
      after,
      reasons: reasons.length ? reasons : ["Correção linguística revisada."],
      inTranslatorMemory: Object.prototype.hasOwnProperty.call(baselineTranslator, source),
      contexts
    });
  }

  const report = {
    generatedAt: new Date().toISOString(),
    files: { memory: MEMORY_PATH, translator: TRANSLATOR_PATH },
    backups: { memory: BACKUP_MEMORY, translator: BACKUP_TRANSLATOR },
    totals: {
      manualCorrectionsReviewed: manual.size,
      changesApplied: cumulativeChanges.length,
      changesAppliedThisRun: changes.length,
      translatorEntriesUpdated: 0,
      genderCandidatesExcludedAsQuotedSpeech: GENDER_EXCLUSIONS.size
    },
    changes: cumulativeChanges
  };
  writeJson(REPORT_PATH, report);
  console.log(JSON.stringify(report.totals, null, 2));
}

main();
