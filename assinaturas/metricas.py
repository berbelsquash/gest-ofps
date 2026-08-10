"""Camada de métricas de Filiações — modelo baseado em PAGAMENTOS reais.

Decisões combinadas com a diretoria (Vinicius), após identificar um "ataque" de
filiações em jan/fev 2026 e o hábito de cancelar inadimplentes em lote (a data de
cancelamento na Vindi não reflete o mês real da saída):

- Conta-se por **pessoa** (ID do cliente na Vindi), não por assinatura.
- **Filiado de verdade = quem pagou ao menos 1 fatura.** Quem nunca pagou (o ataque
  e tentativas frustradas) é ignorado — não é novo nem cancelamento.
- **Novo filiado** = mês do **1º pagamento** da pessoa.
- **Cancelamento** = mês do **último pagamento + 1 ciclo** (o primeiro ciclo que ela
  deixou de pagar), para quem não tem nenhuma assinatura ativa hoje. Isso data a saída
  em quando o dinheiro parou, não no dia do cancelamento administrativo em lote.
- **LTV** = total recebido por filiado (entre quem pagou).
- **Filiado ativo** = pessoa com assinatura não cancelada hoje.
"""

import calendar
import re
import unicodedata
from collections import defaultdict
from datetime import date
from decimal import Decimal

from .models import AssinaturaVindi, PlanoVindi, RecebimentoVindi


def _add_meses(d, n):
    total = d.month - 1 + n
    ano = d.year + total // 12
    mes = total % 12 + 1
    dia = min(d.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().upper().strip()
    return re.sub(r"\s+", " ", s)


def chave_pessoa(vindi_id, nome):
    """Identidade da pessoa: ID do cliente na Vindi (preenchido em 100% da base),
    com fallback para o nome normalizado."""
    if vindi_id:
        return ("v", vindi_id)
    return ("n", _norm(nome))


def meses_entre(d1, d2):
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


class Filiacoes:
    """Carrega assinaturas + pagamentos e agrega por pessoa, aplicando as regras
    acima. Opcionalmente filtra por tipo de plano. `hoje` baliza os cálculos."""

    def __init__(self, tipo="", hoje=None):
        self.hoje = hoje or date.today()
        subs_qs = AssinaturaVindi.objects.exclude(tipo=PlanoVindi.Tipo.IGNORAR)
        recs_qs = RecebimentoVindi.objects.filter(status="paid").exclude(tipo=PlanoVindi.Tipo.IGNORAR)
        if tipo:
            subs_qs = subs_qs.filter(tipo=tipo)
            recs_qs = recs_qs.filter(tipo=tipo)
        self.subs = list(subs_qs)

        # Pagamentos por pessoa: total recebido, 1º e último pagamento.
        self.recebido = defaultdict(lambda: Decimal("0"))
        self.primeiro = {}
        self.ultimo = {}
        plano_rec = {}
        for r in recs_qs:
            k = chave_pessoa(r.cliente_vindi_id, r.cliente_nome)
            self.recebido[k] += r.valor or Decimal("0")
            plano_rec[k] = r.get_tipo_display()
            if r.data_pagamento:
                if k not in self.primeiro or r.data_pagamento < self.primeiro[k]:
                    self.primeiro[k] = r.data_pagamento
                if k not in self.ultimo or r.data_pagamento > self.ultimo[k]:
                    self.ultimo[k] = r.data_pagamento
        self.pagantes = set(self.primeiro)  # quem pagou >= 1 fatura

        # Info por pessoa vinda das assinaturas: ativa?, intervalo de cobrança,
        # inadimplência e plano representativo (prioriza a assinatura ativa, senão a mais recente).
        self.pessoas_ativas = set()
        self.inad_ativos = set()
        self.intervalo = {}
        self._plano = {}
        self._plano_ordem = {}
        for a in self.subs:
            k = chave_pessoa(a.cliente_vindi_id, a.cliente_nome)
            self.intervalo[k] = max(self.intervalo.get(k, 1), max(1, a.intervalo_meses or 1))
            ativa = a.status != "canceled"
            if ativa:
                self.pessoas_ativas.add(k)
                if a.inadimplente_desde:
                    self.inad_ativos.add(k)
            ordem = (1 if ativa else 0, a.data_inicio or date.min)
            if k not in self._plano_ordem or ordem > self._plano_ordem[k]:
                self._plano_ordem[k] = ordem
                self._plano[k] = a.get_tipo_display()
        # Pagante sem assinatura mapeada: usa o tipo do próprio pagamento.
        for k in self.pagantes:
            self._plano.setdefault(k, plano_rec.get(k, "Outros"))

    # ---- eventos por pessoa ----
    def mes_churn(self, k):
        """Mês efetivo de saída: último pagamento + 1 ciclo. None se a pessoa ainda
        está ativa, nunca pagou, ou a saída ainda não aconteceu (está no futuro)."""
        if k in self.pessoas_ativas or k not in self.ultimo:
            return None
        d = _add_meses(self.ultimo[k], self.intervalo.get(k, 1))
        return d if d <= self.hoje else None

    def fim_pessoa(self, k):
        return self.mes_churn(k) or self.hoje

    def permanencia(self, k):
        ini = self.primeiro.get(k)
        return max(0, meses_entre(ini, self.fim_pessoa(k))) if ini else 0

    # ---- agregados ----
    def total_filiados(self):
        return len(self.pessoas_ativas)

    def novos_por_mes(self, ano):
        meses = [0] * 12
        for d in self.primeiro.values():
            if d.year == ano:
                meses[d.month - 1] += 1
        return meses

    def cancelamentos_por_mes(self, ano):
        meses = [0] * 12
        for k in self.pagantes:
            d = self.mes_churn(k)
            if d and d.year == ano:
                meses[d.month - 1] += 1
        return meses

    def cancelamentos_ano(self, ano):
        return sum(self.cancelamentos_por_mes(ano))

    def inadimplentes(self):
        return len(self.inad_ativos)

    def ltv_medio(self):
        """Média do total recebido por filiado, só entre quem já pagou alguma fatura."""
        valores = [v for v in self.recebido.values() if v > 0]
        if not valores:
            return 0.0
        return float(sum(valores, Decimal("0"))) / len(valores)

    def permanencia_media(self):
        vs = [self.permanencia(k) for k in self.pagantes]
        return (sum(vs) / len(vs)) if vs else 0

    def permanencia_por_plano(self):
        pp = defaultdict(list)
        for k in self.pagantes:
            pp[self._plano.get(k, "—")].append(self.permanencia(k))
        return [{"plano": p, "meses": round(sum(v) / len(v), 1), "n": len(v)}
                for p, v in sorted(pp.items())]

    def churn_ano(self, ano):
        canc = self.cancelamentos_ano(ano)
        base = len(self.pessoas_ativas) + canc
        return (100 * canc / base) if base else 0

    def curva_sobrevivencia(self, n=24):
        payers = list(self.pagantes)
        surv = []
        for mm in range(n + 1):
            elig = [k for k in payers if meses_entre(self.primeiro[k], self.hoje) >= mm]
            if not elig:
                surv.append(None)
                continue
            vivos = 0
            for k in elig:
                ch = self.mes_churn(k)
                if ch is None:
                    vivos += 1  # ainda pagante/ativo
                elif meses_entre(self.primeiro[k], ch) >= mm:
                    vivos += 1  # saiu depois do mês mm
            surv.append(round(100 * vivos / len(elig), 1))
        return surv
