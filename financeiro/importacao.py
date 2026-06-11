"""Importa o extrato bancário (xlsx do Banco do Brasil).

- Popula LancamentoBancario (todas as linhas) para a conciliação.
- Popula LancamentoFinanceiro (origem='extrato') de junho em diante, mapeado
  nas categorias da FPS (a planilha cobre até maio).

Ao reimportar, as classificações marcadas como "revisado manualmente" são
preservadas (casadas pela assinatura da linha).
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

import openpyxl

from .categorizacao import classificar
from .models import LancamentoBancario, LancamentoFinanceiro

# A partir deste mês de 2026, o extrato passa a alimentar o ledger (até maio é a planilha).
LEDGER_DESDE_MES = 6
LEDGER_ANO = 2026


def _data(texto):
    return datetime.strptime(texto, "%d/%m/%Y").date()


def _assinatura(data, valor, descricao, razao):
    return (str(data), str(valor), (descricao or "")[:80], (razao or "")[:80])


def _alimentar_ledger_extrato(registros):
    """Cria os lançamentos do ledger a partir do extrato, de junho em diante."""
    LancamentoFinanceiro.objects.filter(origem="extrato").delete()
    novos = []
    for r in registros:
        if r.data.year != LEDGER_ANO or r.data.month < LEDGER_DESDE_MES:
            continue
        grupo = r.grupo or "(a classificar)"
        # Receitas que não são inscrições vão para o grupo "Receitas" (como na planilha).
        if r.tipo == "receita" and grupo != "Inscrições":
            grupo = "Receitas"
        novos.append(LancamentoFinanceiro(
            ano=r.data.year, mes=r.data.month, data=r.data, tipo=r.tipo,
            grupo=grupo, categoria=r.categoria, evento=r.evento,
            valor=abs(r.valor), descricao=(r.razao_social or r.descricao or "")[:255],
            origem="extrato", pago=True,
        ))
    LancamentoFinanceiro.objects.bulk_create(novos, batch_size=500)
    return len(novos)


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

    # Alimenta o ledger unificado (junho+).
    _alimentar_ledger_extrato(registros)

    return len(registros)
