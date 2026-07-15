from django.core.management.base import BaseCommand, CommandError

from assignments.validators import validar_asignacion
from drivers.models import Conductor
from trucks.models import Vehiculo


class Command(BaseCommand):
    help = (
        "Demuestra el resultado de validar_asignacion para un par conductor-vehículo."
    )

    def add_arguments(self, parser):
        parser.add_argument("--conductor_id", type=int, required=True)
        parser.add_argument("--vehiculo_id", type=int, required=True)

    def handle(self, *args, **options):
        try:
            conductor = Conductor.objects.get(pk=options["conductor_id"])
        except Conductor.DoesNotExist as exc:
            raise CommandError(
                f"No existe conductor con id={options['conductor_id']}"
            ) from exc

        try:
            vehiculo = Vehiculo.objects.get(pk=options["vehiculo_id"])
        except Vehiculo.DoesNotExist as exc:
            raise CommandError(
                f"No existe vehículo con id={options['vehiculo_id']}"
            ) from exc

        self.stdout.write("=" * 60)
        self.stdout.write("PRUEBA DE VALIDACIÓN DE ASIGNACIÓN")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Conductor: {conductor} (id={conductor.driver_id}, estado={conductor.estado})")
        self.stdout.write(f"Vehículo:  {vehiculo} (id={vehiculo.truck_id}, estado={vehiculo.estado})")
        self.stdout.write("-" * 60)

        resultado = validar_asignacion(conductor, vehiculo, generar_alertas=True)

        self.stdout.write(self.style.HTTP_INFO(f"VEREDICTO: {resultado['veredicto']}"))
        self.stdout.write("")

        self._imprimir_lista("BLOQUEOS", resultado["bloqueos"])
        self._imprimir_lista("OBSERVACIONES", resultado["observaciones"])

        self.stdout.write("ALERTAS A GENERAR:")
        if not resultado["alertas_a_generar"]:
            self.stdout.write("  (ninguna)")
        else:
            for alerta in resultado["alertas_a_generar"]:
                self.stdout.write(
                    f"  - [{alerta['nivel_riesgo']}] {alerta['tipo_alerta']}: "
                    f"{alerta['mensaje']}"
                )

        self.stdout.write("")
        self.stdout.write(f"ALERTAS GENERADAS (IDs): {resultado['alertas_generadas']}")
        self.stdout.write("=" * 60)

    def _imprimir_lista(self, titulo, items):
        self.stdout.write(f"{titulo}:")
        if not items:
            self.stdout.write("  (ninguno)")
        else:
            for item in items:
                self.stdout.write(f"  - {item}")
        self.stdout.write("")
