from django.db import models
from django.utils import timezone


class Pessoa(models.Model):
    """Membro da equipe que executa tarefas."""

    nome = models.CharField("nome", max_length=80, unique=True)
    ativo = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "pessoa"
        verbose_name_plural = "pessoas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def iniciais(self):
        partes = [p for p in self.nome.split() if p]
        if len(partes) >= 2:
            return (partes[0][0] + partes[-1][0]).upper()
        return self.nome[:2].upper()


class Projeto(models.Model):
    nome = models.CharField("nome", max_length=100, unique=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "projeto"
        verbose_name_plural = "projetos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Evento(models.Model):
    nome = models.CharField("nome", max_length=120, unique=True)
    data_inicio = models.DateField("início", null=True, blank=True)
    data_fim = models.DateField("fim", null=True, blank=True)

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["data_inicio", "nome"]

    def __str__(self):
        return self.nome


class ModeloTarefaEvento(models.Model):
    """Tarefa do checklist padrão que se repete em todo evento."""

    titulo = models.CharField("título", max_length=200)
    responsavel_padrao = models.ForeignKey(
        Pessoa, verbose_name="responsável padrão", null=True, blank=True, on_delete=models.SET_NULL)
    dias_antes = models.IntegerField(
        "prazo (dias antes do evento)", default=0,
        help_text="o prazo da tarefa = data do evento menos estes dias")
    ordem = models.PositiveIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "tarefa padrão de evento"
        verbose_name_plural = "checklist padrão de evento"
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.titulo


class Tarefa(models.Model):
    """Uma tarefa. Pode estar ligada a um evento, a um projeto ou ser avulsa."""

    titulo = models.CharField("título", max_length=200)
    descricao = models.TextField("descrição", blank=True)
    responsavel = models.ForeignKey(
        Pessoa, verbose_name="responsável", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="tarefas")
    evento = models.ForeignKey(
        Evento, null=True, blank=True, on_delete=models.CASCADE, related_name="tarefas")
    projeto = models.ForeignKey(
        Projeto, null=True, blank=True, on_delete=models.CASCADE, related_name="tarefas")
    prazo = models.DateField("prazo", null=True, blank=True)
    feita = models.BooleanField("feita", default=False)
    ordem = models.PositiveIntegerField("ordem", default=0)
    criada_em = models.DateTimeField("criada em", auto_now_add=True)
    concluida_em = models.DateTimeField("concluída em", null=True, blank=True)

    class Meta:
        verbose_name = "tarefa"
        verbose_name_plural = "tarefas"
        ordering = ["feita", "prazo", "ordem", "-id"]

    def __str__(self):
        return self.titulo

    @property
    def tipo_vinculo(self):
        if self.evento_id:
            return "evento"
        if self.projeto_id:
            return "projeto"
        return "avulsa"

    @property
    def vinculo_nome(self):
        if self.evento_id:
            return self.evento.nome
        if self.projeto_id:
            return self.projeto.nome
        return "Avulsa"

    def marcar(self, feita):
        self.feita = feita
        self.concluida_em = timezone.now() if feita else None
        self.save(update_fields=["feita", "concluida_em"])
