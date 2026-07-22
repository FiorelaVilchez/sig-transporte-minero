from django.core.management.base import BaseCommand
from dashboard.exports import exportar_todos_los_csv_a_disco

class Command(BaseCommand):
    help = "Genera y exporta los 8 archivos CSV para Power BI en la carpeta exports/"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Iniciando exportación de datos a CSV..."))
        
        resumen = exportar_todos_los_csv_a_disco()
        
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("EXPORTACIÓN COMPLETADA CON ÉXITO"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        
        for filename, rows in resumen.items():
            self.stdout.write(f"  - {filename:<40} : {rows} filas escritas")
            
        self.stdout.write(self.style.SUCCESS("=" * 60))
