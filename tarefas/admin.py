from django.contrib import admin

from .models import Evento, ModeloTarefaEvento, Pessoa, Projeto, Tarefa


@admin.register(Pessoa)
class PessoaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_editable = ("ativo",)


@admin.register(Projeto)
class ProjetoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ativo")
    list_editable = ("ativo",)


@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ("nome", "data_inicio", "data_fim")
    date_hierarchy = "data_inicio"


@admin.register(ModeloTarefaEvento)
class ModeloTarefaEventoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "responsavel_padrao", "dias_antes", "ordem")
    list_editable = ("responsavel_padrao", "dias_antes", "ordem")
    search_fields = ("titulo",)


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "responsavel", "evento", "projeto", "prazo", "feita")
    list_filter = ("feita", "responsavel", "evento", "projeto")
    list_editable = ("responsavel", "feita")
    search_fields = ("titulo", "descricao")
    date_hierarchy = "prazo"
