import os
import tempfile
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Max, Min, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from financeiro.models import GRUPOS, LancamentoBancario
from painel.menu import contexto_base
from tarefas.models import Evento, Pessoa, Tarefa

from .categorias import CATEGORIAS, SUBCATEGORIAS, categorias_todas
from .importacao import (exportar_atletas, exportar_participacoes,
                         importar_atletas, importar_participacoes)
from .models import Atleta, Participacao


def _eventos_nomes():
    """Nomes dos eventos da base (não-liga), do mais recente ao mais antigo."""
    return list(Evento.objects.exclude(tipo=Evento.Tipo.LIGA)
                .order_by("-data_inicio").values_list("nome", flat=True))


def _pdate(v):
    v = (v or "").strip()
    try:
        return date.fromisoformat(v) if v else None
    except ValueError:
        return None


@login_required
def atletas_lista(request):
    q = (request.GET.get("q") or "").strip()
    filiacao = request.GET.get("filiacao", "")
    regiao = request.GET.get("regiao", "")
    genero = request.GET.get("genero", "")

    qs = Atleta.objects.all()
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(email__icontains=q)
                       | Q(local1__icontains=q) | Q(treinador__icontains=q))
    if filiacao:
        qs = qs.filter(filiacao=filiacao)
    if regiao:
        qs = qs.filter(regiao=regiao)
    if genero:
        qs = qs.filter(genero=genero)

    total = qs.count()
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    def valores(campo):
        return list(Atleta.objects.exclude(**{campo: ""})
                    .values_list(campo, flat=True).distinct().order_by(campo))

    contexto = contexto_base(
        "bases-atletas", page=page, total=total, qs_str=params.urlencode(),
        q=q, filiacao=filiacao, regiao=regiao, genero=genero,
        filiacoes=valores("filiacao"), regioes=valores("regiao"), generos=valores("genero"),
        total_geral=Atleta.objects.count(),
        ativos=Atleta.objects.filter(filiacao="Ativo").count(),
    )
    return render(request, "bases/atletas.html", contexto)


@login_required
def importar_atletas_view(request):
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if not arquivo or not arquivo.name.lower().endswith(".xlsx"):
            messages.error(request, "Envie um arquivo .xlsx da base de atletas.")
            return redirect("bases_atletas")
        fd, caminho = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as destino:
                for chunk in arquivo.chunks():
                    destino.write(chunk)
            criados, atualizados = importar_atletas(caminho)
            messages.success(
                request,
                f"Base atualizada: {criados} novo(s) e {atualizados} atualizado(s) "
                "— sem duplicar nomes.")
        except Exception as erro:
            messages.error(request, f"Não consegui ler a planilha: {erro}")
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
    return redirect("bases_atletas")


@login_required
def exportar_atletas_view(request):
    dados = exportar_atletas()
    resp = HttpResponse(
        dados,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    nome = f"atletas_{timezone.localdate().isoformat()}.xlsx"
    resp["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resp


_MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
          "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


@login_required
def base_financeira(request):
    """Base Financeira: detalhamento completo dos lançamentos, com Categoria,
    Subcategoria e Evento editáveis inline; reconhecimento de evento por data."""
    tipo = request.GET.get("tipo", "")
    grupo = request.GET.get("grupo", "")
    evento_f = request.GET.get("evento", "")
    mes = request.GET.get("mes", "")
    q = (request.GET.get("q") or "").strip()
    sem_evento = request.GET.get("sem_evento", "")

    qs = LancamentoBancario.objects.all()
    if tipo in ("receita", "despesa"):
        qs = qs.filter(tipo=tipo)
    if grupo:
        qs = qs.filter(grupo=grupo)
    if evento_f:
        qs = qs.filter(evento=evento_f)
    if mes.isdigit() and 1 <= int(mes) <= 12:
        qs = qs.filter(data__month=int(mes))
    if sem_evento:
        qs = qs.filter(evento="")
    if q:
        qs = qs.filter(Q(razao_social__icontains=q) | Q(descricao__icontains=q)
                       | Q(categoria__icontains=q))
    qs = qs.order_by("-data", "-id")

    total = qs.count()
    page = Paginator(qs, 80).get_page(request.GET.get("page"))
    for l in page:
        l.valor_abs = abs(l.valor)
        cats = CATEGORIAS.get(l.tipo, [])
        # opções da categoria = taxonomia do tipo + o valor atual (se for antigo)
        l.cat_opcoes = cats + ([l.grupo] if l.grupo and l.grupo not in cats else [])
    params = request.GET.copy()
    params.pop("page", None)

    base = LancamentoBancario.objects.all()
    existentes = set(base.exclude(grupo="").values_list("grupo", flat=True))
    grupos_filtro = categorias_todas() + sorted(existentes - set(categorias_todas()))
    contexto = contexto_base(
        "bases-financeiro",
        page=page, total=total, qs_str=params.urlencode(),
        tipo=tipo, grupo=grupo, evento_f=evento_f, mes=mes, q=q, sem_evento=sem_evento,
        grupos=grupos_filtro, eventos_nomes=_eventos_nomes(),
        sub_receita=SUBCATEGORIAS["receita"], sub_despesa=SUBCATEGORIAS["despesa"],
        meses=list(enumerate(_MESES, start=1)),
        n_total=base.count(), sem_evento_total=base.filter(evento="").count(),
        ultima=base.aggregate(m=Max("importado_em"))["m"],
    )
    return render(request, "bases/financeira.html", contexto)


@login_required
@require_POST
def lancamento_inline(request):
    """Salva Categoria (grupo) / Subcategoria (categoria) / Evento de um
    lançamento direto da linha. Evento só é permitido quando a categoria é
    'Eventos'; ao trocar a categoria para outra, o evento é limpo."""
    obj = LancamentoBancario.objects.filter(pk=request.POST.get("id")).first()
    campo = request.POST.get("campo")
    valor = (request.POST.get("valor") or "").strip()
    if not obj or campo not in ("grupo", "categoria", "evento"):
        return JsonResponse({"ok": False}, status=400)
    if campo == "evento" and obj.grupo != "Eventos":
        return JsonResponse({"ok": False, "erro": "Evento só na categoria Eventos."}, status=400)
    setattr(obj, campo, valor)
    obj.revisado = True
    campos = {campo, "revisado"}
    if campo == "grupo" and valor != "Eventos" and obj.evento:
        obj.evento = ""
        campos.add("evento")
    obj.save(update_fields=list(campos))
    return JsonResponse({"ok": True, "evento_limpo": campo == "grupo" and "evento" in campos})


@login_required
@require_POST
def reconhecer_eventos(request):
    """Atribui evento automaticamente aos lançamentos sem evento:
    - DESPESAS categorizadas como evento (grupo Torneios): pela data.
    - RECEITAS: pelo valor da inscrição + data (usando os valores do evento).
    Só quando o resultado é um único evento; ambíguos ficam para a edição inline."""
    eventos = [e for e in Evento.objects.exclude(tipo=Evento.Tipo.LIGA) if e.data_inicio]
    n_desp = n_rec = 0

    # só lançamentos categorizados como "Eventos" podem receber evento
    for l in (LancamentoBancario.objects
              .filter(evento="", grupo="Eventos", tipo="despesa").exclude(data__isnull=True)):
        achados = {e.nome for e in eventos
                   if (e.data_inicio - timedelta(days=5))
                   <= l.data <= ((e.data_fim or e.data_inicio) + timedelta(days=5))}
        if len(achados) == 1:
            l.evento = achados.pop()
            l.revisado = True
            l.save(update_fields=["evento", "revisado"])
            n_desp += 1

    for l in (LancamentoBancario.objects
              .filter(evento="", grupo="Eventos", tipo="receita").exclude(data__isnull=True)):
        v = int(round(abs(float(l.valor))))
        achados = {e.nome for e in eventos
                   if v in e.valores_set
                   and (e.data_inicio - timedelta(days=45))
                   <= l.data <= ((e.data_fim or e.data_inicio) + timedelta(days=5))}
        if len(achados) == 1:
            l.evento = achados.pop()
            l.revisado = True
            l.save(update_fields=["evento", "revisado"])
            n_rec += 1

    messages.success(
        request,
        f"Reconhecidos: {n_desp} despesa(s) de evento por data e "
        f"{n_rec} receita(s) por valor + data.")
    return redirect("bases_financeiro")


@login_required
def eventos_base(request):
    """Base de Eventos: cadastro editável dos eventos (alimenta a associação do
    financeiro e o vínculo das participações). Filtro de próximos/todos/passados."""
    tipo = request.GET.get("tipo", "")
    quando = request.GET.get("quando", "proximos")
    hoje = timezone.localdate()

    qs = Evento.objects.all()
    if tipo:
        qs = qs.filter(tipo=tipo)
    if quando == "proximos":
        qs = qs.filter(Q(data_fim__gte=hoje) | Q(data_fim__isnull=True, data_inicio__gte=hoje)
                       ).order_by("data_inicio", "nome")
    elif quando == "passados":
        qs = qs.filter(data_fim__lt=hoje).order_by("-data_inicio", "nome")
    else:
        qs = qs.order_by("-data_inicio", "nome")

    eventos = list(qs)
    for e in eventos:
        e.n_tarefas = e.tarefas.count()
    contexto = contexto_base(
        "bases-eventos", eventos=eventos, tipo=tipo, quando=quando,
        tipos=Evento.Tipo.choices, total=Evento.objects.count(),
    )
    return render(request, "bases/eventos.html", contexto)


@login_required
@require_POST
def evento_editar(request):
    """Salva a edição de um evento (via modal na Base de Eventos)."""
    ev = Evento.objects.filter(pk=request.POST.get("id")).first()
    if ev:
        def d(chave):
            v = (request.POST.get(chave) or "").strip()
            try:
                return date.fromisoformat(v) if v else None
            except ValueError:
                return None
        nome = (request.POST.get("nome") or "").strip()
        if nome:
            ev.nome = nome
        ev.tipo = request.POST.get("tipo") or ev.tipo
        ev.tier = (request.POST.get("tier") or "").strip()
        ev.valores = (request.POST.get("valores") or "").strip()
        ev.data_inicio = d("data_inicio")
        ev.data_fim = d("data_fim")
        ev.inscricoes_ate = d("inscricoes_ate")
        ev.save()
        messages.success(request, f"Evento atualizado: {ev.nome}.")
        return redirect(f"/s/bases-eventos/?abrir={ev.id}")
    return redirect("bases_eventos")


@login_required
@require_POST
def evento_criar(request):
    """Cria um evento e já gera as tarefas dele (checklist + comunicações)."""
    from tarefas.gerar import gerar_para_evento
    nome = (request.POST.get("nome") or "").strip()
    if not nome:
        messages.error(request, "O evento precisa de um nome.")
        return redirect("bases_eventos")
    if Evento.objects.filter(nome=nome).exists():
        messages.error(request, "Já existe um evento com esse nome.")
        return redirect("bases_eventos")
    ev = Evento.objects.create(
        nome=nome, tipo=request.POST.get("tipo") or Evento.Tipo.CAMPEONATO,
        tier=(request.POST.get("tier") or "").strip(),
        valores=(request.POST.get("valores") or "").strip(),
        data_inicio=_pdate(request.POST.get("data_inicio")),
        data_fim=_pdate(request.POST.get("data_fim")),
        inscricoes_ate=_pdate(request.POST.get("inscricoes_ate")))
    nc, nm = gerar_para_evento(ev)
    messages.success(
        request, f"Evento “{nome}” criado com {nc + nm} tarefas geradas "
        "(checklist + comunicações). Ajuste ou exclua o que precisar.")
    return redirect(f"/s/bases-eventos/?abrir={ev.id}")


@login_required
def evento_painel(request, pk):
    """Conteúdo do popup do evento: infos + tarefas (carregado via AJAX)."""
    ev = get_object_or_404(Evento, pk=pk)
    tarefas = list(ev.tarefas.prefetch_related("responsaveis").order_by("prazo", "ordem", "id"))
    contexto = {
        "evento": ev, "tarefas": tarefas,
        "pessoas": Pessoa.objects.filter(ativo=True),
        "tipos": Evento.Tipo.choices,
    }
    return render(request, "bases/_evento_painel.html", contexto)


@login_required
@require_POST
def evento_tarefa_salvar(request):
    """Edita um campo de uma tarefa de evento (título, data, responsável, feita)."""
    t = Tarefa.objects.filter(pk=request.POST.get("id")).first()
    if not t:
        return JsonResponse({"ok": False}, status=400)
    campo = request.POST.get("campo")
    if campo == "titulo":
        t.titulo = (request.POST.get("valor") or "").strip() or t.titulo
        t.save(update_fields=["titulo"])
    elif campo == "prazo":
        t.prazo = _pdate(request.POST.get("valor"))
        t.save(update_fields=["prazo"])
    elif campo == "responsavel":
        pid = request.POST.get("valor")
        if request.POST.get("marcado") == "1":
            t.responsaveis.add(pid)
        else:
            t.responsaveis.remove(pid)
    elif campo == "feita":
        t.marcar(request.POST.get("valor") == "1")
    else:
        return JsonResponse({"ok": False}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def evento_tarefa_excluir(request):
    Tarefa.objects.filter(pk=request.POST.get("id")).exclude(evento__isnull=True).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def evento_tarefa_add(request):
    ev = Evento.objects.filter(pk=request.POST.get("evento")).first()
    if not ev:
        return JsonResponse({"ok": False}, status=400)
    Tarefa.objects.create(
        titulo=(request.POST.get("titulo") or "Nova tarefa").strip(),
        tipo=Tarefa.Tipo.EVENTO, evento=ev, prazo=_pdate(request.POST.get("prazo")))
    return JsonResponse({"ok": True})


@login_required
def participacoes(request):
    """Base de Participações: resultados dos atletas nos eventos, ligados à Base
    de Atletas pelo nome. Busca, filtro por campeonato e por 'sem atleta'."""
    q = (request.GET.get("q") or "").strip()
    campeonato = request.GET.get("campeonato", "")
    so_sem = request.GET.get("sem_atleta", "")

    qs = Participacao.objects.select_related("atleta")
    if q:
        qs = qs.filter(Q(atleta_nome__icontains=q) | Q(campeonato__icontains=q)
                       | Q(academia__icontains=q))
    if campeonato:
        qs = qs.filter(campeonato=campeonato)
    if so_sem:
        qs = qs.filter(atleta__isnull=True)

    total = qs.count()
    page = Paginator(qs, 60).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    n_total = Participacao.objects.count()
    n_casados = Participacao.objects.exclude(atleta__isnull=True).count()
    contexto = contexto_base(
        "bases-participacoes", page=page, total=total, qs_str=params.urlencode(),
        q=q, campeonato=campeonato, so_sem=so_sem,
        campeonatos=list(Participacao.objects.values_list("campeonato", flat=True)
                         .distinct().order_by("campeonato")),
        n_total=n_total, n_casados=n_casados, n_sem=n_total - n_casados,
    )
    return render(request, "bases/participacoes.html", contexto)


@login_required
def importar_participacoes_view(request):
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if not arquivo or not arquivo.name.lower().endswith(".xlsx"):
            messages.error(request, "Envie um arquivo .xlsx de resultados/participações.")
            return redirect("bases_participacoes")
        fd, caminho = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as destino:
                for chunk in arquivo.chunks():
                    destino.write(chunk)
            total, casados, sem = importar_participacoes(caminho)
            messages.success(
                request,
                f"{total} participações importadas — {casados} ligadas a atletas, "
                f"{sem} sem atleta (grafia a conciliar).")
        except Exception as erro:
            messages.error(request, f"Não consegui ler a planilha: {erro}")
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
    return redirect("bases_participacoes")


@login_required
def exportar_participacoes_view(request):
    dados = exportar_participacoes()
    resp = HttpResponse(
        dados,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    nome = f"participacoes_{timezone.localdate().isoformat()}.xlsx"
    resp["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resp
