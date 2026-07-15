from django.core.management.base import BaseCommand

from documents.models import DocumentoConductor, DocumentoVehiculo
from documents.services import calcular_estado_documento


class Command(BaseCommand):
    help = "Recalcula estado_documento de todos los documentos según su fecha de vencimiento."

    def handle(self, *args, **options):
        contadores = {"Vigente": 0, "Por vencer": 0, "Vencido": 0}
        actualizados = 0

        for documento in DocumentoConductor.objects.all():
            nuevo_estado = calcular_estado_documento(documento.fecha_vencimiento)
            if documento.estado_documento != nuevo_estado:
                documento.estado_documento = nuevo_estado
                documento.save(update_fields=["estado_documento", "updated_at"])
                actualizados += 1
            contadores[nuevo_estado] += 1

        for documento in DocumentoVehiculo.objects.all():
            nuevo_estado = calcular_estado_documento(documento.fecha_vencimiento)
            if documento.estado_documento != nuevo_estado:
                documento.estado_documento = nuevo_estado
                documento.save(update_fields=["estado_documento", "updated_at"])
                actualizados += 1
            contadores[nuevo_estado] += 1

        total = sum(contadores.values())
        self.stdout.write(self.style.SUCCESS(
            f"Recálculo completado: {total} documentos procesados, {actualizados} actualizados."
        ))
        self.stdout.write(f"  Vigente:    {contadores['Vigente']}")
        self.stdout.write(f"  Por vencer: {contadores['Por vencer']}")
        self.stdout.write(f"  Vencido:    {contadores['Vencido']}")
