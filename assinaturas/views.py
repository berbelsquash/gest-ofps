import calendar
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from painel.menu import contexto_base

from .models import AssinaturaVindi, PlanoVindi, RecebimentoVindi
from .sincronizacao import executar_sincronizacao

# Tipos oferecidos nos filtros (sem "outros"/"ignorar").
TIPOS_FILTRO = [
    (t.value, t.label)
    for t in PlanoVindi.Tipo
    if t.value not in ("outros", "ignorar")
]

MESES_PT = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def _add_meses(d, n):
    total = d.month - 1 + n
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


@login_required
def adimplencia(request):
    """Aba 1 — filiados ATIVOS com status de pagamento, com filtro por tipo."""
    tipo_sel = request.GET.get("tipo", "")
    qs = AssinaturaVindi.objects.exclude(tipo=PlanoVindi.Tipo.IGNORAR).exclude(status="canceled")
    if tipo_sel:
        qs = qs.filter(tipo=tipo_sel)
    qs = qs.order_by("cliente_nome")

    total = qs.count()
    inadimplentes = qs.filter(inadimplente_desde__isnull=False).count()
    em_dia = total - inadimplentes
    ultima = AssinaturaVindi.objects.aggregate(m=Max("atualizado_em"))["m"]

    contexto = contexto_base(
        "assinaturas-adimplencia",
        assinaturas=qs,
        total=total,
        em_dia=em_dia,
        inadimplentes=inadimplentes,
        tipo_sel=tipo_sel,
        tipos=TIPOS_FILTRO,
        ultima_sync=ultima,
    )
    return render(request, "assinaturas/adimplencia.html", contexto)


@login_required
def recebimentos(request):
    """Aba 2 — histórico de pagamentos recebidos (faturas pagas)."""
    tipo_sel = request.GET.get("tipo", "")
    ano_sel = request.GET.get("ano", "")
    busca = request.GET.get("q", "").strip()

    qs = RecebimentoVindi.objects.all()
    if tipo_sel:
        qs = qs.filter(tipo=tipo_sel)
    if ano_sel.isdigit():
        qs = qs.filter(data_pagamento__year=int(ano_sel))
    if busca:
        qs = qs.filter(cliente_nome__icontains=busca)
    qs = qs.order_by("-data_pagamento")

    total_valor = qs.aggregate(s=Sum("valor"))["s"] or 0
    total_qtd = qs.count()
    anos = [d.year for d in RecebimentoVindi.objects.dates("data_pagamento", "year", order="DESC")]

    contexto = contexto_base(
        "recebimentos",
        recebimentos=qs[:500],
        total_valor=total_valor,
        total_qtd=total_qtd,
        mostrando=min(total_qtd, 500),
        tipo_sel=tipo_sel,
        ano_sel=ano_sel,
        busca=busca,
        tipos=TIPOS_FILTRO,
        anos=anos,
    )
    return render(request, "assinaturas/recebimentos.html", contexto)


@login_required
def inadimplencia(request):
    """Aba 3 — inadimplentes e cancelamentos, com detector de re-assinatura."""
    tipo_sel = request.GET.get("tipo", "")

    ativas_emdia = set(
        AssinaturaVindi.objects.exclude(status="canceled")
        .filter(inadimplente_desde__isnull=True)
        .values_list("cliente_vindi_id", flat=True)
    )
    qualquer_ativa = set(
        AssinaturaVindi.objects.exclude(status="canceled").values_list("cliente_vindi_id", flat=True)
    )

    inad_qs = (
        AssinaturaVindi.objects.exclude(tipo=PlanoVindi.Tipo.IGNORAR)
        .exclude(status="canceled")
        .filter(inadimplente_desde__isnull=False)
    )
    canc_qs = AssinaturaVindi.objects.exclude(tipo=PlanoVindi.Tipo.IGNORAR).filter(status="canceled")
    if tipo_sel:
        inad_qs = inad_qs.filter(tipo=tipo_sel)
        canc_qs = canc_qs.filter(tipo=tipo_sel)

    inadimplentes = list(inad_qs.order_by("inadimplente_desde"))
    for a in inadimplentes:
        a.tem_outra = a.cliente_vindi_id is not None and a.cliente_vindi_id in ativas_emdia

    total_canc = canc_qs.count()
    cancelados = list(canc_qs.order_by("-cancelada_em")[:500])
    for a in cancelados:
        a.re_assinou = a.cliente_vindi_id is not None and a.cliente_vindi_id in qualquer_ativa

    canc_clientes = set(canc_qs.values_list("cliente_vindi_id", flat=True))
    voltaram = len((canc_clientes & qualquer_ativa) - {None})

    contexto = contexto_base(
        "inadimplencia-cancelamentos",
        inadimplentes=inadimplentes,
        cancelados=cancelados,
        total_inad=len(inadimplentes),
        total_canc=total_canc,
        mostrando_canc=min(total_canc, 500),
        voltaram=voltaram,
        tipo_sel=tipo_sel,
        tipos=TIPOS_FILTRO,
    )
    return render(request, "assinaturas/inadimplencia.html", contexto)


@login_required
def resumo(request):
    """Aba 4 — resumo do ano (realizado) + previsão mês a mês pelas assinaturas ativas."""
    ano = int(request.GET.get("ano") or timezone.localdate().year)
    hoje = timezone.localdate()

    # Realizado por mês (faturas pagas no ano).
    realizado = {m: Decimal("0") for m in range(1, 13)}
    por_mes = (
        RecebimentoVindi.objects.filter(data_pagamento__year=ano)
        .annotate(m=ExtractMonth("data_pagamento"))
        .values("m")
        .annotate(s=Sum("valor"))
    )
    for row in por_mes:
        if row["m"]:
            realizado[row["m"]] = row["s"] or Decimal("0")

    # Previsto por mês (cobranças futuras das assinaturas ativas dentro do ano).
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

    linhas = []
    total_real = Decimal("0")
    total_prev = Decimal("0")
    mes_atual = hoje.month if ano == hoje.year else 12
    for m in range(1, 13):
        futuro = ano > hoje.year or (ano == hoje.year and m > hoje.month)
        total_real += realizado[m]
        if futuro:
            total_prev += previsto[m]
        linhas.append({
            "mes": MESES_PT[m - 1],
            "realizado": realizado[m],
            "previsto": previsto[m],
            "futuro": futuro,
        })

    label_tipo = dict(PlanoVindi.Tipo.choices)
    por_tipo = [
        {"label": label_tipo.get(r["tipo"], r["tipo"]), "n": r["n"], "s": r["s"]}
        for r in RecebimentoVindi.objects.filter(data_pagamento__year=ano)
        .values("tipo")
        .annotate(s=Sum("valor"), n=Count("id"))
        .order_by("-s")
    ]

    anos = [d.year for d in RecebimentoVindi.objects.dates("data_pagamento", "year", order="DESC")]

    contexto = contexto_base(
        "resumo-assinaturas",
        ano=ano,
        anos=anos,
        linhas=linhas,
        total_real=total_real,
        total_prev=total_prev,
        projecao_ano=total_real + total_prev,
        por_tipo=por_tipo,
        ativos_count=ativos.count(),
    )
    return render(request, "assinaturas/resumo.html", contexto)


@login_required
def sincronizar(request):
    """Dispara a sincronização com a Vindi e volta para a aba indicada."""
    destino = request.POST.get("voltar_para", "assinaturas_adimplencia")
    if request.method == "POST":
        try:
            r = executar_sincronizacao()
            messages.success(
                request,
                f"Sincronizado com a Vindi: {r['assinaturas']} assinaturas, "
                f"{r['recebimentos']} recebimentos e {r['planos']} planos.",
            )
        except Exception as erro:
            messages.error(request, f"Erro ao sincronizar com a Vindi: {erro}")
    try:
        return redirect(destino)
    except Exception:
        return redirect("assinaturas_adimplencia")
