"""Taxonomia de categorias/subcategorias da Base Financeira.

Editável aqui (config única, não hardcoded nas telas). Depois pode virar um
modelo com CRUD pelo usuário. As opções variam por tipo (receita × despesa).
"""

CATEGORIAS = {
    "receita": ["Eventos", "Filiações", "Vendas", "Clubes", "Patrocínios", "Rendimentos"],
    "despesa": ["Folha", "Administrativos", "Eventos", "Cartão", "Devoluções", "Impostos"],
}

SUBCATEGORIAS = {
    "receita": ["Inscrições"],
    "despesa": ["Arbitragem", "Transmissão", "Cobertura", "Promotor", "Camisetas",
                "Troféus", "Recepção", "Premiação", "Site", "Tráfego pago"],
}


def categorias_todas():
    """União das categorias (receita + despesa), sem repetir (ex.: 'Eventos')."""
    vistos, out = set(), []
    for tipo in ("receita", "despesa"):
        for c in CATEGORIAS[tipo]:
            if c not in vistos:
                vistos.add(c)
                out.append(c)
    return out
