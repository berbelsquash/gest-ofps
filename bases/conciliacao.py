"""Camada de conciliação de identidade (spec 4.4).

Liga registros de outras fontes ao atleta-âncora da Base de Atletas pelo nome
(com e-mail de reserva), persistindo o vínculo. Aqui: assinaturas da Vindi.
As participações já casam por nome na importação; a mesma normalização é usada.
"""

import re
import unicodedata

from assinaturas.models import AssinaturaVindi

from .models import Atleta


def _norm(nome):
    txt = unicodedata.normalize("NFKD", str(nome or ""))
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", txt).strip().upper()


def conciliar_vindi(sobrescrever=False):
    """Liga cada assinatura Vindi a um atleta pelo nome (ou e-mail).

    Por padrão preserva vínculos já feitos; sobrescrever=True re-liga tudo.
    Devolve (linkadas, sem_atleta, total)."""
    por_nome, por_email = {}, {}
    for a in Atleta.objects.all():
        por_nome.setdefault(_norm(a.nome), a)
        if a.email:
            por_email.setdefault(a.email.strip().lower(), a)

    for s in AssinaturaVindi.objects.all():
        if s.atleta_id and not sobrescrever:
            continue
        atleta = por_nome.get(_norm(s.cliente_nome))
        if not atleta and s.cliente_email:
            atleta = por_email.get(s.cliente_email.strip().lower())
        if atleta and s.atleta_id != atleta.id:
            s.atleta = atleta
            s.save(update_fields=["atleta"])

    total = AssinaturaVindi.objects.count()
    linkadas = AssinaturaVindi.objects.exclude(atleta__isnull=True).count()
    return linkadas, total - linkadas, total
