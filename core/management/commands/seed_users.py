from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import PerfilUsuario
from drivers.models import Conductor

class Command(BaseCommand):
    help = 'Seeds the database with test users for each of the 4 roles.'

    def handle(self, *args, **options):
        # Datos de usuarios y perfiles
        users_data = [
            {
                'username': 'admin_operaciones',
                'first_name': 'Administrador',
                'last_name': 'Operaciones',
                'email': 'admin.ops@transmin.com',
                'password': 'Operaciones2026*',
                'rol': 'Administrador de operaciones',
                'conductor_license': None,
                'telefono': '951111111'
            },
            {
                'username': 'supervisor1',
                'first_name': 'Carlos',
                'last_name': 'Supervisor',
                'email': 'carlos.sup@transmin.com',
                'password': 'Supervisor2026*',
                'rol': 'Supervisor',
                'conductor_license': None,
                'telefono': '952222222'
            },
            {
                'username': 'gerencia1',
                'first_name': 'Ana',
                'last_name': 'Gerente',
                'email': 'ana.ger@transmin.com',
                'password': 'Gerencia2026*',
                'rol': 'Gerencia',
                'conductor_license': None,
                'telefono': '953333333'
            },
            {
                'username': 'conductor1',
                'first_name': 'Juan',
                'last_name': 'Conductor',
                'email': 'juan.cond@transmin.com',
                'password': 'Conductor2026*',
                'rol': 'Conductor',
                'conductor_license': 'Q12345678', # Juan Pérez Quispe
                'telefono': '954444444'
            }
        ]

        self.stdout.write('Clearing existing test users and profiles...')
        # Eliminar usuarios previos
        usernames = [u['username'] for u in users_data]
        User.objects.filter(username__in=usernames).delete()

        for u in users_data:
            self.stdout.write(f"Creating user {u['username']}...")
            user = User.objects.create_user(
                username=u['username'],
                first_name=u['first_name'],
                last_name=u['last_name'],
                email=u['email'],
                password=u['password']
            )
            
            # Buscar conductor si corresponde
            conductor = None
            if u['conductor_license']:
                try:
                    conductor = Conductor.objects.get(licencia=u['conductor_license'])
                except Conductor.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Conductor con licencia {u['conductor_license']} no encontrado!"))

            # Crear PerfilUsuario
            PerfilUsuario.objects.create(
                usuario=user,
                rol=u['rol'],
                conductor=conductor,
                telefono=u['telefono']
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded all test users and profiles!'))
