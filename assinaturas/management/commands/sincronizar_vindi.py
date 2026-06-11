from django.core.management.base import BaseCommand

from assinaturas.sincronizacao import executar_sincronizacao


class Command(BaseCommand):
    help = "Sincroniza planos, assinaturas e recebimentos da Vindi para o banco local."

    def handle(self, *args, **options):
        r = executar_sincronizacao()
        self.stdout.write(
            self.style.SUCCESS(
                f"OK: {r['planos']} planos, {r['assinaturas']} assinaturas "
                f"e {r['recebimentos']} recebimentos sincronizados."
            )
        )
