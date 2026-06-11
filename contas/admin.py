from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """Administração dos usuários do sistema (pessoas da FPS)."""

    # Acrescenta os campos da FPS aos formulários padrão do Django.
    fieldsets = UserAdmin.fieldsets + (
        ("Informações da FPS", {"fields": ("cargo", "telefone")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informações da FPS", {"fields": ("cargo", "telefone")}),
    )
    list_display = (
        "username",
        "first_name",
        "last_name",
        "cargo",
        "email",
        "is_staff",
        "is_active",
    )
    list_filter = UserAdmin.list_filter + ("is_active",)
    search_fields = ("username", "first_name", "last_name", "email", "cargo")
