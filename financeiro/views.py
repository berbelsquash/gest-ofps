import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import render
from django.utils import timezone

from assinaturas.models import AssinaturaVindi, PlanoVindi, RecebimentoVindi
from painel.menu import contexto_base

from .models import LancamentoBancario, LancamentoFinanceiro

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


@login_required
def despesas(request):
    """Despesas mês a mês — direto do extrato (data e descrição como no banco)."""
    ano = int(request.GET.get("ano") or 2026)
    grupo_sel = request.GET.get("grupo", "")
    qs = LancamentoBancario.objects.filter(tipo="despesa", data__year=ano)
    linhas, totais, total = _pivot_extrato(qs)
    det = qs
    if grupo_sel:
        det = det.filter(grupo=grupo_sel)
    det = list(det.order_by("data", "-id")[:600])
    for l in det:
        l.valor_abs = abs(l.valor)
    contexto = contexto_base(
        "financeiro-despesas", ano=ano, anos=_anos_banco(), meses=MESES,
        linhas=linhas, totais=totais, total=total,
        detalhe=det, grupos=[l["grupo"] for l in linhas], grupo_sel=grupo_sel,
    )
    return render(request, "financeiro/despesas.html", contexto)


SALDO_INICIAL_2026 = Decimal("3875.03")  # saldo da conta em 31/12/2025 (do extrato)


@login_required
def receitas(request):
    """Receitas mês a mês — direto do extrato (data e descrição como no banco)."""
    ano = int(request.GET.get("ano") or 2026)
    grupo_sel = request.GET.get("grupo", "")
    qs = LancamentoBancario.objects.filter(tipo="receita", data__year=ano)
    linhas, totais, total = _pivot_extrato(qs)
    det = qs
    if grupo_sel:
        det = det.filter(grupo=grupo_sel)
    det = list(det.order_by("data", "-id")[:600])
    contexto = contexto_base(
        "financeiro-receitas", ano=ano, anos=_anos_banco(), meses=MESES,
        linhas=linhas, totais=totais, total=total,
        detalhe=det, grupos=[l["grupo"] for l in linhas], grupo_sel=grupo_sel,
    )
    return render(request, "financeiro/receitas.html", contexto)


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
    ano = int(request.GET.get("ano") or 2026)
    dados = (LancamentoFinanceiro.objects.filter(ano=ano).exclude(evento="")
             .values("evento").annotate(
                 receita=Sum("valor", filter=Q(tipo="receita")),
                 despesa=Sum("valor", filter=Q(tipo="despesa")),
                 n=Count("id")).order_by("evento"))
    eventos = []
    for row in dados:
        rec = row["receita"] or Decimal("0")
        desp = row["despesa"] or Decimal("0")
        eventos.append({"evento": row["evento"], "receita": rec, "despesa": desp,
                        "saldo": rec - desp, "n": row["n"]})
    contexto = contexto_base("financeiro-eventos", ano=ano, anos=_anos_fin(), eventos=eventos)
    return render(request, "financeiro/eventos.html", contexto)


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
