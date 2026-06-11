"""Motor de categorização dos lançamentos do extrato, segundo as regras da FPS.

Heurística por nome/valor. O que não for reconhecido fica como "a classificar"
para o Vinicius revisar — e vira regra nova aqui. Algumas regras já vinculam
o lançamento a um EVENTO (ex.: estrutura/repasses de cada torneio).
"""

import unicodedata


def _norm(s):
    s = (s or "").upper()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _contem(texto, lista):
    return any(frag in texto for frag in lista)


# Árbitros — fragmentos distintivos do nome
ARBITROS = [
    "KALINA", "CARECHO", "MANTOVANI", "ARROYO", "BATAGLIA", "YAMANAKA",
    "LINCOLN ALVES", "DEALIS", "PAULO MUNIZ", "RICARDO COSTA", "FREIRE COSTA",
    "MATHIESON", "RICARDO PARDO", "ALISON", "MAURICIO CARVALHO", "MAGNANI",
    "MAURO CONSTANTINO", "GRACIANO", "ACANGELI", "CYRILLO", "JURANDIR",
    "J & C SOARES", "SOARES ROSA", "DIEGUES",
]

# Junior XP / Junior Experience — instrutores que recebem
JUNIOR_XP = [
    "CASEIRO", "ALARCON", "GOBBI", "GUI MELO",
    "NOVACK", "MOMETTO", "MURILO FERNANDES", "GALLEGO",
]

# Regras de DESPESA por nome: (fragmentos, grupo, categoria, evento)
REGRAS_DESPESA = [
    (ARBITROS, "Torneios", "Arbitragem", ""),
    (["NA LATA SQUASH"], "Torneios", "Transmissão", ""),
    (JUNIOR_XP, "Torneios", "Junior XP", ""),
    (["COOL CAMISETAS", "PAAMA", "SERGIO TIEPP"], "Torneios", "Camisetas", ""),
    (["3D TROFEU", "JETPRINT", "METALURGICA SPORT", "JETSAND"], "Torneios", "Troféus", ""),
    (["DIFERENCIAL"], "Torneios", "Gráfica e adesivagem", ""),
    (["FUND ANGLO", "MARINA PORTO ILHABELA", "MARINAUTICA", "ELAINE ELOI", "ELAINE CABRAL",
      "PAULUS", "ATELIE", "MARSIL", "MODENA"],
     "Torneios", "Estrutura e quadra de vidro", "Ilhabela Open"),
    (["SOCIEDADE CULTURAL DE PORTO FERREIRA"], "Torneios", "Repasse a promotor", "Porto Ferreira Open"),
    (["ACADEMIA BIO POR CENTO"], "Torneios", "Repasse a promotor", "Bio por Cento Open"),
    (["JOSAFA"], "Torneios", "Repasse a promotor", "CI&T Open"),
    (["LUIS GUSTAVO"], "Torneios", "Repasse a promotor", "ECP Open"),
    (["FERNANDA PEREIRA"], "Torneios", "Staff", "ECP Open"),
    (["SOCIEDADE HIPICA", "HIPICA DE CAMPINAS"], "Torneios", "Estrutura / sede", "Hípica de Campinas"),
    (["MAURICIO DE CAMARGO"], "Torneios", "Repasse a promotor", "CAY Juniors"),
    (["RHUAN"], "Torneios", "Exibição", "Indaiatuba Clube Open"),
    (["GABRIELLA CRISTINA", "GARBIM"], "Torneios", "Fotografia", ""),
    (["FAMIGLIA MANZOLI", "RESTAURANTENOSU", "RESTAURANTE"], "Despesas gerais", "Alimentação", ""),
    (["MONICA CRISTINA AMADOR", "PELLIZER"], "Despesas gerais", "Devolução", ""),
    (["EDIN"], "Despesas gerais", "Zeladoria", ""),
    (["YAPAY"], "Despesas gerais", "Taxas Vindi/Yapay", ""),
    (["CONFEDERACAO BRASILEIRA", "CBS"], "Despesas gerais", "Taxa Confederação (CBS)", ""),
    (["VENTURA"], "Despesas gerais", "Contabilidade", ""),
    (["SIOUX"], "Despesas gerais", "Tecnologia / Site", ""),
    (["SQUASH WALL"], "Despesas gerais", "Aluguel (sede e quadra)", ""),
]

# Regras de RECEITA por nome: (fragmentos, grupo, categoria, evento)
REGRAS_RECEITA = [
    (["EURO IMPORT"], "Patrocínios", "Patrocínio", "Ilhabela Open"),
    (["ZBRA", "ROADCARD", "NUTRILATINO", "FAUSTO", "TEPATRI", "PAULO ERNANI"], "Patrocínios", "Patrocínio", "ECP Open"),
    (["RICARDO PARDO"], "Inscrições", "Inscrição (família)", ""),
]

# Receitas por valor (PIX recebido de inscrições)
INSCRICOES = {
    80: ("Inscrições", "Juvenil iniciante"),
    160: ("Inscrições", "Interior"),
    260: ("Inscrições", "Interior (2 categorias / não filiado)"),
    180: ("Inscrições", "Evento juvenil"),
    200: ("Inscrições", "Gold / Junior XP"),
    300: ("Inscrições", "Gold (não filiado)"),
    220: ("Inscrições", "Platinum"),
    320: ("Inscrições", "Platinum (não filiado)"),
    85: ("SquaSHE", "SquaSHE"),
    125: ("SquaSHE", "SquaSHE"),
}


def classificar(descricao, razao, valor):
    """Retorna (tipo, grupo, categoria, evento). grupo vazio = 'a classificar'."""
    d = _norm(descricao)
    r = _norm(razao)
    alvo = (r + " " + d).strip()
    valor = float(valor)
    tipo = "receita" if valor > 0 else "despesa"

    # Movimentações financeiras (não operacional)
    if _contem(d, ["APLICACAO", "RESGATE", "RENDIMENTO", "RFSIMP", "FUNDO", "POUPANCA", "CDB"]):
        return (tipo, "Financeiro (não operacional)", "Aplicação / resgate / rendimento", "")

    if valor < 0:  # ===== DESPESA =====
        # Galvão / Berbel / Duran: R$ 4.000 = Folha; demais valores = torneio/evento.
        if "GALVAO" in alvo:
            if abs(valor) == 4000:
                return ("despesa", "Folha", "Squash Talks", "")
            return ("despesa", "Torneios", "Squash Talks (evento)", "")
        if "VINICIUS TORRES BERBEL" in alvo:
            if abs(valor) == 4000:
                return ("despesa", "Folha", "Vinicius Berbel", "")
            return ("despesa", "Torneios", "Produção e comunicação", "")
        if "DURAN COMUNICAC" in alvo:
            if abs(valor) == 4000:
                return ("despesa", "Folha", "Aline Rocha", "")
            return ("despesa", "Torneios", "Produção e comunicação", "")
        for frags, grupo, cat, evento in REGRAS_DESPESA:
            if _contem(alvo, frags):
                return ("despesa", grupo, cat, evento)
        if "BUSINESS" in d:
            return ("despesa", "Despesas gerais", "Cartão de crédito", "")
        if "SAQUE" in d:
            return ("despesa", "Despesas gerais", "Saque", "")
        if d.startswith("TAR") or "TARIFA" in d or d.startswith("IOF"):
            return ("despesa", "Despesas gerais", "Tarifas bancárias", "")
        return ("despesa", "", "", "")

    # ===== RECEITA =====
    for frags, grupo, cat, evento in REGRAS_RECEITA:
        if _contem(alvo, frags):
            return ("receita", grupo, cat, evento)
    if "YAPAY" in alvo or ("SISPAG" in d and ("MAST" in d or "VISA" in d)):
        return ("receita", "Cartão/Vindi", "Cartão (Yapay)", "")
    chave = int(round(valor))
    if chave in INSCRICOES:
        grupo, cat = INSCRICOES[chave]
        return ("receita", grupo, cat, "")
    if "BOLETO" in d:
        return ("receita", "Filiação", "Filiação de clubes (boleto - verificar)", "")
    return ("receita", "", "", "")
