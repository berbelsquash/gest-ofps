from collections import OrderedDict
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from painel.menu import contexto_base

from .models import Evento, Pessoa, Projeto, Tarefa


def _agrupar(tarefas, dim):
    """Agrupa a lista de tarefas pela dimensão escolhida."""
    g = OrderedDict()
    for t in tarefas:
        if dim == "evento":
            chave = t.evento.nome if t.evento_id else "Sem evento"
        elif dim == "projeto":
            chave = t.projeto.nome if t.projeto_id else "Sem projeto"
        elif dim == "todas":
            chave = "Todas as tarefas"
        else:
            chave = t.responsavel.nome if t.responsavel_id else "Sem dono"
        g.setdefault(chave, []).append(t)
    itens = sorted(g.items(), key=lambda kv: (kv[0].startswith("Sem"), kv[0]))
    return [{"titulo": k, "tarefas": v} for k, v in itens]


@login_required
def painel_tarefas(request):
    agrupar = request.GET.get("agrupar", "pessoa")
    status = request.GET.get("status", "afazer")

    qs = Tarefa.objects.select_related("responsavel", "evento", "projeto")
    if status == "afazer":
        qs = qs.filter(feita=False)
    elif status == "feitas":
        qs = qs.filter(feita=True)

    pessoa_id = None
    pessoa_sel = request.GET.get("pessoa")
    if pessoa_sel == "0":
        qs, agrupar, pessoa_id = qs.filter(responsavel__isnull=True), "pessoa", 0
    elif pessoa_sel:
        qs, agrupar, pessoa_id = qs.filter(responsavel_id=pessoa_sel), "pessoa", int(pessoa_sel)
    if request.GET.get("evento"):
        qs, agrupar = qs.filter(evento_id=request.GET["evento"]), "evento"
    if request.GET.get("projeto"):
        qs, agrupar = qs.filter(projeto_id=request.GET["projeto"]), "projeto"

    grupos = _agrupar(list(qs), agrupar)

    # Mini-dash: quantas tarefas a fazer cada pessoa tem.
    cont = {}
    for r_id in Tarefa.objects.filter(feita=False).values_list("responsavel_id", flat=True):
        cont[r_id] = cont.get(r_id, 0) + 1
    pessoas = list(Pessoa.objects.filter(ativo=True))
    for p in pessoas:
        p.a_fazer = cont.get(p.id, 0)

    contexto = contexto_base(
        "tarefas-por-pessoa",
        pessoas=pessoas, sem_dono=cont.get(None, 0), grupos=grupos,
        agrupar=agrupar, status=status, pessoa_id=pessoa_id,
        eventos=Evento.objects.all(), projetos=Projeto.objects.filter(ativo=True),
        total_afazer=Tarefa.objects.filter(feita=False).count(),
        total_feitas=Tarefa.objects.filter(feita=True).count(),
    )
    return render(request, "tarefas/painel.html", contexto)


@login_required
def tarefa_criar(request):
    voltar = request.POST.get("voltar") or "/"
    if not voltar.startswith("/"):
        voltar = "/"
    if request.method == "POST":
        titulo = (request.POST.get("titulo") or "").strip()
        if not titulo:
            messages.error(request, "A tarefa precisa de um título.")
            return redirect(voltar)
        t = Tarefa(titulo=titulo, descricao=(request.POST.get("descricao") or "").strip())
        resp = request.POST.get("responsavel")
        t.responsavel_id = int(resp) if resp else None
        vinc = request.POST.get("vinculo") or ""
        if vinc.startswith("evento:"):
            t.evento_id = int(vinc.split(":", 1)[1])
        elif vinc.startswith("projeto:"):
            t.projeto_id = int(vinc.split(":", 1)[1])
        prazo = (request.POST.get("prazo") or "").strip()
        if prazo:
            try:
                t.prazo = date.fromisoformat(prazo)
            except ValueError:
                pass
        t.save()
        messages.success(request, "Tarefa criada.")
    return redirect(voltar)


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
