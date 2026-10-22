"""Prepara la base de demostración en un despliegue (por ejemplo, Render).

Carga los datos de demostración solo si la base está vacía, o si la variable
RECARGAR_DEMO vale 1. Las cuentas de prueba se actualizan siempre.
"""
import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from drivers.models import Conductor


class Command(BaseCommand):
    help = 'Carga los datos de demostración si la base está vacía y actualiza las cuentas de prueba.'

    def handle(self, *args, **options):
        recargar = os.environ.get('RECARGAR_DEMO', '0') == '1'
        if recargar or not Conductor.objects.exists():
            motivo = 'RECARGAR_DEMO=1' if recargar else 'base vacía'
            self.stdout.write(f'Cargando datos de demostración ({motivo})...')
            call_command('seed_data')
        else:
            self.stdout.write('La base ya tiene datos; no se recargan.')
        call_command('seed_users')
