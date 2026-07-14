# Estrutura do menu lateral do painel.
# Para adicionar, renomear ou remover itens, basta editar a lista MENU.
# 'icone' usa as classes do Bootstrap Icons (https://icons.getbootstrap.com/).
# Um grupo com "titulo" vazio aparece como item solto (sem cabeçalho).

MENU = [
    {
        "titulo": "",
        "itens": [
            {"slug": "tarefas-por-pessoa", "label": "Tarefas", "icone": "bi-check2-square"},
        ],
    },
    {
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
        "titulo": "Filiações",
        "itens": [
            {"slug": "assinaturas-adimplencia", "label": "Assinaturas & adimplência", "icone": "bi-people"},
            {"slug": "recebimentos", "label": "Recebimentos", "icone": "bi-cash-coin"},
            {"slug": "inadimplencia-cancelamentos", "label": "Inadimplência & cancelamentos", "icone": "bi-exclamation-triangle"},
            {"slug": "resumo-assinaturas", "label": "Resumo & previsões", "icone": "bi-graph-up"},
        ],
    },
    {
        "titulo": "",
        "itens": [
            {"slug": "bases-atletas", "label": "Bases", "icone": "bi-people"},
        ],
    },
    {
        "titulo": "",
        "itens": [
            {"slug": "doc-oficiais", "label": "Documentos", "icone": "bi-folder"},
        ],
    },
]

# Seção exibida ao abrir o sistema.
SECAO_INICIAL = "tarefas-por-pessoa"

# Índice rápido por slug: {slug: {"label": ..., "grupo": ...}}
ITENS = {
    item["slug"]: {"label": item["label"], "grupo": grupo["titulo"]}
    for grupo in MENU
    for item in grupo["itens"]
}


def contexto_base(slug, **extra):
    """Monta o contexto comum das telas (menu + identificação da seção ativa)."""
    item = ITENS.get(slug, {})
    contexto = {
        "menu": MENU,
        "slug_ativo": slug,
        "titulo": item.get("label", ""),
        "grupo_atual": item.get("grupo", ""),
    }
    contexto.update(extra)
    return contexto
