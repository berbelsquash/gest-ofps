"""Lê a planilha de inscrições (respostas do Google Forms) de um evento e
devolve o roster estruturado: atleta, categoria, filiado, valor, link do
comprovante, etc.

Não tenta casar comprovante×extrato por nome (o pagador no banco costuma ser o
pai/responsável, diferente do atleta). A conciliação é feita por totais na tela
do evento: soma das inscrições (esperado) × receitas marcadas no extrato.

O leitor é tolerante: os formulários variam os rótulos das colunas. Detecta as
colunas padrão pelo cabeçalho e a coluna de VALOR (que costuma vir sem rótulo,
ex.: "Coluna 1") por heurística — e mostra na tela o que detectou.
"""

import unicodedata
from datetime import date, datetime
from decimal import Decimal

import openpyxl


# --- normalização ----------------------------------------------------------

def _sem_acento(texto):
    txt = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in txt if not unicodedata.combining(c))


def _norm(texto):
    return _sem_acento(texto).strip().upper()


# --- parsing de células ----------------------------------------------------

def _parse_data(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except ValueError:
            continue
    return None


def _parse_valor(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return Decimal(str(abs(v)))
    s = _sem_acento(str(v)).upper().replace("R$", "").strip()
    if "," in s:  # 1.234,56 -> 1234.56
        s = s.replace(".", "").replace(",", ".")
    import re
    m = re.search(r"-?\d+(\.\d+)?", s)
    return Decimal(str(abs(float(m.group())))) if m else None


# --- detecção de colunas ---------------------------------------------------

# campo lógico -> palavras-chave no cabeçalho (ordem importa)
_CHAVES = [
    ("nome", ("nome completo", "nome do atleta", "atleta", "nome")),
    ("email", ("email", "e-mail")),
    ("data", ("carimbo", "timestamp")),
    ("clube", ("clube", "academia")),
    ("treinador", ("treinador", "professor")),
    ("filiado", ("filiado", "filiacao")),
    ("categoria", ("categoria",)),
    ("pacote", ("pacote",)),
    ("comprovante", ("comprovante", "recibo", "anexo")),
]

# cabeçalhos que NÃO são valor (evita casar RG, telefone, etc. na heurística)
_NAO_VALOR = ("RG", "CELULAR", "TELEFONE", "NASCIMENTO", "PONTUA", "EMAIL",
              "ENDERECO", "CARIMBO", "DATA", "CEP", "IDADE")


def _mapear(cabecalho):
    mapa = {}
    usados = set()
    norm = [_norm(c) for c in cabecalho]
    for campo, chaves in _CHAVES:
        for i, h in enumerate(norm):
            if i in usados:
                continue
            if any(_sem_acento(k).upper() in h for k in chaves):
                mapa[campo] = i
                usados.add(i)
                break
    return mapa


def _detectar_coluna_valor(cabecalho, corpo, usados):
    """Coluna do valor pago. Primeiro por rótulo; senão, a coluna numérica com
    mais valores numa faixa plausível de inscrição (R$10–5.000)."""
    norm = [_norm(c) for c in cabecalho]
    for i, h in enumerate(norm):
        if any(k in h for k in ("VALOR", "TOTAL", "PRECO", "INVESTIMENTO", "PAGO")):
            return i
    melhor, escore = None, 0
    for i, h in enumerate(norm):
        if i in usados or any(b in h for b in _NAO_VALOR):
            continue
        cont = 0
        for row in corpo:
            v = row[i] if i < len(row) else None
            try:
                x = float(v)
            except (TypeError, ValueError):
                continue
            if 10 <= x <= 5000:
                cont += 1
        if cont > escore:
            escore, melhor = cont, i
    return melhor


def preparar_lista_inscricoes(caminho):
    """Lê o .xlsx e devolve {colunas: {campo: rótulo}, linhas: [dict...]}."""
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    ws = wb.active
    todas = list(ws.iter_rows(values_only=True))
    wb.close()
    if not todas:
        return {"colunas": {}, "linhas": []}

    cabecalho = list(todas[0])
    corpo = todas[1:]
    mapa = _mapear(cabecalho)
    ivalor = _detectar_coluna_valor(cabecalho, corpo, set(mapa.values()))
    if ivalor is not None:
        mapa["valor"] = ivalor

    def rotulo(i):
        return str(cabecalho[i]) if (i is not None and i < len(cabecalho)) else ""

    linhas = []
    for row in corpo:
        if row is None or all(c is None or c == "" for c in row):
            continue

        def val(campo):
            i = mapa.get(campo)
            return row[i] if (i is not None and i < len(row)) else None

        nome = str(val("nome") or "").strip()
        if not nome:
            continue
        linhas.append({
            "nome": nome,
            "email": str(val("email") or "").strip(),
            "clube": str(val("clube") or "").strip(),
            "treinador": str(val("treinador") or "").strip(),
            "categoria": str(val("categoria") or "").strip(),
            "filiado": str(val("filiado") or "").strip(),
            "valor": _parse_valor(val("valor")) or Decimal("0"),
            "comprovante": str(val("comprovante") or "").strip(),
            "pacote": "sim" in _norm(val("pacote") or "").lower() if val("pacote") else False,
            "data": _parse_data(val("data")),
        })

    colunas = {campo: rotulo(i) for campo, i in mapa.items()}
    return {"colunas": colunas, "linhas": linhas}
