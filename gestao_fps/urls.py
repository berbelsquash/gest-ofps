"""
Rotas principais do projeto Gestão FPS.
"""

from django.contrib import admin
from django.urls import include, path

from assinaturas import views as assinaturas_views
from financeiro import views as financeiro_views
from painel import views as painel_views

# Personalização dos títulos do painel administrativo do Django.
admin.site.site_header = "Gestão FPS — Administração"
admin.site.site_title = "Gestão FPS"
admin.site.index_title = "Administração avançada"

urlpatterns = [
    # Seção inicial do painel (Tarefas por pessoa).
    path("", painel_views.secao, name="home"),
    # Abas com tela própria (precisam vir ANTES da rota genérica).
    path("s/assinaturas-adimplencia/", assinaturas_views.adimplencia, name="assinaturas_adimplencia"),
    path("s/recebimentos/", assinaturas_views.recebimentos, name="recebimentos"),
    path("s/inadimplencia-cancelamentos/", assinaturas_views.inadimplencia, name="inadimplencia_cancelamentos"),
    path("s/resumo-assinaturas/", assinaturas_views.resumo, name="resumo_assinaturas"),
    path("assinaturas/sincronizar/", assinaturas_views.sincronizar, name="assinaturas_sincronizar"),
    path("s/financeiro-despesas/", financeiro_views.despesas, name="financeiro_despesas"),
    path("s/financeiro-receitas/", financeiro_views.receitas, name="financeiro_receitas"),
    path("s/financeiro-eventos/", financeiro_views.por_evento, name="financeiro_eventos"),
    path("s/financeiro-previsao/", financeiro_views.previsao, name="financeiro_previsao"),
    path("s/financeiro-conciliacao/", financeiro_views.conciliacao, name="financeiro_conciliacao"),
    # Demais seções do menu (placeholder genérico).
    path("s/<slug:slug>/", painel_views.secao, name="secao"),
    # Login, logout e troca de senha (views prontas do Django).
    path("", include("django.contrib.auth.urls")),
    # Painel administrativo do Django.
    path("admin/", admin.site.urls),
]
