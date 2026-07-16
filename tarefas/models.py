from django.db import models
from django.utils import timezone

# Perguntas do "business plan" instanciadas ao criar um projeto.
PERGUNTAS_PROJETO = [
    "Qual é o objetivo do projeto? O que queremos alcançar?",
    "Por que ele é importante para a FPS? (justificativa)",
    "Quem é o público-alvo / quem se beneficia?",
    "Qual o escopo? O que inclui e o que NÃO inclui?",
    "Quais são as principais entregas e marcos?",
    "Qual o orçamento estimado e as fontes de receita?",
    "Quais são os custos principais?",
    "Quem são os responsáveis e parceiros envolvidos?",
    "Qual o cronograma? (início, fim e datas-chave)",
    "Quais os riscos e como mitigá-los?",
    "Como vamos medir o sucesso? (metas e indicadores)",
    "Quais os próximos passos imediatos?",
]


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


class Tema(models.Model):
    """Assunto/categoria de uma tarefa (uma tarefa pode ter vários)."""

    nome = models.CharField("nome", max_length=60, unique=True)
    ativo = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "tema"
        verbose_name_plural = "temas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Evento(models.Model):
    class Tipo(models.TextChoices):
        CAMPEONATO = "campeonato", "Campeonato (amador/juvenil)"
        JUNIOR_XP = "junior_xp", "Junior XP"
        SQUASHE = "squashe", "SquaSHE"
        LIGA = "liga", "FPS League"
        OUTRO = "outro", "Outro"

    nome = models.CharField("nome", max_length=120, unique=True)
    data_inicio = models.DateField("início", null=True, blank=True)
    data_fim = models.DateField("fim", null=True, blank=True)
    inscricoes_ate = models.DateField(
        "inscrições até", null=True, blank=True,
        help_text="encerramento das inscrições — gera os avisos de fim de inscrição")
    tipo = models.CharField("tipo", max_length=12, choices=Tipo.choices, default=Tipo.CAMPEONATO)
    tier = models.CharField("tier", max_length=20, blank=True)

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["data_inicio", "nome"]

    def __str__(self):
        return self.nome

    @property
    def checklist(self):
        """Qual checklist padrão se aplica a este tipo de evento."""
        if self.tipo in (self.Tipo.JUNIOR_XP, self.Tipo.SQUASHE):
            return ModeloTarefaEvento.Checklist.JUNIOR_SQUASHE
        if self.tipo == self.Tipo.CAMPEONATO:
            return ModeloTarefaEvento.Checklist.CAMPEONATO
        return None


class Projeto(models.Model):
    class Status(models.TextChoices):
        IDEIA = "ideia", "Ideia"
        PLANEJAMENTO = "planejamento", "Planejamento"
        ANDAMENTO = "andamento", "Em andamento"
        CONCLUIDO = "concluido", "Concluído"
        PAUSADO = "pausado", "Pausado"

    nome = models.CharField("nome", max_length=100, unique=True)
    resumo = models.TextField("resumo", blank=True)
    status = models.CharField("status", max_length=14, choices=Status.choices, default=Status.PLANEJAMENTO)
    ativo = models.BooleanField("ativo", default=True)
    criado_em = models.DateTimeField("criado em", auto_now_add=True)

    class Meta:
        verbose_name = "projeto"
        verbose_name_plural = "projetos"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def instanciar_business_plan(self):
        """Cria as perguntas do business plan se ainda não existirem."""
        if self.respostas.exists():
            return
        RespostaProjeto.objects.bulk_create([
            RespostaProjeto(projeto=self, ordem=i, pergunta=p)
            for i, p in enumerate(PERGUNTAS_PROJETO)
        ])


class RespostaProjeto(models.Model):
    """Uma pergunta do business plan do projeto + a resposta."""

    projeto = models.ForeignKey(Projeto, on_delete=models.CASCADE, related_name="respostas")
    ordem = models.PositiveIntegerField("ordem", default=0)
    pergunta = models.CharField("pergunta", max_length=255)
    resposta = models.TextField("resposta", blank=True)

    class Meta:
        verbose_name = "resposta do projeto"
        verbose_name_plural = "business plan"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.projeto.nome} · {self.pergunta[:40]}"


class ModeloTarefaEvento(models.Model):
    """Item do checklist padrão de evento. O prazo de cada tarefa gerada =
    data do evento + offset_dias (negativo = antes do início, positivo = após o fim)."""

    class Checklist(models.TextChoices):
        CAMPEONATO = "campeonato", "Campeonato (amador/juvenil)"
        JUNIOR_SQUASHE = "junior_squashe", "Junior XP / SquaSHE"

    checklist = models.CharField(
        "checklist", max_length=16, choices=Checklist.choices, default=Checklist.CAMPEONATO)
    titulo = models.CharField("título", max_length=200)
    offset_dias = models.IntegerField(
        "offset (dias)", default=0,
        help_text="negativo = dias antes do início; positivo = dias após o fim")
    tema = models.ForeignKey("Tema", null=True, blank=True, on_delete=models.SET_NULL)
    ordem = models.PositiveIntegerField("ordem", default=0)

    class Meta:
        verbose_name = "tarefa padrão de evento"
        verbose_name_plural = "checklist padrão de evento"
        ordering = ["checklist", "ordem", "id"]

    def __str__(self):
        return f"[{self.get_checklist_display()}] {self.titulo}"


class Tarefa(models.Model):
    """Uma tarefa. Ligada a um evento, a um projeto, recorrente (geral),
    reunião ou avulsa. Sempre pode ter vários responsáveis e temas."""

    class Tipo(models.TextChoices):
        EVENTO = "evento", "Evento"
        PROJETO = "projeto", "Projeto"
        GERAL = "geral", "Geral / recorrente"
        REUNIAO = "reuniao", "Reunião"
        AVULSA = "avulsa", "Avulsa"

    titulo = models.CharField("título", max_length=200)
    descricao = models.TextField("descrição", blank=True)
    tipo = models.CharField("tipo", max_length=10, choices=Tipo.choices, default=Tipo.AVULSA)
    responsaveis = models.ManyToManyField(Pessoa, blank=True, related_name="tarefas")
    temas = models.ManyToManyField(Tema, blank=True, related_name="tarefas")
    evento = models.ForeignKey(
        Evento, null=True, blank=True, on_delete=models.CASCADE, related_name="tarefas")
    projeto = models.ForeignKey(
        Projeto, null=True, blank=True, on_delete=models.CASCADE, related_name="tarefas")
    prazo = models.DateField("prazo", null=True, blank=True)
    hora = models.TimeField("hora", null=True, blank=True)
    feita = models.BooleanField("feita", default=False)
    serie = models.CharField("série", max_length=40, blank=True,
                             help_text="marca tarefas recorrentes/geradas (ex.: folha, reuniao-fps)")
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
    def vinculo_nome(self):
        if self.evento_id:
            return self.evento.nome
        if self.projeto_id:
            return self.projeto.nome
        return self.get_tipo_display()

    @property
    def atrasada(self):
        return bool(self.prazo) and not self.feita and self.prazo < timezone.localdate()

    def marcar(self, feita):
        self.feita = feita
        self.concluida_em = timezone.now() if feita else None
        self.save(update_fields=["feita", "concluida_em"])
