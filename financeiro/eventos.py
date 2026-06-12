"""Calendário 2026 dos eventos da FPS (datas exatas + tier).

Usado para SUGERIR o evento de cada lançamento do extrato:
- Despesas de torneio: pela proximidade da data.
- Inscrições (receitas): pelo valor (que indica o tier) + a data mais próxima.
  Obs.: R$ 200 pode ser Gold OU Junior XP — por isso os dois entram como candidatos.
"""

from datetime import date

# (nome do evento, data inicial, data final, tier)
EVENTOS = [
    ("CAY Open", date(2026, 2, 25), date(2026, 3, 1), "Gold"),
    ("CI&T", date(2026, 3, 6), date(2026, 3, 8), "Interior"),
    ("Junior Experience com Julio Caseiro", date(2026, 3, 8), date(2026, 3, 8), "Junior XP"),
    ("Squash Wall", date(2026, 3, 10), date(2026, 3, 15), "Gold"),
    ("RGSA Juniors", date(2026, 3, 20), date(2026, 3, 22), "Juvenil"),
    ("SquaSHE Bio por Cento", date(2026, 3, 22), date(2026, 3, 22), "SquaSHE"),
    ("Ilhabela", date(2026, 3, 28), date(2026, 3, 29), "Platinum"),
    ("Junior Experience com Rafael Alarcon", date(2026, 4, 4), date(2026, 4, 4), "Junior XP"),
    ("Bio por Cento", date(2026, 4, 9), date(2026, 4, 12), "Gold"),
    ("Armada Asset", date(2026, 4, 24), date(2026, 4, 26), "Interior"),
    ("SquaSHE Squash Wall", date(2026, 4, 25), date(2026, 4, 25), "SquaSHE"),
    ("CAY Juniors", date(2026, 5, 8), date(2026, 5, 10), "Juvenil"),
    ("Junior Experience com Diego Gobbi", date(2026, 5, 16), date(2026, 5, 16), "Junior XP"),
    ("ECP", date(2026, 5, 18), date(2026, 5, 24), "Platinum"),
    ("Porto Ferreira", date(2026, 5, 29), date(2026, 5, 31), "Interior"),
    ("Ipê Clube Juniors", date(2026, 6, 12), date(2026, 6, 14), "Juvenil"),
    ("SquaSHE SPAC", date(2026, 6, 21), date(2026, 6, 21), "SquaSHE"),
]

NOMES_EVENTOS = [e[0] for e in EVENTOS]

# Valor da inscrição -> tier do torneio (filiado / não filiado).
TIER_VALORES = {
    "Gold": {200, 300},
    "Platinum": {220, 320},
    "Interior": {160, 260},
    "Juvenil": {80, 180, 260},  # 80 iniciante · 180 filiado · 260 não filiado
    "SquaSHE": {85, 125},
    "Junior XP": {200},
}


def _dist(d, ini, fim):
    """Distância (em dias) de uma data até a janela [ini, fim]; 0 se estiver dentro."""
    if d < ini:
        return (ini - d).days
    if d > fim:
        return (d - fim).days
    return 0


def sugerir_evento(data, valor, tipo, grupo, categoria=""):
    """Sugere (evento, motivo) para um lançamento, ou (None, None) se não der."""
    if not data:
        return None, None

    if tipo == "receita":
        chave = int(round(abs(float(valor))))
        tiers = [t for t, vals in TIER_VALORES.items() if chave in vals]
        cands = [e for e in EVENTOS if e[3] in tiers]
        if not cands:
            return None, None
        nome, ini, fim, tier = min(cands, key=lambda e: _dist(data, e[1], e[2]))
        d = _dist(data, ini, fim)
        if d > 45:
            return None, None
        return nome, f"inscrição R$ {chave} · {tier} · {d}d do evento"

    # despesa: só faz sentido para gastos de torneio
    if grupo != "Torneios":
        return None, None
    cands = EVENTOS
    if "Junior XP" in (categoria or ""):
        cands = [e for e in EVENTOS if e[3] == "Junior XP"]
    nome, ini, fim, tier = min(cands, key=lambda e: _dist(data, e[1], e[2]))
    d = _dist(data, ini, fim)
    if d > 21:
        return None, None
    return nome, f"despesa a {d}d do evento"
