from django.db import models
from django.utils import timezone


class Atleta(models.Model):
    """Cadastro mestre de atleta (Base de Atletas). É a identidade-âncora à qual
    a conciliação liga inscrições, filiações (Vindi) e favorecidos de Pix.

    Importada/enriquecida via planilha: o upsert casa por Player ID (quando há)
    ou pelo nome, então reimportar a base enriquecida não duplica ninguém."""

    nome = models.CharField("nome", max_length=160)
    player_id = models.CharField("Player ID", max_length=20, blank=True, db_index=True)
    genero = models.CharField("gênero", max_length=20, blank=True)
    data_nascimento = models.DateField("data de nascimento", null=True, blank=True)
    classe = models.CharField("classe", max_length=40, blank=True)
    treinador = models.CharField("treinador", max_length=120, blank=True)
    telefone = models.CharField("telefone", max_length=40, blank=True)
    email = models.CharField("e-mail", max_length=160, blank=True)
    regiao = models.CharField("região", max_length=60, blank=True)
    filiacao = models.CharField("filiação", max_length=40, blank=True)
    local1 = models.CharField("local 1", max_length=160, blank=True)
    local2 = models.CharField("local 2", max_length=160, blank=True)
    local3 = models.CharField("local 3", max_length=160, blank=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "atleta"
        verbose_name_plural = "atletas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def idade(self):
        if not self.data_nascimento:
            return None
        h = timezone.localdate()
        return (h.year - self.data_nascimento.year
                - ((h.month, h.day) < (self.data_nascimento.month, self.data_nascimento.day)))

    @property
    def filiado(self):
        return self.filiacao.strip().lower() == "ativo"
