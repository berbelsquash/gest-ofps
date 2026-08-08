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


class Participacao(models.Model):
    """Participação de um atleta num evento (resultado). Ligada à Base de Atletas
    pelo nome → atleta (que carrega o Player ID). Nome cru fica guardado para os
    casos ainda não conciliados."""

    atleta = models.ForeignKey(
        Atleta, null=True, blank=True, on_delete=models.SET_NULL, related_name="participacoes")
    atleta_nome = models.CharField("atleta", max_length=160)
    campeonato = models.CharField("campeonato", max_length=160)
    data = models.DateField("data", null=True, blank=True)
    categoria = models.CharField("categoria disputada", max_length=120, blank=True)
    colocacao = models.CharField("colocação", max_length=60, blank=True)
    pontuacao = models.IntegerField("pontuação", null=True, blank=True)
    academia = models.CharField("academia/clube", max_length=160, blank=True)
    treinador = models.CharField("treinador", max_length=120, blank=True)

    class Meta:
        verbose_name = "participação"
        verbose_name_plural = "participações"
        ordering = ["-data", "campeonato", "atleta_nome"]
        indexes = [models.Index(fields=["campeonato"]), models.Index(fields=["atleta_nome"])]

    def __str__(self):
        return f"{self.atleta_nome} · {self.campeonato}"
