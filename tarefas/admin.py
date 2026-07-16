from django.contrib import admin

from .models import (Evento, ModeloTarefaEvento, Pessoa, Projeto,
                     RespostaProjeto, Tarefa, Tema)


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_editable = ("ativo",)


@admin.register(Tema)
class TemaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_editable = ("ativo",)


class RespostaProjetoInline(admin.TabularInline):
    model = RespostaProjeto
    extra = 0


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "status", "ativo")
    list_editable = ("status", "ativo")
    inlines = [RespostaProjetoInline]


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "tier", "data_inicio", "data_fim", "inscricoes_ate")
    list_editable = ("inscricoes_ate",)
    list_filter = ("tipo",)
    date_hierarchy = "data_inicio"


@admin.register(ModeloTarefaEvento)
class ModeloTarefaEventoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "checklist", "offset_dias", "tema", "ordem")
    list_editable = ("offset_dias", "tema", "ordem")
    list_filter = ("checklist",)
    search_fields = ("titulo",)


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "tipo", "evento", "projeto", "prazo", "hora", "feita")
    list_filter = ("feita", "tipo", "responsaveis", "temas", "evento", "projeto")
    list_editable = ("feita",)
    filter_horizontal = ("responsaveis", "temas")
    search_fields = ("titulo", "descricao")
    date_hierarchy = "prazo"
