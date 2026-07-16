"""Gera as tarefas de um evento a partir do seu checklist padrão e da cadência
de comunicação. Reutilizável ao cadastrar/editar um evento.

- Checklist: um item por linha do ModeloTarefaEvento do tipo do evento; prazo =
  data do evento + offset (negativo antes do início, positivo após o fim).
- Comunicação: uma por semana (segunda-feira) nas ~8 semanas até o evento +
  os 3 avisos de fim de inscrição (−7, −1 e o dia do fecho), se houver data.

Tudo é atribuído por padrão ao Vinicius Berbel (ajustável depois). Regenerar é
idempotente: apaga as tarefas da mesma série do evento antes de recriar.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone
from django.utils.timezone import make_aware

from .models import Evento, ModeloTarefaEvento, Pessoa, Tarefa, Tema

RESP_PADRAO = "Vinicius Berbel"


def _criar(ev, titulo, prazo, serie, ordem, tema=None):
    if not prazo:
        return None
    feita = prazo < timezone.localdate()
    t = Tarefa.objects.create(
        titulo=titulo, tipo=Tarefa.Tipo.EVENTO, evento=ev, prazo=prazo,
        serie=serie, ordem=ordem, feita=feita,
        concluida_em=make_aware(datetime.combine(prazo, time(12, 0))) if feita else None)
    resp = Pessoa.objects.filter(nome=RESP_PADRAO).first()
    if resp:
        t.responsaveis.add(resp)
    if tema:
        t.temas.add(tema)
    return t


def gerar_checklist(ev):
    """(Re)cria as tarefas do checklist padrão do evento."""
    ev.tarefas.filter(serie="checklist").delete()
    chk = ev.checklist
    if not chk or not ev.data_inicio:
        return 0
    fim = ev.data_fim or ev.data_inicio
    n = 0
    for m in ModeloTarefaEvento.objects.filter(checklist=chk):
        base = ev.data_inicio if m.offset_dias < 0 else fim
        _criar(ev, m.titulo, base + timedelta(days=m.offset_dias), "checklist", m.ordem, m.tema)
        n += 1
    return n


def gerar_comunicacoes(ev):
    """(Re)cria as comunicações semanais + avisos de fim de inscrição."""
    ev.tarefas.filter(serie="comunicacao").delete()
    if ev.tipo == Evento.Tipo.LIGA or not ev.data_inicio:
        return 0
    tema = Tema.objects.filter(nome="Comunicação").first()
    n = 0
    d = ev.data_inicio - timedelta(days=56)
    while d.weekday() != 0:  # 0 = segunda-feira
        d += timedelta(days=1)
    i = 0
    while d <= ev.data_inicio:
        _criar(ev, f"Comunicar {ev.nome}", d, "comunicacao", i, tema)
        i += 1
        n += 1
        d += timedelta(days=7)
    c = ev.inscricoes_ate
    if c:
        _criar(ev, f"Comunicar {ev.nome}: falta 1 semana p/ o fim das inscrições",
               c - timedelta(days=7), "comunicacao", 90, tema)
        _criar(ev, f"Comunicar {ev.nome}: amanhã é o último dia de inscrição",
               c - timedelta(days=1), "comunicacao", 91, tema)
        _criar(ev, f"Comunicar {ev.nome}: hoje é o último dia de inscrição",
               c, "comunicacao", 92, tema)
        n += 3
    return n


def gerar_para_evento(ev):
    """Gera checklist + comunicações. Devolve (n_checklist, n_comunicacao)."""
    return gerar_checklist(ev), gerar_comunicacoes(ev)
