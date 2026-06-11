from decimal import Decimal, InvalidOperation

from django.utils.dateparse import parse_date, parse_datetime

from .models import AssinaturaVindi, PlanoVindi, RecebimentoVindi
from .tipos import classificar_tipo
from .vindi import VindiAPI


def _para_data(valor):
    if not valor:
        return None
    dt = parse_datetime(valor)
    if dt:
        return dt.date()
    return parse_date(valor)


def _para_decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _valor_e_intervalo(s):
    """Valor por cobrança (soma dos itens) e o intervalo em meses da assinatura."""
    valor = Decimal("0")
    for item in s.get("product_items") or []:
        preco = _para_decimal((item.get("pricing_schema") or {}).get("price"))
        valor += preco * (item.get("quantity") or 1)
    interval = s.get("interval")
    count = s.get("interval_count") or 1
    if interval == "days":
        meses = max(1, round((count or 30) / 30))
    else:
        meses = count or 1
    return valor, meses


def _data_pagamento(bill):
    for charge in bill.get("charges") or []:
        if charge.get("paid_at"):
            return _para_data(charge["paid_at"])
    return _para_data(bill.get("created_at"))


def _plano_e_tipo(bill, mapa_assinaturas):
    sub = bill.get("subscription") or {}
    assinatura = mapa_assinaturas.get(sub.get("id"))
    if assinatura:
        return assinatura.plano_nome, assinatura.tipo
    itens = bill.get("bill_items") or []
    if itens:
        produto = itens[0].get("product") or {}
        nome = produto.get("name") or itens[0].get("description") or ""
        return nome, classificar_tipo(nome)
    return "", PlanoVindi.Tipo.OUTROS


def sincronizar_planos(api):
    planos = api.listar("plans")
    mapa = {}
    for p in planos:
        obj, _ = PlanoVindi.objects.update_or_create(
            vindi_id=p["id"],
            defaults={
                "nome": p.get("name", "") or "",
                "tipo": classificar_tipo(p.get("name", "")),
                "intervalo": f'{p.get("interval", "")} x{p.get("interval_count", "")}',
                "status": p.get("status", "") or "",
            },
        )
        mapa[p["id"]] = obj
    return planos, mapa


def sincronizar_assinaturas(api, mapa_planos):
    assinaturas = api.listar("subscriptions")
    for s in assinaturas:
        plano = s.get("plan") or {}
        plano_obj = mapa_planos.get(plano.get("id"))
        tipo = plano_obj.tipo if plano_obj else classificar_tipo(plano.get("name", ""))
        cliente = s.get("customer") or {}
        valor, meses = _valor_e_intervalo(s)
        AssinaturaVindi.objects.update_or_create(
            vindi_id=s["id"],
            defaults={
                "cliente_nome": cliente.get("name", "") or "",
                "cliente_vindi_id": cliente.get("id"),
                "cliente_email": cliente.get("email", "") or "",
                "cliente_documento": cliente.get("registry_code", "") or "",
                "plano": plano_obj,
                "plano_nome": plano.get("name", "") or "",
                "tipo": tipo,
                "status": s.get("status", "") or "",
                "valor_ciclo": valor,
                "intervalo_meses": meses,
                "data_inicio": _para_data(s.get("start_at")),
                "proxima_cobranca": _para_data(s.get("next_billing_at")),
                "inadimplente_desde": _para_data(s.get("overdue_since")),
                "cancelada_em": _para_data(s.get("cancel_at")),
            },
        )
    return len(assinaturas)


def sincronizar_recebimentos(api):
    mapa_assinaturas = {a.vindi_id: a for a in AssinaturaVindi.objects.all()}
    bills = api.listar("bills", params={"query": "status:paid"})
    n = 0
    for b in bills:
        if b.get("status") != "paid":
            continue
        plano_nome, tipo = _plano_e_tipo(b, mapa_assinaturas)
        cliente = b.get("customer") or {}
        RecebimentoVindi.objects.update_or_create(
            vindi_id=b["id"],
            defaults={
                "cliente_nome": cliente.get("name", "") or "",
                "cliente_vindi_id": cliente.get("id"),
                "plano_nome": plano_nome,
                "tipo": tipo,
                "valor": _para_decimal(b.get("amount")),
                "status": b.get("status", "") or "",
                "data_pagamento": _data_pagamento(b),
            },
        )
        n += 1
    return n


def executar_sincronizacao():
    """Sincronização completa: planos, assinaturas (com valores) e recebimentos."""
    api = VindiAPI()
    planos, mapa = sincronizar_planos(api)
    n_ass = sincronizar_assinaturas(api, mapa)
    n_rec = sincronizar_recebimentos(api)
    return {"planos": len(planos), "assinaturas": n_ass, "recebimentos": n_rec}


def atualizar_valores():
    """Sincroniza apenas planos e assinaturas (com valores), sem recarregar faturas."""
    api = VindiAPI()
    planos, mapa = sincronizar_planos(api)
    n_ass = sincronizar_assinaturas(api, mapa)
    return {"planos": len(planos), "assinaturas": n_ass}
