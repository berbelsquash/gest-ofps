from decimal import Decimal

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


class ItemPrevisao(models.Model):
    """Item recorrente ou pontual da previsão financeira (folha, despesas
    operacionais, receitas manuais). A previsão de filiações (Vindi) vem das
    assinaturas — não é cadastrada aqui."""

    class Tipo(models.TextChoices):
        RECEITA = "receita", "Receita"
        DESPESA = "despesa", "Despesa"

    class Recorrencia(models.TextChoices):
        MENSAL = "mensal", "Todo mês"
        ANUAL = "anual", "Uma vez por ano"
        UNICO = "unico", "Único (mês específico)"

    nome = models.CharField("nome", max_length=120)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, default=Tipo.DESPESA)
    valor = models.DecimalField("valor (R$)", max_digits=12, decimal_places=2)
    recorrencia = models.CharField(
        "recorrência", max_length=10, choices=Recorrencia.choices, default=Recorrencia.MENSAL)
    mes = models.PositiveSmallIntegerField(
        "mês", null=True, blank=True,
        help_text="Para anual/único: mês em que ocorre (1–12). Mensal: deixe em branco.")
    categoria = models.CharField("categoria", max_length=80, blank=True)
    ativo = models.BooleanField("ativo", default=True)
    observacao = models.CharField("observação", max_length=255, blank=True)

    class Meta:
        verbose_name = "item de previsão"
        verbose_name_plural = "itens de previsão"
        ordering = ["tipo", "-valor"]

    def __str__(self):
        return f"{self.get_tipo_display()} · {self.nome} · R$ {self.valor}"

    def valor_no_mes(self, m):
        """Valor previsto deste item no mês m (1–12); 0 se não se aplica."""
        if not self.ativo:
            return Decimal("0")
        if self.recorrencia == self.Recorrencia.MENSAL:
            return self.valor
        return self.valor if self.mes == m else Decimal("0")

    @property
    def periodo_nome(self):
        if self.recorrencia == self.Recorrencia.MENSAL:
            return "Todo mês"
        if self.mes and 1 <= self.mes <= 12:
            return MESES_PT[self.mes - 1]
        return self.get_recorrencia_display()


class Inscricao(models.Model):
    """Inscrição de um atleta num evento (respostas do Google Forms).

    Serve para: (1) conciliar o esperado do evento (soma das inscrições) com o
    que está marcado no extrato; (2) guardar o link do comprovante por atleta;
    (3) ser a base de atletas por evento. O pagamento em si continua no extrato
    (LancamentoBancario) — aqui é o "quem se inscreveu e quanto deveria pagar"."""

    evento = models.CharField("evento", max_length=120)
    ano = models.PositiveSmallIntegerField("ano", default=2026)
    nome = models.CharField("atleta", max_length=160)
    email = models.CharField("e-mail", max_length=160, blank=True)
    clube = models.CharField("clube/academia", max_length=160, blank=True)
    treinador = models.CharField("treinador", max_length=160, blank=True)
    categoria = models.CharField("categoria", max_length=80, blank=True)
    filiado = models.CharField("filiado", max_length=20, blank=True)
    valor = models.DecimalField("valor (R$)", max_digits=10, decimal_places=2, default=0)
    comprovante_link = models.CharField("comprovante (link)", max_length=500, blank=True)
    pacote = models.BooleanField("pagou via pacote", default=False)
    data_inscricao = models.DateField("data da inscrição", null=True, blank=True)
    importado_em = models.DateTimeField("importado em", auto_now_add=True)

    class Meta:
        verbose_name = "inscrição"
        verbose_name_plural = "inscrições"
        ordering = ["evento", "nome"]

    def __str__(self):
        return f"{self.evento} · {self.nome} · R$ {self.valor}"
