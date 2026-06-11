from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Usuário do sistema — pessoas da FPS que acessam a gestão.

    Herda de AbstractUser, então já possui: username, first_name, last_name,
    email, password, is_staff, is_active, is_superuser, etc.
    """

    cargo = models.CharField("cargo / função na FPS", max_length=100, blank=True)
    telefone = models.CharField("telefone", max_length=20, blank=True)

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"
        ordering = ["first_name", "username"]

    def __str__(self):
        return self.get_full_name() or self.username
