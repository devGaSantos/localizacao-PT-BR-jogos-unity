import os
import re

input_folder = "exportados"
report_folder = "relatorios"

os.makedirs(report_folder, exist_ok=True)

type_string = "CustomFieldType_Localization"

title_pattern = re.compile(r'\s*\d+\s+string\s+title\s*=\s*"([^"]*)"')
value_pattern = re.compile(r'\s*\d+\s+string\s+value\s*=\s*"(.*)"')
type_pattern = re.compile(r'\s*\d+\s+string\s+typeString\s*=\s*"([^"]*)"')

arquivos = [
    f for f in os.listdir(input_folder)
    if f.lower().endswith(".txt")
]

mantidos = 0
apagados = 0

print(f"📂 Arquivos encontrados: {len(arquivos)}")


# =========================
# VALIDAÇÃO DO TEXTO
# =========================

def texto_valido(texto):
    if not texto:
        return False

    texto = texto.strip()

    if texto == "":
        return False

    if re.fullmatch(r'[-._\s]+', texto):
        return False

    if not re.search(r'[A-Za-z]', texto):
        return False

    return True


# =========================
# VALIDAÇÃO DO BLOCO
# =========================

def analisar_bloco(bloco):
    title = None
    is_localization = False
    texto = None

    for linha in bloco:
        t_match = title_pattern.match(linha)
        if t_match:
            title = t_match.group(1)

        v_match = value_pattern.match(linha)
        if v_match:
            texto = v_match.group(1)

        type_match = type_pattern.match(linha)
        if type_match and type_match.group(1) == type_string:
            is_localization = True

    valido = (
        title == "en"
        and is_localization
        and texto_valido(texto)
    )

    return valido, title, texto


# =========================
# PROCESSAMENTO
# =========================

for arquivo in arquivos:
    caminho = os.path.join(input_folder, arquivo)
    report_path = os.path.join(report_folder, f"RELATORIO - {arquivo}")

    try:
        with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
            linhas = f.readlines()

        bloco = []
        dentro = False

        encontrou_valido = False
        registros = []

        for linha in linhas:

            if re.match(r'\s*\d+\s+Field\s+data\s*$', linha):
                bloco = [linha]
                dentro = True
                continue

            if dentro:
                bloco.append(linha)

                if re.match(r'\s*\[\d+\]\s*$', linha):
                    valido, title, texto = analisar_bloco(bloco)

                    if valido:
                        encontrou_valido = True
                        registros.append(f"[OK] title={title} | value={texto}")
                    else:
                        registros.append(f"[IGNORADO] title={title} | value={texto}")

                    dentro = False

        if dentro:
            valido, title, texto = analisar_bloco(bloco)
            if valido:
                encontrou_valido = True
                registros.append(f"[OK] title={title} | value={texto}")
            else:
                registros.append(f"[IGNORADO] title={title} | value={texto}")

        # =========================
        # ESCREVE RELATÓRIO
        # =========================

        with open(report_path, "w", encoding="utf-8") as r:
            r.write(f"Arquivo: {arquivo}\n")
            r.write("=" * 60 + "\n")

            for linha in registros:
                r.write(linha + "\n")

        # =========================
        # DECISÃO DE APAGAR
        # =========================

        if encontrou_valido:
            mantidos += 1
            print(f"✅ Mantido: {arquivo}")
        else:
            os.remove(caminho)
            apagados += 1
            print(f"🗑️ Apagado: {arquivo}")

    except Exception as e:
        print(f"⚠️ Erro em {arquivo}: {e}")

print("\n🔥 Limpeza concluída!")
print(f"✅ Mantidos: {mantidos}")
print(f"🗑️ Apagados: {apagados}")