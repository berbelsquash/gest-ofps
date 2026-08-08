import os
import tempfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from painel.menu import contexto_base

from .importacao import exportar_atletas, importar_atletas
from .models import Atleta


@login_required
def atletas_lista(request):
    q = (request.GET.get("q") or "").strip()
    filiacao = request.GET.get("filiacao", "")
    regiao = request.GET.get("regiao", "")
    genero = request.GET.get("genero", "")

    qs = Atleta.objects.all()
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(email__icontains=q)
                       | Q(local1__icontains=q) | Q(treinador__icontains=q))
    if filiacao:
        qs = qs.filter(filiacao=filiacao)
    if regiao:
        qs = qs.filter(regiao=regiao)
    if genero:
        qs = qs.filter(genero=genero)

    total = qs.count()
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)

    def valores(campo):
        return list(Atleta.objects.exclude(**{campo: ""})
                    .values_list(campo, flat=True).distinct().order_by(campo))

    contexto = contexto_base(
        "bases-atletas", page=page, total=total, qs_str=params.urlencode(),
        q=q, filiacao=filiacao, regiao=regiao, genero=genero,
        filiacoes=valores("filiacao"), regioes=valores("regiao"), generos=valores("genero"),
        total_geral=Atleta.objects.count(),
        ativos=Atleta.objects.filter(filiacao="Ativo").count(),
    )
    return render(request, "bases/atletas.html", contexto)


@login_required
def importar_atletas_view(request):
    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if not arquivo or not arquivo.name.lower().endswith(".xlsx"):
            messages.error(request, "Envie um arquivo .xlsx da base de atletas.")
            return redirect("bases_atletas")
        fd, caminho = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as destino:
                for chunk in arquivo.chunks():
                    destino.write(chunk)
            criados, atualizados = importar_atletas(caminho)
            messages.success(
                request,
                f"Base atualizada: {criados} novo(s) e {atualizados} atualizado(s) "
                "— sem duplicar nomes.")
        except Exception as erro:
            messages.error(request, f"Não consegui ler a planilha: {erro}")
        finally:
            try:
                os.remove(caminho)
            except OSError:
                pass
    return redirect("bases_atletas")


@login_required
def exportar_atletas_view(request):
    dados = exportar_atletas()
    resp = HttpResponse(
        dados,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    nome = f"atletas_{timezone.localdate().isoformat()}.xlsx"
    resp["Content-Disposition"] = f'attachment; filename="{nome}"'
    return resp
