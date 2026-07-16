from collections import OrderedDict
from datetime import date, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from painel.menu import contexto_base

from .models import Evento, Pessoa, Projeto, Tarefa, Tema


@login_required
def painel_tarefas(request):
    """Home das tarefas: 'hoje' (tarefas + reuniões), filtros a fazer/futuras/
    realizadas, por pessoa e por tipo, e o mini-dash por pessoa."""
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=7)  # "a fazer" = até 7 dias à frente
    status = request.GET.get("status", "afazer")
    pessoa_sel = request.GET.get("pessoa", "")
    tipo_sel = request.GET.get("tipo", "")

    qs = (Tarefa.objects.prefetch_related("responsaveis", "temas")
          .select_related("evento", "projeto"))
    if pessoa_sel:
        qs = qs.filter(responsaveis__id=pessoa_sel)
    if tipo_sel:
        qs = qs.filter(tipo=tipo_sel)

    if status == "feitas":
        lista = qs.filter(feita=True).order_by("-prazo", "-id")
    elif status == "futuras":
        lista = qs.filter(feita=False, prazo__gt=limite).order_by("prazo", "id")
    else:
        status = "afazer"
        lista = (qs.filter(feita=False)
                 .filter(Q(prazo__lte=limite) | Q(prazo__isnull=True))
                 .order_by("prazo", "id"))
    lista = list(lista.distinct())

    # "Hoje": tarefas do dia + reuniões do dia
    hoje_qs = (Tarefa.objects.prefetch_related("responsaveis", "temas")
               .select_related("evento", "projeto").filter(prazo=hoje, feita=False))
    tarefas_dia = [t for t in hoje_qs if t.tipo != Tarefa.Tipo.REUNIAO]
    reunioes_dia = [t for t in hoje_qs if t.tipo == Tarefa.Tipo.REUNIAO]

    # mini-dash: a fazer por pessoa (não feita, próximos 7 dias / atrasada / sem prazo)
    base = (Tarefa.objects.filter(feita=False)
            .filter(Q(prazo__lte=limite) | Q(prazo__isnull=True)))
    cont = {}
    for pid in base.values_list("responsaveis__id", flat=True):
        cont[pid] = cont.get(pid, 0) + 1
    pessoas = list(Pessoa.objects.filter(ativo=True))
    for p in pessoas:
        p.a_fazer = cont.get(p.id, 0)

    contexto = contexto_base(
        "tarefas-por-pessoa", hoje=hoje,
        lista=lista, status=status, pessoa_sel=pessoa_sel, tipo_sel=tipo_sel,
        tarefas_dia=tarefas_dia, reunioes_dia=reunioes_dia,
        pessoas=pessoas, temas=Tema.objects.filter(ativo=True),
        tipos=Tarefa.Tipo.choices,
        eventos=Evento.objects.all(), projetos=Projeto.objects.filter(ativo=True),
        total_afazer=base.distinct().count(),
    )
    return render(request, "tarefas/painel.html", contexto)


@login_required
def agenda(request):
    """Visão em agenda: tarefas agrupadas por dia, numa janela de 6 semanas."""
    hoje = timezone.localdate()
    try:
        ini = date.fromisoformat(request.GET["ini"]) if request.GET.get("ini") else hoje
    except ValueError:
        ini = hoje
    fim = ini + timedelta(days=42)
    pessoa_sel = request.GET.get("pessoa", "")

    qs = (Tarefa.objects.prefetch_related("responsaveis", "temas")
          .select_related("evento", "projeto")
          .filter(prazo__gte=ini, prazo__lte=fim))
    if pessoa_sel:
        qs = qs.filter(responsaveis__id=pessoa_sel)
    dias = OrderedDict()
    for t in qs.order_by("prazo", "hora", "id").distinct():
        dias.setdefault(t.prazo, []).append(t)
    grupos = [{"data": d, "tarefas": ts, "hoje": d == hoje} for d, ts in dias.items()]

    contexto = contexto_base(
        "tarefas-por-pessoa", titulo="Agenda", grupos=grupos, hoje=hoje,
        ini=ini, fim=fim, pessoa_sel=pessoa_sel,
        pessoas=Pessoa.objects.filter(ativo=True),
        prev=(ini - timedelta(days=42)).isoformat(),
        prox=(ini + timedelta(days=42)).isoformat(),
    )
    return render(request, "tarefas/agenda.html", contexto)


@login_required
def tarefa_criar(request):
    """Cria uma tarefa ou reunião (o form manda o tipo)."""
    voltar = request.POST.get("voltar") or "/"
    if not voltar.startswith("/"):
        voltar = "/"
    if request.method == "POST":
        titulo = (request.POST.get("titulo") or "").strip()
        if not titulo:
            messages.error(request, "A tarefa precisa de um título.")
            return redirect(voltar)
        t = Tarefa(titulo=titulo, descricao=(request.POST.get("descricao") or "").strip())
        t.tipo = request.POST.get("tipo") or Tarefa.Tipo.AVULSA
        vinc = request.POST.get("vinculo") or ""
        if vinc.startswith("evento:"):
            t.evento_id = int(vinc.split(":", 1)[1])
            t.tipo = Tarefa.Tipo.EVENTO
        elif vinc.startswith("projeto:"):
            t.projeto_id = int(vinc.split(":", 1)[1])
            t.tipo = Tarefa.Tipo.PROJETO
        prazo = (request.POST.get("prazo") or "").strip()
        if prazo:
            try:
                t.prazo = date.fromisoformat(prazo)
            except ValueError:
                pass
        hora = (request.POST.get("hora") or "").strip()
        if hora:
            try:
                t.hora = time.fromisoformat(hora)
            except ValueError:
                pass
        t.save()
        resp_ids = request.POST.getlist("responsaveis")
        if resp_ids:
            t.responsaveis.set(Pessoa.objects.filter(id__in=resp_ids))
        tema_ids = request.POST.getlist("temas")
        if tema_ids:
            t.temas.set(Tema.objects.filter(id__in=tema_ids))
        messages.success(
            request, "Reunião criada." if t.tipo == Tarefa.Tipo.REUNIAO else "Tarefa criada.")
    return redirect(voltar)


@login_required
def projetos_lista(request):
    """Lista de projetos + criar projeto."""
    if request.method == "POST":
        nome = (request.POST.get("nome") or "").strip()
        if not nome:
            messages.error(request, "O projeto precisa de um nome.")
            return redirect("projetos_lista")
        p, criado = Projeto.objects.get_or_create(nome=nome, defaults={
            "resumo": (request.POST.get("resumo") or "").strip(),
            "status": request.POST.get("status") or Projeto.Status.PLANEJAMENTO})
        p.instanciar_business_plan()
        messages.success(request, f"Projeto “{nome}” criado." if criado else "Esse projeto já existia.")
        return redirect("projeto_detalhe", pk=p.id)

    projetos = list(Projeto.objects.all())
    for p in projetos:
        p.n_total = p.tarefas.count()
        p.n_afazer = p.tarefas.filter(feita=False).count()
    contexto = contexto_base(
        "projetos", projetos=projetos, status_opcoes=Projeto.Status.choices)
    return render(request, "tarefas/projetos.html", contexto)


@login_required
def projeto_detalhe(request, pk):
    """Detalhe do projeto: business plan (perguntas), status e tarefas (checklist/timeline)."""
    projeto = get_object_or_404(Projeto, pk=pk)
    projeto.instanciar_business_plan()

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "salvar_plano":
            projeto.resumo = (request.POST.get("resumo") or "").strip()
            projeto.status = request.POST.get("status") or projeto.status
            projeto.save(update_fields=["resumo", "status"])
            for r in projeto.respostas.all():
                val = request.POST.get(f"resposta_{r.id}")
                if val is not None and val.strip() != r.resposta:
                    r.resposta = val.strip()
                    r.save(update_fields=["resposta"])
            messages.success(request, "Projeto salvo.")
        elif acao == "add_tarefa":
            titulo = (request.POST.get("titulo") or "").strip()
            if titulo:
                t = Tarefa.objects.create(titulo=titulo, tipo=Tarefa.Tipo.PROJETO, projeto=projeto)
                prazo = (request.POST.get("prazo") or "").strip()
                if prazo:
                    try:
                        t.prazo = date.fromisoformat(prazo)
                        t.save(update_fields=["prazo"])
                    except ValueError:
                        pass
                resp = request.POST.get("responsavel")
                if resp:
                    t.responsaveis.add(resp)
                messages.success(request, "Tarefa do projeto criada.")
        return redirect("projeto_detalhe", pk=pk)

    tarefas = list(projeto.tarefas.prefetch_related("responsaveis", "temas")
                   .order_by("feita", "prazo", "ordem", "id"))
    contexto = contexto_base(
        "projetos", titulo=projeto.nome, projeto=projeto,
        respostas=list(projeto.respostas.all()), tarefas=tarefas,
        status_opcoes=Projeto.Status.choices, pessoas=Pessoa.objects.filter(ativo=True))
    return render(request, "tarefas/projeto_detalhe.html", contexto)


@login_required
def tarefa_toggle(request, pk):
    voltar = request.POST.get("voltar") or "/"
    if not voltar.startswith("/"):
        voltar = "/"
    if request.method == "POST":
        t = Tarefa.objects.filter(pk=pk).first()
        if t:
            t.marcar(not t.feita)
    return redirect(voltar)
