import calendar
import os
import tempfile
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import Abs, ExtractMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from assinaturas.models import AssinaturaVindi, PlanoVindi, RecebimentoVindi
from painel.menu import contexto_base

from .eventos import NOMES_EVENTOS, sugerir_evento
from .importacao import importar_extrato
from .models import GRUPOS, LancamentoBancario, LancamentoFinanceiro, MESES_PT

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _anos_fin():
    anos = list(LancamentoFinanceiro.objects.values_list("ano", flat=True).distinct().order_by("-ano"))
    return anos or [2026]


def _add_meses(d, n):
    total = d.month - 1 + n
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


# =========================================================================
# Páginas baseadas no ledger categorizado (planilha até maio + extrato jun+)
# =========================================================================

def _pivot_fin(qs):
    dados = qs.values("grupo", "mes").annotate(s=Sum("valor"))
    grupos = defaultdict(lambda: defaultdict(Decimal))
    tot = defaultdict(Decimal)
    for row in dados:
        g = row["grupo"] or "(sem grupo)"
        v = row["s"] or Decimal("0")
        grupos[g][row["mes"]] += v
        tot[row["mes"]] += v
    linhas = []
    for g in sorted(grupos, key=lambda x: -sum(grupos[x].values())):
        meses = [grupos[g].get(m, Decimal("0")) for m in range(1, 13)]
        linhas.append({"grupo": g, "meses": meses, "total": sum(meses)})
    totais = [tot.get(m, Decimal("0")) for m in range(1, 13)]
    return linhas, totais, sum(totais)


def _pagina_ledger(request, tipo, template, slug):
    ano = int(request.GET.get("ano") or 2026)
    grupo_sel = request.GET.get("grupo", "")
    qs = LancamentoFinanceiro.objects.filter(tipo=tipo, ano=ano)
    linhas, totais, total = _pivot_fin(qs)
    det = qs
    if grupo_sel:
        det = det.filter(grupo=grupo_sel)
    det = list(det.order_by("mes", "-id")[:400])
    contexto = contexto_base(
        slug, ano=ano, anos=_anos_fin(), meses=MESES,
        linhas=linhas, totais=totais, total=total,
        detalhe=det, grupos=[l["grupo"] for l in linhas], grupo_sel=grupo_sel,
    )
    return render(request, template, contexto)


def _anos_banco():
    anos = [d.year for d in LancamentoBancario.objects.dates("data", "year", order="DESC")]
    return anos or [2026]


def _pivot_extrato(qs):
    dados = qs.annotate(m=ExtractMonth("data")).values("grupo", "m").annotate(s=Sum("valor"))
    grupos = defaultdict(lambda: defaultdict(Decimal))
    tot = defaultdict(Decimal)
    for row in dados:
        g = row["grupo"] or "(a classificar)"
        v = abs(row["s"] or Decimal("0"))
        grupos[g][row["m"]] += v
        tot[row["m"]] += v
    linhas = []
    for g in sorted(grupos, key=lambda x: -sum(grupos[x].values())):
        meses = [grupos[g].get(m, Decimal("0")) for m in range(1, 13)]
        linhas.append({"grupo": g, "meses": meses, "total": sum(meses)})
    totais = [tot.get(m, Decimal("0")) for m in range(1, 13)]
    return linhas, totais, sum(totais)


def _ordenar_det(qs, ordenar):
    """Ordena os lançamentos por data ou por valor (maior/menor magnitude)."""
    if ordenar == "maior":
        return qs.annotate(_mag=Abs("valor")).order_by("-_mag", "-data")
    if ordenar == "menor":
        return qs.annotate(_mag=Abs("valor")).order_by("_mag", "-data")
    return qs.order_by("data", "-id")


def _pagina_extrato(request, tipo, template, slug):
    """Página de Despesas/Receitas: números no topo + lançamentos do extrato."""
    ano = int(request.GET.get("ano") or 2026)
    grupo_sel = request.GET.get("grupo", "")
    mes_sel = int(request.GET.get("mes") or 0)
    ordenar = request.GET.get("ordenar", "data")
    qs = LancamentoBancario.objects.filter(tipo=tipo, data__year=ano)
    # Total por mês (valores absolutos).
    mes_tot = {m: Decimal("0") for m in range(1, 13)}
    for row in qs.annotate(m=ExtractMonth("data")).values("m").annotate(s=Sum("valor")):
        if row["m"]:
            mes_tot[row["m"]] = abs(row["s"] or Decimal("0"))
    totais = [mes_tot[m] for m in range(1, 13)]
    total = sum(totais)
    ativos = [m for m in range(1, 13) if mes_tot[m] > 0]
    maior_m = max(ativos, key=lambda m: mes_tot[m]) if ativos else 0
    # Lançamentos com filtros (mês, grupo) e ordenação.
    det = qs
    if mes_sel:
        det = det.filter(data__month=mes_sel)
    if grupo_sel:
        det = det.filter(grupo=grupo_sel)
    det = list(_ordenar_det(det, ordenar)[:600])
    for l in det:
        l.valor_abs = abs(l.valor)
        l.valor_str = f"{abs(l.valor):.2f}"
    grupos = sorted(set(qs.exclude(grupo="").values_list("grupo", flat=True)))
    contexto = contexto_base(
        slug, ano=ano, anos=_anos_banco(), meses=MESES,
        total=total, totais=totais,
        maior_valor=(mes_tot[maior_m] if maior_m else Decimal("0")),
        maior_nome=(MESES_PT[maior_m - 1] if maior_m else "—"),
        media=(total / len(ativos)) if ativos else Decimal("0"),
        detalhe=det, grupos=grupos, grupo_sel=grupo_sel,
        mes_sel=mes_sel, ordenar=ordenar, meses_filtro=list(enumerate(MESES_PT, 1)),
        grupos_todos=[g[0] for g in GRUPOS],
    )
    return render(request, template, contexto)


@login_required
def despesas(request):
    return _pagina_extrato(request, "despesa", "financeiro/despesas.html", "financeiro-despesas")


SALDO_INICIAL_2026 = Decimal("3875.03")  # saldo da conta em 31/12/2025 (do extrato)


@login_required
def receitas(request):
    return _pagina_extrato(request, "receita", "financeiro/receitas.html", "financeiro-receitas")


def _parse_valor(s):
    """Lê um valor digitado (aceita vírgula ou ponto) e devolve Decimal positivo."""
    s = (s or "").strip().replace("R$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return abs(Decimal(s))
    except (InvalidOperation, ValueError):
        return None


@login_required
def editar_lancamento(request, pk):
    """Salva a edição feita no modal das telas de Despesas/Receitas."""
    obj = get_object_or_404(LancamentoBancario, pk=pk)
    voltar = request.POST.get("voltar") or "/s/financeiro-despesas/"
    if not voltar.startswith("/"):
        voltar = "/s/financeiro-despesas/"
    if request.method == "POST":
        tipo = request.POST.get("tipo") or obj.tipo
        valor = _parse_valor(request.POST.get("valor"))
        if valor is not None:
            obj.valor = valor if tipo == "receita" else -valor
        obj.tipo = tipo
        obj.grupo = request.POST.get("grupo", "").strip()
        obj.categoria = request.POST.get("categoria", "").strip()
        obj.evento = request.POST.get("evento", "").strip()
        obj.razao_social = request.POST.get("razao_social", "").strip()
        data_str = (request.POST.get("data") or "").strip()
        if data_str:
            try:
                obj.data = date.fromisoformat(data_str)
            except ValueError:
                pass
        obj.revisado = bool(request.POST.get("revisado"))
        obj.classificado = True
        obj.save()
        messages.success(request, "Lançamento atualizado com sucesso.")
    return redirect(voltar)


@login_required
def importar_extrato_view(request):
    """Recebe o .xlsx do extrato enviado pelo usuário e reimporta os lançamentos."""
    voltar = request.POST.get("voltar") or "/s/financeiro-despesas/"
    if not voltar.startswith("/"):
        voltar = "/s/financeiro-despesas/"
    arquivo = request.FILES.get("arquivo")
    if request.method == "POST" and arquivo:
        if not arquivo.name.lower().endswith(".xlsx"):
            messages.error(request, "Envie um arquivo .xlsx (extrato do Banco do Brasil).")
            return redirect(voltar)
        fd, caminho = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as destino:
                for chunk in arquivo.chunks():
                    destino.write(chunk)
            n = importar_extrato(caminho)
            messages.success(
                request,
                f"Extrato importado: {n} lançamentos. As correções marcadas como "
                "'revisado' foram preservadas.",
            )
        except Exception as erro:
            messages.error(request, f"Não consegui ler esse extrato: {erro}")
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
    else:
        messages.error(request, "Selecione um arquivo .xlsx para importar.")
    return redirect(voltar)


@login_required
def balanco(request):
    """Balanço: saldo atual da conta + resumo mês a mês (receitas, despesas, resultado)."""
    ano = int(request.GET.get("ano") or 2026)
    rec = {m: Decimal("0") for m in range(1, 13)}
    desp = {m: Decimal("0") for m in range(1, 13)}
    for row in (LancamentoBancario.objects.filter(data__year=ano)
                .annotate(m=ExtractMonth("data")).values("m", "tipo").annotate(s=Sum("valor"))):
        if row["m"]:
            if row["tipo"] == "receita":
                rec[row["m"]] = row["s"] or Decimal("0")
            else:
                desp[row["m"]] = abs(row["s"] or Decimal("0"))
    saldo_inicial = SALDO_INICIAL_2026 if ano == 2026 else Decimal("0")
    rec_list = [rec[m] for m in range(1, 13)]
    desp_list = [desp[m] for m in range(1, 13)]
    result_list = [rec[m] - desp[m] for m in range(1, 13)]
    tot_rec = sum(rec_list)
    tot_desp = sum(desp_list)
    rows = [
        {"label": "Receitas", "valores": rec_list, "total": tot_rec, "classe": "val-pos"},
        {"label": "Despesas", "valores": desp_list, "total": tot_desp, "classe": "val-neg"},
        {"label": "Total (resultado)", "valores": result_list, "total": tot_rec - tot_desp, "classe": "col-total"},
    ]
    # Linha de saldo na conta (acumulado), só até o último mês com movimento.
    ultimo = max((m for m in range(1, 13) if rec[m] or desp[m]), default=0)
    saldo_list, acum = [], saldo_inicial
    for m in range(1, 13):
        acum += rec[m] - desp[m]
        saldo_list.append(acum if m <= ultimo else Decimal("0"))
    rows.append({"label": "Saldo na conta", "valores": saldo_list,
                 "total": saldo_inicial + tot_rec - tot_desp, "classe": "col-total"})

    # --- Projeção do ano: realizado (até o mês atual) + previsto (depois) ---
    hoje = timezone.localdate()
    mes_atual = hoje.month if ano == hoje.year else 12
    vindi_prev = _vindi_previsto(ano, hoje)
    # Despesa futura prevista = média mensal SÓ das recorrentes definidas pela FPS:
    # folha (sem Aline, que saiu) + contabilidade + taxas Vindi/Yapay + telefone (Claro) + Mailchimp.
    # Squash Wall (aluguel só no início do ano) e torneios NÃO entram na recorrência.
    recorrente_filtro = (
        (Q(grupo="Folha") & ~Q(categoria="Aline Rocha"))
        | Q(categoria__in=["Contabilidade", "Taxas Vindi/Yapay", "Telefone", "Mailchimp"])
    )
    recorrente_total = abs(
        LancamentoBancario.objects.filter(
            tipo="despesa", data__year=ano, data__month__lte=mes_atual
        ).filter(recorrente_filtro).aggregate(s=Sum("valor"))["s"] or Decimal("0")
    )
    media_desp = (recorrente_total / mes_atual) if mes_atual else Decimal("0")
    rec_proj, desp_proj = [], []
    for m in range(1, 13):
        futuro = ano > hoje.year or (ano == hoje.year and m > mes_atual)
        rec_proj.append(vindi_prev[m] if futuro else rec[m])
        desp_proj.append(media_desp if futuro else desp[m])
    result_proj = [rec_proj[i] - desp_proj[i] for i in range(12)]
    tot_rec_proj, tot_desp_proj = sum(rec_proj), sum(desp_proj)
    rows_proj = [
        {"label": "Receitas", "valores": rec_proj, "total": tot_rec_proj, "classe": "val-pos"},
        {"label": "Despesas", "valores": desp_proj, "total": tot_desp_proj, "classe": "val-neg"},
        {"label": "Total (resultado)", "valores": result_proj, "total": tot_rec_proj - tot_desp_proj, "classe": "col-total"},
    ]
    saldo_proj_list, acum = [], saldo_inicial
    for i in range(12):
        acum += rec_proj[i] - desp_proj[i]
        saldo_proj_list.append(acum)
    rows_proj.append({"label": "Saldo projetado", "valores": saldo_proj_list,
                      "total": saldo_inicial + tot_rec_proj - tot_desp_proj, "classe": "col-total"})

    contexto = contexto_base(
        "financeiro-balanco", ano=ano, anos=_anos_banco(), meses=MESES, rows=rows,
        saldo_inicial=saldo_inicial, total_rec=tot_rec, total_desp=tot_desp,
        saldo_atual=saldo_inicial + tot_rec - tot_desp,
        rows_proj=rows_proj, mes_atual_nome=MESES[mes_atual - 1],
        saldo_fim_ano=saldo_inicial + tot_rec_proj - tot_desp_proj,
    )
    return render(request, "financeiro/balanco.html", contexto)


@login_required
def por_evento(request):
    """Resultado por evento — direto do extrato (lançamentos vinculados a cada torneio)."""
    ano = int(request.GET.get("ano") or 2026)
    evento_sel = request.GET.get("evento", "")
    if evento_sel:
        lancs = list(LancamentoBancario.objects.filter(
            data__year=ano, evento=evento_sel).order_by("data", "-id"))
        rec = desp = Decimal("0")
        for l in lancs:
            l.valor_abs = abs(l.valor)
            l.valor_str = f"{l.valor_abs:.2f}"
            if l.tipo == "receita":
                rec += l.valor_abs
            else:
                desp += l.valor_abs
        contexto = contexto_base(
            "financeiro-eventos", ano=ano, anos=_anos_banco(),
            evento_sel=evento_sel, detalhe=lancs,
            total_rec=rec, total_desp=desp, saldo=rec - desp,
            grupos_todos=[g[0] for g in GRUPOS],
        )
        return render(request, "financeiro/evento_detalhe.html", contexto)
    dados = (LancamentoBancario.objects.filter(data__year=ano).exclude(evento="")
             .values("evento").annotate(
                 receita=Sum("valor", filter=Q(tipo="receita")),
                 despesa=Sum("valor", filter=Q(tipo="despesa")),
                 n=Count("id")).order_by("evento"))
    eventos = []
    for row in dados:
        rec = row["receita"] or Decimal("0")
        desp = abs(row["despesa"] or Decimal("0"))
        eventos.append({"evento": row["evento"], "receita": rec, "despesa": desp,
                        "saldo": rec - desp, "n": row["n"]})
    eventos.sort(key=lambda e: -(e["receita"] + e["despesa"]))
    contexto = contexto_base("financeiro-eventos", ano=ano, anos=_anos_banco(), eventos=eventos)
    return render(request, "financeiro/eventos.html", contexto)


@login_required
def revisar_eventos(request):
    """Propõe (e aplica após revisão) o evento de cada lançamento do extrato."""
    if request.method == "POST":
        n = 0
        for pk in request.POST.getlist("id"):
            novo = (request.POST.get(f"evento_{pk}") or "").strip()
            obj = LancamentoBancario.objects.filter(pk=pk).first()
            if obj and novo != (obj.evento or ""):
                obj.evento = novo
                obj.revisado = True
                obj.save(update_fields=["evento", "revisado"])
                n += 1
        messages.success(request, f"{n} lançamento(s) vinculados a eventos.")
        qs_str = request.POST.get("qs", "")
        return redirect("/s/financeiro-eventos-revisar/" + (f"?{qs_str}" if qs_str else ""))

    tipo_f = request.GET.get("tipo", "")
    so_sug = request.GET.get("sug", "1")
    qs = LancamentoBancario.objects.filter(data__year=2026, evento="")
    if tipo_f in ("despesa", "receita"):
        qs = qs.filter(tipo=tipo_f)
    linhas = []
    for l in qs.order_by("data", "-id"):
        sug, motivo = sugerir_evento(l.data, l.valor, l.tipo, l.grupo, l.categoria)
        if so_sug == "1" and not sug:
            continue
        l.valor_abs = abs(l.valor)
        l.sugestao = sug or ""
        l.motivo = motivo or ""
        linhas.append(l)
    paginator = Paginator(linhas, 120)
    page = paginator.get_page(request.GET.get("page") or 1)
    params = request.GET.copy()
    params.pop("page", None)
    contexto = contexto_base(
        "financeiro-eventos-revisar", eventos=NOMES_EVENTOS, page=page,
        tipo_f=tipo_f, so_sug=so_sug, qs_str=params.urlencode(), total=len(linhas),
    )
    return render(request, "financeiro/revisar_eventos.html", contexto)


# =========================================================================
# Conciliação e previsão (baseadas no extrato bancário / Vindi)
# =========================================================================

def _mes_dict(qs, campo="data", absoluto=False):
    d = {m: Decimal("0") for m in range(1, 13)}
    for row in qs.annotate(m=ExtractMonth(campo)).values("m").annotate(s=Sum("valor")):
        if row["m"]:
            v = row["s"] or Decimal("0")
            d[row["m"]] = abs(v) if absoluto else v
    return d


def _vindi_previsto(ano, hoje):
    previsto = {m: Decimal("0") for m in range(1, 13)}
    ativos = AssinaturaVindi.objects.exclude(status="canceled").exclude(
        tipo=PlanoVindi.Tipo.IGNORAR
    ).filter(valor_ciclo__gt=0, proxima_cobranca__isnull=False)
    for a in ativos:
        intervalo = max(1, a.intervalo_meses or 1)
        d = a.proxima_cobranca
        guarda = 0
        while d.year <= ano and guarda < 240:
            if d.year == ano and d.month > hoje.month:
                previsto[d.month] += a.valor_ciclo
            d = _add_meses(d, intervalo)
            guarda += 1
            if d.year > ano:
                break
    return previsto


@login_required
def conciliacao(request):
    ano = int(request.GET.get("ano") or 2026)
    vindi = _mes_dict(RecebimentoVindi.objects.filter(data_pagamento__year=ano), campo="data_pagamento")
    conta = _mes_dict(LancamentoBancario.objects.filter(
        tipo="receita", grupo="Cartão/Vindi", data__year=ano))
    linhas = []
    tot_v = tot_c = Decimal("0")
    acum = Decimal("0")
    for m in range(1, 13):
        v, c = vindi[m], conta[m]
        dif = v - c
        acum += dif
        tot_v += v
        tot_c += c
        linhas.append({"mes": MESES[m - 1], "vindi": v, "conta": c, "dif": dif, "acum": acum})
    contexto = contexto_base(
        "financeiro-conciliacao", ano=ano, anos=[ano], linhas=linhas,
        tot_vindi=tot_v, tot_conta=tot_c, a_receber=tot_v - tot_c,
    )
    return render(request, "financeiro/conciliacao.html", contexto)


@login_required
def previsao(request):
    """Fechamento: realizado (ledger) + previsto (receita Vindi / despesa média)."""
    ano = int(request.GET.get("ano") or 2026)
    hoje = timezone.localdate()
    mes_atual = hoje.month if ano == hoje.year else 12

    rec_real = {m: Decimal("0") for m in range(1, 13)}
    desp_real = {m: Decimal("0") for m in range(1, 13)}
    for row in (LancamentoFinanceiro.objects.filter(ano=ano)
                .values("mes", "tipo").annotate(s=Sum("valor"))):
        alvo = rec_real if row["tipo"] == "receita" else desp_real
        alvo[row["mes"]] = row["s"] or Decimal("0")

    vindi_prev = _vindi_previsto(ano, hoje)
    desp_passada = sum(desp_real[m] for m in range(1, mes_atual + 1))
    media_desp = (desp_passada / mes_atual) if mes_atual else Decimal("0")

    linhas = []
    tot_rec = tot_desp = Decimal("0")
    for m in range(1, 13):
        futuro = ano > hoje.year or (ano == hoje.year and m > mes_atual)
        if futuro:
            rec, desp = vindi_prev[m], media_desp
        else:
            rec, desp = rec_real[m], desp_real[m]
        tot_rec += rec
        tot_desp += desp
        linhas.append({"mes": MESES[m - 1], "receita": rec, "despesa": desp,
                       "saldo": rec - desp, "futuro": futuro})

    contexto = contexto_base(
        "financeiro-previsao", ano=ano, anos=_anos_fin(), linhas=linhas,
        tot_rec=tot_rec, tot_desp=tot_desp, fechamento=tot_rec - tot_desp,
        media_desp=media_desp,
    )
    return render(request, "financeiro/previsao.html", contexto)
