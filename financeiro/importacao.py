"""Importa o extrato bancário (xlsx do Banco do Brasil) para o banco local.

Ao reimportar, as classificações marcadas como "revisado manualmente" são
preservadas (casadas pela assinatura da linha), para não perder o trabalho manual.
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import openpyxl

from .categorizacao import classificar
from .models import LancamentoBancario


def _data(texto):
    return datetime.strptime(texto, "%d/%m/%Y").date()


def _assinatura(data, valor, descricao, razao):
    return (str(data), str(valor), (descricao or "")[:80], (razao or "")[:80])


def importar_extrato(caminho, substituir=True):
    wb = openpyxl.load_workbook(caminho, data_only=True)
    ws = wb.worksheets[0]

    registros = []
    for row in ws.iter_rows(values_only=True):
        vals = (list(row) + [None] * 6)[:6]
        data, lanc, razao, cpf, valor, _saldo = vals
        if valor is None:
            continue
        if not (isinstance(data, str) and "/" in data):
            continue
        try:
            dt = _data(data)
        except ValueError:
            continue

        v = Decimal(str(valor))
        tipo, grupo, categoria, evento = classificar(lanc or "", razao or "", float(v))
        registros.append(
            LancamentoBancario(
                data=dt,
                descricao=(lanc or "")[:255],
                razao_social=(razao or "")[:255],
                cpf_cnpj=(cpf or "")[:30],
                valor=v,
                tipo=tipo,
                grupo=grupo,
                categoria=categoria,
                evento=(evento or "")[:120],
                classificado=bool(grupo),
            )
        )

    if substituir:
        # Preserva classificações revisadas manualmente.
        preservar = defaultdict(list)
        for r in LancamentoBancario.objects.filter(revisado=True):
            chave = _assinatura(r.data, r.valor, r.descricao, r.razao_social)
            preservar[chave].append((r.grupo, r.categoria, r.evento))
        for reg in registros:
            chave = _assinatura(reg.data, reg.valor, reg.descricao, reg.razao_social)
            if preservar.get(chave):
                g, c, e = preservar[chave].pop(0)
                reg.grupo, reg.categoria, reg.evento = g, c, e
                reg.classificado = bool(g)
                reg.revisado = True
        LancamentoBancario.objects.all().delete()

    LancamentoBancario.objects.bulk_create(registros, batch_size=500)
    return len(registros)
