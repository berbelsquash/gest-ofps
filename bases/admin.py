from django.contrib import admin

from .models import Atleta


@admin.register(Atleta)
class AtletaAdmin(admin.ModelAdmin):
    list_display = ("nome", "player_id", "genero", "regiao", "filiacao", "local1", "treinador")
    list_filter = ("filiacao", "regiao", "genero")
    search_fields = ("nome", "email", "telefone", "player_id", "local1", "treinador")
    list_per_page = 60
