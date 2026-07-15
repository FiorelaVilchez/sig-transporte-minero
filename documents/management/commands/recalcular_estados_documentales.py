from django.core.management.base import BaseCommand

from documents.services import recalcular_estados_todos_documentos


class Command(BaseCommand):
    help = "Recalcula estado_documento de todos los documentos según su fecha de vencimiento."

    def handle(self, *args, **options):
        resultado = recalcular_estados_todos_documentos()
        contadores = resultado["contadores"]
        self.stdout.write(self.style.SUCCESS(
            f"Recálculo completado: {resultado['total']} documentos procesados, "
            f"{resultado['actualizados']} actualizados."
        ))
        self.stdout.write(f"  Vigente:    {contadores['Vigente']}")
        self.stdout.write(f"  Por vencer: {contadores['Por vencer']}")
        self.stdout.write(f"  Vencido:    {contadores['Vencido']}")
