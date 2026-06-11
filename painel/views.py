from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from .menu import ITENS, SECAO_INICIAL, contexto_base


@login_required
def secao(request, slug=SECAO_INICIAL):
    """Renderiza uma seção genérica do painel (ainda sem campos)."""
    if slug not in ITENS:
        raise Http404("Seção não encontrada.")
    return render(request, "painel/secao.html", contexto_base(slug))
