# Estrutura do menu lateral do painel.
# A navegação tem DUAS áreas (workspaces), trocadas pelo seletor no topo:
#   - "painel": o que se consome (tarefas, análise financeira, dashboards)
#   - "bases":  o que se atualiza (as 5 bases de dados)
# Cada grupo do MENU pertence a uma área. Grupo com "titulo" vazio = itens soltos.

AREAS = [
    {"id": "painel", "label": "Painel", "icone": "bi-grid-1x2-fill"},
    {"id": "bases", "label": "Bases", "icone": "bi-database"},
]

MENU = [
    # ===================== PAINEL =====================
    {
        "area": "painel",
        "titulo": "Tarefas e projetos",
        "itens": [
            {"slug": "tarefas-por-pessoa", "label": "Tarefas", "icone": "bi-check2-square"},
            {"slug": "projetos", "label": "Projetos", "icone": "bi-kanban"},
        ],
    },
    {
        "area": "painel",
        "titulo": "Financeira",
        "itens": [
            {"slug": "financeiro-balanco", "label": "Início", "icone": "bi-house"},
            {"slug": "financeiro-detalhado", "label": "Detalhado", "icone": "bi-bar-chart-line"},
            {"slug": "financeiro-eventos", "label": "Eventos", "icone": "bi-calendar-event"},
            {"slug": "financeiro-previsao", "label": "Previsão", "icone": "bi-graph-up-arrow"},
            {"slug": "financeiro-relatorios", "label": "Relatórios", "icone": "bi-file-earmark-text"},
        ],
    },
    {
        "area": "painel",
        "titulo": "Filiações",
        "itens": [
            {"slug": "recebimentos", "label": "Recebimentos", "icone": "bi-cash-coin"},
            {"slug": "resumo-assinaturas", "label": "Resumo & previsões", "icone": "bi-graph-up"},
        ],
    },
    {
        "area": "painel",
        "titulo": "",
        "itens": [
            {"slug": "doc-oficiais", "label": "Documentos", "icone": "bi-folder"},
        ],
    },
    # ===================== BASES =====================
    {
        "area": "bases",
        "titulo": "",
        "itens": [
            {"slug": "bases-atletas", "label": "Atletas", "icone": "bi-people"},
            {"slug": "bases-financeiro", "label": "Financeira", "icone": "bi-bank"},
            {"slug": "bases-eventos", "label": "Eventos", "icone": "bi-calendar-event"},
            {"slug": "bases-participacoes", "label": "Participações", "icone": "bi-trophy"},
            {"slug": "assinaturas-adimplencia", "label": "Filiações", "icone": "bi-people"},
        ],
    },
]

# Seção exibida ao abrir o sistema.
SECAO_INICIAL = "tarefas-por-pessoa"

# Índice rápido por slug: {slug: {"label", "grupo", "area"}}
ITENS = {
    item["slug"]: {"label": item["label"], "grupo": grupo["titulo"], "area": grupo["area"]}
    for grupo in MENU
    for item in grupo["itens"]
}


def _primeiro_slug(area):
    for grupo in MENU:
        if grupo["area"] == area and grupo["itens"]:
            return grupo["itens"][0]["slug"]
    return ""


def contexto_base(slug, **extra):
    """Monta o contexto comum das telas (menu + área/seção ativa)."""
    item = ITENS.get(slug, {})
    area_atual = item.get("area", "painel")
    areas = [
        {**a, "primeiro": _primeiro_slug(a["id"]), "ativo": a["id"] == area_atual}
        for a in AREAS
    ]
    contexto = {
        "menu": MENU,
        "slug_ativo": slug,
        "titulo": item.get("label", ""),
        "grupo_atual": item.get("grupo", ""),
        "area_atual": area_atual,
        "areas": areas,
    }
    contexto.update(extra)
    return contexto
