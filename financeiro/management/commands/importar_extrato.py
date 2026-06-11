from django.core.management.base import BaseCommand

from financeiro.importacao import importar_extrato


class Command(BaseCommand):
    help = "Importa um extrato bancário (xlsx do Banco do Brasil)."

    def add_arguments(self, parser):
        parser.add_argument("caminho", help="Caminho do arquivo .xlsx do extrato")

    def handle(self, *args, **options):
        n = importar_extrato(options["caminho"])
        self.stdout.write(self.style.SUCCESS(f"OK: {n} lançamentos importados e classificados."))
