import calendar
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum
from django.db.models.functions import ExtractMonth
from django.shortcuts import redirect, render
from django.utils import timezone

from financeiro.models import LancamentoBancario
from painel.menu import contexto_base

from .metricas import Filiacoes
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
    """Base de Filiações — filiados com filtro de status (ativos / em dia /
    inadimplente / cancelado) e por tipo de plano."""
    tipo_sel = request.GET.get("tipo", "")
    status_sel = request.GET.get("status", "")
    atleta_sel = request.GET.get("atleta", "")

    base = AssinaturaVindi.objects.exclude(tipo=PlanoVindi.Tipo.IGNORAR)
    if status_sel == "cancelado":
        qs = base.filter(status="canceled")
    elif status_sel == "inadimplente":
        qs = base.exclude(status="canceled").filter(inadimplente_desde__isnull=False)
    elif status_sel == "em_dia":
        qs = base.exclude(status="canceled").filter(inadimplente_desde__isnull=True)
    else:  # ativos (padrão)
        qs = base.exclude(status="canceled")
    if tipo_sel:
        qs = qs.filter(tipo=tipo_sel)
    if atleta_sel == "sem":
        qs = qs.filter(atleta__isnull=True)
    qs = qs.select_related("atleta").order_by("cliente_nome")

    # Visão geral (independente do filtro) para os cartões.
    ativos = base.exclude(status="canceled")
    n_ativos = ativos.count()
    n_inad = ativos.filter(inadimplente_desde__isnull=False).count()
    n_link = ativos.exclude(atleta__isnull=True).count()
    ultima = AssinaturaVindi.objects.aggregate(m=Max("atualizado_em"))["m"]

    contexto = contexto_base(
        "assinaturas-adimplencia",
        assinaturas=qs,
        total=qs.count(),
        n_ativos=n_ativos,
        em_dia=n_ativos - n_inad,
        inadimplentes=n_inad,
        cancelados=base.filter(status="canceled").count(),
        conciliados=n_link,
        sem_atleta=n_ativos - n_link,
        tipo_sel=tipo_sel,
        status_sel=status_sel,
        atleta_sel=atleta_sel,
        tipos=TIPOS_FILTRO,
        ultima_sync=ultima,
    )
    return render(request, "assinaturas/adimplencia.html", contexto)


@login_required
def conciliar_vindi_view(request):
    """Roda a conciliação Vindi ↔ Atletas (liga por nome/e-mail)."""
    if request.method == "POST":
        from bases.conciliacao import conciliar_vindi
        linkadas, sem, total = conciliar_vindi()
        messages.success(
            request, f"Conciliação: {linkadas} de {total} assinaturas ligadas a atletas "
            f"({sem} sem atleta).")
    return redirect("assinaturas_adimplencia")


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

    # Quanto da Vindi já caiu de fato na conta (cartão/Yapay identificado no extrato).
    caiu_conta = LancamentoBancario.objects.filter(
        tipo="receita", grupo="Cartão/Vindi", data__year=ano
    ).aggregate(s=Sum("valor"))["s"] or Decimal("0")

    contexto = contexto_base(
        "resumo-assinaturas",
        ano=ano,
        anos=anos,
        linhas=linhas,
        total_real=total_real,
        total_prev=total_prev,
        projecao_ano=total_real + total_prev,
        caiu_conta=caiu_conta,
        a_receber=total_real - caiu_conta,
        por_tipo=por_tipo,
        ativos_count=ativos.count(),
    )
    return render(request, "assinaturas/resumo.html", contexto)


def _meses_entre(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


@login_required
def dashboard_filiacoes(request):
    """Dashboard de Filiações — abas Visão geral / Retenção / Movimento, com
    filtros por ano e por plano. Fonte: AssinaturaVindi + RecebimentoVindi."""
    aba = request.GET.get("aba", "geral")
    if aba not in ("geral", "retencao", "movimento"):
        aba = "geral"
    hoje = timezone.localdate()
    ano = int(request.GET.get("ano") or hoje.year)
    plano = request.GET.get("plano", "")

    f = Filiacoes(tipo=plano, hoje=hoje)
    recebimentos = RecebimentoVindi.objects.all()
    if plano:
        recebimentos = recebimentos.filter(tipo=plano)

    anos = [d.year for d in RecebimentoVindi.objects.dates("data_pagamento", "year", order="DESC")] or [ano]
    planos = [(t.value, t.label) for t in PlanoVindi.Tipo if t.value != "ignorar"]
    ctx = dict(aba=aba, ano=ano, anos=anos, plano=plano, planos=planos, meses=MESES_PT)

    if aba == "geral":
        realizado = [Decimal("0")] * 12
        for r in (recebimentos.filter(data_pagamento__year=ano)
                  .annotate(m=ExtractMonth("data_pagamento")).values("m").annotate(s=Sum("valor"))):
            if r["m"]:
                realizado[r["m"] - 1] = r["s"] or Decimal("0")
        previsto = [Decimal("0")] * 12
        # Previsão de receita: por assinatura ativa (cada assinatura cobra), não por pessoa.
        ativas = [a for a in f.subs
                  if a.status != "canceled" and a.valor_ciclo and a.proxima_cobranca]
        for a in ativas:
            intervalo = max(1, a.intervalo_meses or 1)
            d, guarda = a.proxima_cobranca, 0
            while d.year <= ano and guarda < 240:
                if d.year == ano and (ano > hoje.year or d.month > hoje.month):
                    previsto[d.month - 1] += a.valor_ciclo
                d = _add_meses(d, intervalo)
                guarda += 1
                if d.year > ano:
                    break
        total_real, total_prev = sum(realizado), sum(previsto)
        ctx.update(
            realizado=[float(x) for x in realizado], previsto=[float(x) for x in previsto],
            total_real=total_real, total_prev=total_prev, projecao_ano=total_real + total_prev,
            total_filiados=f.total_filiados(),
            novos_ano=sum(f.novos_por_mes(ano)),
        )

    elif aba == "retencao":
        ctx.update(
            ltv=f.ltv_medio(),
            permanencia_media=f.permanencia_media(),
            churn=f.churn_ano(ano),
            canc_ano=f.cancelamentos_ano(ano),
            perman_plano=f.permanencia_por_plano(),
            sobrevivencia=f.curva_sobrevivencia(24), sobrev_meses=list(range(25)),
        )

    else:  # movimento
        novos = f.novos_por_mes(ano)
        canc = f.cancelamentos_por_mes(ano)
        inad = f.inadimplentes()
        ativos = f.total_filiados()
        ctx.update(
            novos=novos, cancelamentos=canc, total_novos=sum(novos), total_canc=sum(canc),
            inadimplentes=inad, inad_pct=round(100 * inad / ativos, 1) if ativos else 0,
            ativos=ativos,
        )

    return render(request, "assinaturas/dashboard_filiacoes.html", contexto_base("dash-filiacoes", **ctx))


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
