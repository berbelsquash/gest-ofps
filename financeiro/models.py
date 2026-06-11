from django.db import models

GRUPOS = [
    ("Torneios", "Torneios"),
    ("Folha", "Folha"),
    ("Despesas gerais", "Despesas gerais"),
    ("Patrocínios", "Patrocínios"),
    ("Inscrições", "Inscrições"),
    ("SquaSHE", "SquaSHE"),
    ("Cartão/Vindi", "Cartão/Vindi"),
    ("Filiação", "Filiação"),
    ("Receitas", "Receitas"),
    ("Outras receitas", "Outras receitas"),
    ("Financeiro (não operacional)", "Financeiro (não operacional)"),
]

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


class LancamentoBancario(models.Model):
    """Uma linha do extrato bancário (Banco do Brasil) — usada na conciliação."""

    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    data = models.DateField("data")
    descricao = models.CharField("lançamento", max_length=255, blank=True)
    razao_social = models.CharField("razão social", max_length=255, blank=True)
    cpf_cnpj = models.CharField("CPF/CNPJ", max_length=30, blank=True)
    valor = models.DecimalField("valor (R$)", max_digits=12, decimal_places=2)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    grupo = models.CharField("grupo", max_length=40, blank=True, choices=GRUPOS)
    categoria = models.CharField("categoria", max_length=80, blank=True)
    evento = models.CharField("evento", max_length=120, blank=True)
    classificado = models.BooleanField("classificado", default=False)
    revisado = models.BooleanField(
        "revisado manualmente", default=False,
        help_text="Marque para preservar esta classificação ao reimportar o extrato.",
    )
    importado_em = models.DateTimeField("importado em", auto_now_add=True)

    class Meta:
        verbose_name = "lançamento bancário"
        verbose_name_plural = "lançamentos bancários"
        ordering = ["-data", "-id"]

    def __str__(self):
        return f"{self.data} · {self.razao_social or self.descricao} · R$ {self.valor}"


class LancamentoFinanceiro(models.Model):
    """Ledger categorizado (visão da FPS).

    Fonte da verdade: a planilha até maio (origem='planilha') e, a partir de
    junho, o extrato bancário categorizado nas mesmas categorias (origem='extrato').
    'valor' é sempre positivo; o 'tipo' indica receita ou despesa.
    """

    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    class Origem(models.TextChoices):
        PLANILHA = "planilha", "Planilha (até maio)"
        EXTRATO = "extrato", "Extrato bancário"

    ano = models.PositiveSmallIntegerField("ano", default=2026)
    mes = models.PositiveSmallIntegerField("mês")
    data = models.DateField("data", null=True, blank=True)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices)
    grupo = models.CharField("grupo", max_length=40)
    categoria = models.CharField("categoria", max_length=80, blank=True)
    evento = models.CharField("evento", max_length=120, blank=True)
    valor = models.DecimalField("valor (R$)", max_digits=12, decimal_places=2)
    descricao = models.CharField("descrição", max_length=255, blank=True)
    origem = models.CharField("origem", max_length=12, choices=Origem.choices, default=Origem.PLANILHA)
    pago = models.BooleanField("pago", default=True)

    class Meta:
        verbose_name = "lançamento financeiro"
        verbose_name_plural = "lançamentos financeiros"
        ordering = ["ano", "mes", "-id"]

    def __str__(self):
        return f"{self.mes}/{self.ano} · {self.grupo}/{self.categoria} · R$ {self.valor}"

    @property
    def mes_nome(self):
        return MESES_PT[self.mes - 1] if 1 <= self.mes <= 12 else str(self.mes)
