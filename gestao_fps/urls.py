"""
Rotas principais do projeto Gestão FPS.
"""

from django.contrib import admin
from django.urls import include, path

from assinaturas import views as assinaturas_views
from bases import views as bases_views
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
    path("s/bases-atletas/", bases_views.atletas_lista, name="bases_atletas"),
    path("bases/atletas/importar/", bases_views.importar_atletas_view, name="bases_atletas_importar"),
    path("bases/atletas/exportar/", bases_views.exportar_atletas_view, name="bases_atletas_exportar"),
    path("s/bases-financeiro/", bases_views.base_financeira, name="bases_financeiro"),
    path("bases/financeiro/inline/", bases_views.lancamento_inline, name="bases_lancamento_inline"),
    path("bases/financeiro/reconhecer/", bases_views.reconhecer_eventos, name="bases_reconhecer_eventos"),
    path("s/bases-eventos/", bases_views.eventos_base, name="bases_eventos"),
    path("bases/eventos/editar/", bases_views.evento_editar, name="bases_evento_editar"),
    path("bases/eventos/criar/", bases_views.evento_criar, name="bases_evento_criar"),
    path("bases/eventos/<int:pk>/painel/", bases_views.evento_painel, name="bases_evento_painel"),
    path("bases/eventos/tarefa/salvar/", bases_views.evento_tarefa_salvar, name="bases_evento_tarefa_salvar"),
    path("bases/eventos/tarefa/excluir/", bases_views.evento_tarefa_excluir, name="bases_evento_tarefa_excluir"),
    path("bases/eventos/tarefa/add/", bases_views.evento_tarefa_add, name="bases_evento_tarefa_add"),
    path("s/bases-participacoes/", bases_views.participacoes, name="bases_participacoes"),
    path("bases/participacoes/importar/", bases_views.importar_participacoes_view, name="bases_participacoes_importar"),
    path("bases/participacoes/exportar/", bases_views.exportar_participacoes_view, name="bases_participacoes_exportar"),
    # Abas com tela própria (precisam vir ANTES da rota genérica).
    path("s/assinaturas-adimplencia/", assinaturas_views.adimplencia, name="assinaturas_adimplencia"),
    path("s/recebimentos/", assinaturas_views.recebimentos, name="recebimentos"),
    path("s/inadimplencia-cancelamentos/", assinaturas_views.inadimplencia, name="inadimplencia_cancelamentos"),
    path("s/resumo-assinaturas/", assinaturas_views.resumo, name="resumo_assinaturas"),
    path("assinaturas/sincronizar/", assinaturas_views.sincronizar, name="assinaturas_sincronizar"),
    path("assinaturas/conciliar/", assinaturas_views.conciliar_vindi_view, name="assinaturas_conciliar"),
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
