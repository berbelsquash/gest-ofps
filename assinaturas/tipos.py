def classificar_tipo(nome_plano):
    """Deduz o 'tipo' da FPS a partir do nome do plano da Vindi.

    Regras combinadas com a FPS:
      - planos de teste  -> ignorar
      - contém "squashe" -> SquaSHE
      - contém "interior"-> Interior
      - contém "juvenil"/"junior" -> Juvenil (inclui Junior XP e FPS Juniors)
      - contém "filia"   -> Filiação
      - caso contrário   -> Outros (ex.: FPS Tour, Plano Mensal avulso)
    """
    n = (nome_plano or "").lower()
    if "teste" in n:
        return "ignorar"
    if "squashe" in n or "squash" in n:
        return "squashe"
    if "interior" in n:
        return "interior"
    if "juvenil" in n or "junior" in n:
        return "juvenil"
    if "filia" in n:
        return "filiacao"
    return "outros"
