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


@login_required
def despesas(request):
    return _pagina_ledger(request, "despesa", "financeiro/despesas.html", "financeiro-despesas")


@login_required
def receitas(request):
    return _pagina_ledger(request, "receita", "financeiro/receitas.html", "financeiro-receitas")


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
