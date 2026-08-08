from django.contrib import admin

from .models import Atleta, Participacao


@admin.register(Atleta)
class AtletaAdmin(admin.ModelAdmin):
    list_display = ("nome", "player_id", "genero", "regiao", "filiacao", "local1", "treinador")
    list_filter = ("filiacao", "regiao", "genero")
    search_fields = ("nome", "email", "telefone", "player_id", "local1", "treinador")
    list_per_page = 60


@admin.register(Participacao)
class ParticipacaoAdmin(admin.ModelAdmin):
    list_display = ("atleta_nome", "campeonato", "data", "categoria", "colocacao", "pontuacao", "atleta")
    list_filter = ("campeonato",)
    search_fields = ("atleta_nome", "campeonato", "academia")
    list_per_page = 60
    raw_id_fields = ("atleta",)
