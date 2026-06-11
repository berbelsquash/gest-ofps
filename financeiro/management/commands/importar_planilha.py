from django.core.management.base import BaseCommand

from financeiro.importacao_planilha import importar_planilha


class Command(BaseCommand):
    help = "Importa a planilha financeira categorizada da FPS (fonte da verdade até maio)."

    def add_arguments(self, parser):
        parser.add_argument("caminho", help="Caminho do arquivo .xlsx da planilha")
        parser.add_argument("--ate-mes", type=int, default=5)

    def handle(self, *args, **options):
        n = importar_planilha(options["caminho"], ate_mes=options["ate_mes"])
        self.stdout.write(self.style.SUCCESS(f"OK: {n} lançamentos importados da planilha."))
