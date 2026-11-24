"""
ETL del Data Mart (Evidencia 02): ejecuta docs/datamart/etl_datamart.sql, que
extrae los servicios cerrados del SIG, limpia los datos y carga el esquema en
estrella datamart (dimensiones y tabla de hechos).

Uso:  python manage.py cargar_datamart
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

SCRIPT = Path(settings.BASE_DIR) / 'docs' / 'datamart' / 'etl_datamart.sql'
TABLAS = ['dim_tiempo', 'dim_cliente', 'dim_conductor', 'dim_vehiculo', 'dim_ruta', 'fact_servicio']


def cargar_datamart():
    """Ejecuta la ETL y devuelve el número de filas de cada tabla del Data Mart."""
    if connection.vendor != 'postgresql':
        raise CommandError('El Data Mart se carga solo en PostgreSQL.')
    sql = SCRIPT.read_text(encoding='utf-8')
    sql = sql.replace('BEGIN;', '').replace('COMMIT;', '')
    with transaction.atomic(), connection.cursor() as cursor:
        cursor.execute(sql)
        filas = {}
        for tabla in TABLAS:
            cursor.execute(f'SELECT count(*) FROM datamart.{tabla}')
            filas[tabla] = cursor.fetchone()[0]
    return filas


def resumen_origen():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT count(*),
                   count(*) FILTER (WHERE estado_operativo IN ('Completado', 'Con incidencia')),
                   count(*) FILTER (WHERE estado_operativo IN ('Completado', 'Con incidencia')
                                      AND (km_final IS NULL OR km_inicial IS NULL OR km_final < km_inicial))
            FROM assignments_asignacion
        """)
        return cursor.fetchone()


class Command(BaseCommand):
    help = 'Extrae, limpia y carga el Data Mart del servicio de transporte (esquema datamart).'

    def handle(self, *args, **options):
        total, cerrados, km_corregidos = resumen_origen()
        self.stdout.write(f'Asignaciones en el SIG: {total}')
        self.stdout.write(f'  Servicios cerrados que pasan al Data Mart: {cerrados}')
        self.stdout.write(f'  Descartadas (programadas, en ruta o canceladas): {total - cerrados}')
        self.stdout.write(f'  Kilometrajes incompletos corregidos a 0: {km_corregidos}')
        filas = cargar_datamart()
        self.stdout.write('Tablas cargadas en el esquema datamart:')
        for tabla, n in filas.items():
            self.stdout.write(f'  {tabla}: {n} filas')
        self.stdout.write(self.style.SUCCESS('Data Mart cargado correctamente.'))
