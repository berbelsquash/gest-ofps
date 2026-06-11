from django.db import models


class PlanoVindi(models.Model):
    """Plano sincronizado da Vindi, com o 'tipo' da FPS deduzido pelo nome."""

    class Tipo(models.TextChoices):
        FILIACAO = "filiacao", "Filiação"
        INTERIOR = "interior", "Interior"
        JUVENIL = "juvenil", "Juvenil"
        SQUASHE = "squashe", "SquaSHE"
        OUTROS = "outros", "Outros"
        IGNORAR = "ignorar", "Ignorar"

    vindi_id = models.BigIntegerField("ID na Vindi", unique=True)
    nome = models.CharField("plano", max_length=200)
    tipo = models.CharField("tipo", max_length=20, choices=Tipo.choices, default=Tipo.OUTROS)
    intervalo = models.CharField("intervalo", max_length=50, blank=True)
    status = models.CharField("status", max_length=30, blank=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "plano (Vindi)"
        verbose_name_plural = "planos (Vindi)"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class AssinaturaVindi(models.Model):
    """Assinatura/filiação sincronizada da Vindi."""

    vindi_id = models.BigIntegerField("ID na Vindi", unique=True)
    cliente_nome = models.CharField("nome", max_length=200)
    cliente_vindi_id = models.BigIntegerField("ID do cliente na Vindi", null=True, blank=True)
    cliente_email = models.EmailField("e-mail", blank=True)
    cliente_documento = models.CharField("documento (CPF)", max_length=30, blank=True)
    plano = models.ForeignKey(
        PlanoVindi, on_delete=models.SET_NULL, null=True, blank=True, related_name="assinaturas"
    )
    plano_nome = models.CharField("plano", max_length=200, blank=True)
    tipo = models.CharField(
        "tipo", max_length=20, choices=PlanoVindi.Tipo.choices, default=PlanoVindi.Tipo.OUTROS
    )
    status = models.CharField("status", max_length=20, blank=True)
    valor_ciclo = models.DecimalField("valor por cobrança (R$)", max_digits=12, decimal_places=2, default=0)
    intervalo_meses = models.PositiveIntegerField("intervalo (meses)", default=1)
    data_inicio = models.DateField("data de filiação", null=True, blank=True)
    proxima_cobranca = models.DateField("próxima cobrança", null=True, blank=True)
    inadimplente_desde = models.DateField("inadimplente desde", null=True, blank=True)
    cancelada_em = models.DateField("cancelada em", null=True, blank=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "assinatura (Vindi)"
        verbose_name_plural = "assinaturas (Vindi)"
        ordering = ["cliente_nome"]

    def __str__(self):
        return f"{self.cliente_nome} — {self.plano_nome}"

    @property
    def cancelada(self):
        return self.status == "canceled"

    @property
    def inadimplente(self):
        return self.inadimplente_desde is not None and not self.cancelada

    @property
    def status_pagamento(self):
        if self.cancelada:
            return "Cancelada"
        if self.inadimplente:
            return "Inadimplente"
        return "Em dia"


class RecebimentoVindi(models.Model):
    """Pagamento recebido (fatura paga na Vindi) — compõe o histórico de recebimentos."""

    vindi_id = models.BigIntegerField("ID na Vindi", unique=True)
    cliente_nome = models.CharField("nome", max_length=200)
    cliente_vindi_id = models.BigIntegerField("ID do cliente na Vindi", null=True, blank=True)
    plano_nome = models.CharField("plano", max_length=200, blank=True)
    tipo = models.CharField(
        "tipo", max_length=20, choices=PlanoVindi.Tipo.choices, default=PlanoVindi.Tipo.OUTROS
    )
    valor = models.DecimalField("valor (R$)", max_digits=12, decimal_places=2, default=0)
    status = models.CharField("status", max_length=20, blank=True)
    data_pagamento = models.DateField("data do pagamento", null=True, blank=True)
    atualizado_em = models.DateTimeField("atualizado em", auto_now=True)

    class Meta:
        verbose_name = "recebimento (Vindi)"
        verbose_name_plural = "recebimentos (Vindi)"
        ordering = ["-data_pagamento"]

    def __str__(self):
        return f"{self.cliente_nome} — R$ {self.valor}"
