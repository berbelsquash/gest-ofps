"""
Rotas principais do projeto Gestão FPS.
"""

from django.contrib import admin
from django.urls import include, path

from assinaturas import views as assinaturas_views
from financeiro import views as financeiro_views
from painel import views as painel_views
from tarefas import views as tarefas_views

# Personalização dos títulos do painel administrativo do Django.
admin.site.site_header = "Gestão FPS — Administração"
admin.site.site_title = "Gestão FPS"
admin.site.index_title = "Administração avançada"

urlpatterns = [
    # Seção inicial do painel (Painel de tarefas).
    path("", tarefas_views.painel_tarefas, name="home"),
    path("s/tarefas-por-pessoa/", tarefas_views.painel_tarefas, name="tarefas_painel"),
    path("s/tarefas-agenda/", tarefas_views.agenda, name="tarefas_agenda"),
    path("tarefas/nova/", tarefas_views.tarefa_criar, name="tarefa_criar"),
    path("tarefas/<int:pk>/toggle/", tarefas_views.tarefa_toggle, name="tarefa_toggle"),
    path("s/projetos/", tarefas_views.projetos_lista, name="projetos_lista"),
    path("projetos/<int:pk>/", tarefas_views.projeto_detalhe, name="projeto_detalhe"),
    # Abas com tela própria (precisam vir ANTES da rota genérica).
    path("s/assinaturas-adimplencia/", assinaturas_views.adimplencia, name="assinaturas_adimplencia"),
    path("s/recebimentos/", assinaturas_views.recebimentos, name="recebimentos"),
    path("s/inadimplencia-cancelamentos/", assinaturas_views.inadimplencia, name="inadimplencia_cancelamentos"),
    path("s/resumo-assinaturas/", assinaturas_views.resumo, name="resumo_assinaturas"),
    path("assinaturas/sincronizar/", assinaturas_views.sincronizar, name="assinaturas_sincronizar"),
    path("s/financeiro-despesas/", financeiro_views.despesas, name="financeiro_despesas"),
    path("s/financeiro-receitas/", financeiro_views.receitas, name="financeiro_receitas"),
    path("s/financeiro-receitas-despesas/", financeiro_views.receitas_despesas, name="financeiro_receitas_despesas"),
    path("s/financeiro-detalhado/", financeiro_views.detalhado, name="financeiro_detalhado"),
    path("s/financeiro-eventos/", financeiro_views.por_evento, name="financeiro_eventos"),
    path("s/financeiro-eventos-revisar/", financeiro_views.revisar_eventos, name="financeiro_eventos_revisar"),
    path("s/financeiro-inscricoes/", financeiro_views.importar_inscricoes, name="financeiro_inscricoes"),
    path("s/financeiro-conciliar/", financeiro_views.conciliar_evento, name="financeiro_conciliar"),
    path("s/financeiro-balanco/", financeiro_views.balanco, name="financeiro_balanco"),
    path("s/financeiro-previsao/", financeiro_views.previsao, name="financeiro_previsao"),
    path("s/financeiro-relatorios/", financeiro_views.relatorios, name="financeiro_relatorios"),
    path("s/financeiro-conciliacao/", financeiro_views.conciliacao, name="financeiro_conciliacao"),
    path("financeiro/lancamento/<int:pk>/editar/", financeiro_views.editar_lancamento, name="editar_lancamento"),
    path("financeiro/importar-extrato/", financeiro_views.importar_extrato_view, name="importar_extrato_view"),
    # Demais seções do menu (placeholder genérico).
    path("s/<slug:slug>/", painel_views.secao, name="secao"),
    # Login, logout e troca de senha (views prontas do Django).
    path("", include("django.contrib.auth.urls")),
    # Painel administrativo do Django.
    path("admin/", admin.site.urls),
]
