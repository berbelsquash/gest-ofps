from django.core.management.base import BaseCommand

from assinaturas.sincronizacao import atualizar_valores


class Command(BaseCommand):
    help = "Atualiza planos e assinaturas (com valores) sem recarregar as faturas."

    def handle(self, *args, **options):
        r = atualizar_valores()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {r['planos']} planos e {r['assinaturas']} assinaturas (valores atualizados)."
            )
        )
