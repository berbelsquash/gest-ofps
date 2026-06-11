from django.contrib import admin

from .models import LancamentoBancario, LancamentoFinanceiro


@admin.register(LancamentoBancario)
class LancamentoBancarioAdmin(admin.ModelAdmin):
    list_display = (
        "data", "descricao", "razao_social", "valor",
        "tipo", "grupo", "categoria", "evento", "revisado",
    )
    list_filter = ("tipo", "grupo", "categoria", "revisado", "classificado")
    search_fields = ("descricao", "razao_social", "cpf_cnpj")
    date_hierarchy = "data"
    list_editable = ("grupo", "categoria", "revisado")
    list_per_page = 50
    actions = ["marcar_revisado"]

    @admin.action(description="Marcar como revisado (preserva ao reimportar)")
    def marcar_revisado(self, request, queryset):
        n = queryset.update(revisado=True)
        self.message_user(request, f"{n} lançamento(s) marcado(s) como revisado.")


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = ("ano", "mes", "tipo", "grupo", "categoria", "evento", "valor", "origem")
    list_filter = ("tipo", "grupo", "categoria", "origem", "ano", "mes")
    search_fields = ("categoria", "evento", "descricao")
    list_editable = ("grupo", "categoria", "evento")
    list_per_page = 60
