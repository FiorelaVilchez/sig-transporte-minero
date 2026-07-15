from django.core.management.base import BaseCommand

from alerts.services import escanear_documentos_y_generar_alertas


class Command(BaseCommand):
    help = (
        "Escanea toda la base documental y genera/actualiza alertas de vigencia."
    )

    def handle(self, *args, **options):
        resumen = escanear_documentos_y_generar_alertas()

        self.stdout.write("=" * 60)
        self.stdout.write("ESCANEO AUTOMÁTICO DE ALERTAS DOCUMENTALES")
        self.stdout.write("=" * 60)
        self.stdout.write("")
        self.stdout.write("DOCUMENTOS (tras recálculo de estados):")
        self.stdout.write(f"  Vencidos:     {resumen['documentos_vencidos']}")
        self.stdout.write(f"  Por vencer:   {resumen['documentos_por_vencer']}")
        self.stdout.write("")
        self.stdout.write("ALERTAS GENERADAS EN ESTA EJECUCIÓN:")
        self.stdout.write(f"  Nuevas altas:  {resumen['alertas_nuevas_altas']}")
        self.stdout.write(f"  Nuevas medias: {resumen['alertas_nuevas_medias']}")
        self.stdout.write(f"  Resueltas:     {resumen['alertas_resueltas']}")
        self.stdout.write("=" * 60)
