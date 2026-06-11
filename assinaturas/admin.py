from django.contrib import admin

from .models import AssinaturaVindi, PlanoVindi, RecebimentoVindi


@admin.register(PlanoVindi)
class PlanoVindiAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "status", "vindi_id", "atualizado_em")
    list_filter = ("tipo", "status")
    search_fields = ("nome",)


@admin.register(AssinaturaVindi)
class AssinaturaVindiAdmin(admin.ModelAdmin):
    list_display = (
        "cliente_nome",
        "plano_nome",
        "tipo",
        "status",
        "data_inicio",
        "inadimplente_desde",
        "cancelada_em",
    )
    list_filter = ("tipo", "status")
    search_fields = ("cliente_nome", "cliente_email", "cliente_documento")


@admin.register(RecebimentoVindi)
class RecebimentoVindiAdmin(admin.ModelAdmin):
    list_display = ("cliente_nome", "plano_nome", "tipo", "valor", "data_pagamento")
    list_filter = ("tipo", "status")
    search_fields = ("cliente_nome",)
    date_hierarchy = "data_pagamento"
