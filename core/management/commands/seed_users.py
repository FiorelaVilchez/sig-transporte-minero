from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import PerfilUsuario
from drivers.models import Conductor

class Command(BaseCommand):
    help = 'Seeds the database with test users for each of the 5 roles.'

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
                'conductor_license': 'Q41258763',  # Juan Alberto Pérez Quispe
                'telefono': '954444444'
            },
            {
                'username': 'finanzas1',
                'first_name': 'Rocío',
                'last_name': 'Finanzas',
                'email': 'rocio.fin@transmin.com',
                'password': 'Finanzas2026*',
                'rol': 'Finanzas',
                'conductor_license': None,
                'telefono': '955555555'
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
                conductor = Conductor.objects.filter(licencia=u['conductor_license']).first()
                if conductor is None:
                    vinculados = PerfilUsuario.objects.filter(conductor__isnull=False).values('conductor_id')
                    conductor = (Conductor.objects.exclude(estado__in=['De baja', 'No apto'])
                                 .exclude(pk__in=vinculados).order_by('apellidos').first())
                    if conductor:
                        self.stdout.write(self.style.WARNING(
                            f"No existe la licencia {u['conductor_license']}; se vincula con {conductor.apellidos}, {conductor.nombres}. "
                            "Ejecute primero 'python manage.py seed_data' para cargar los datos de demostración."
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            "No hay conductores registrados: la cuenta queda sin vincular. "
                            "Ejecute 'python manage.py seed_data' y luego este comando de nuevo."
                        ))

            # Crear PerfilUsuario
            PerfilUsuario.objects.create(
                usuario=user,
                rol=u['rol'],
                conductor=conductor,
                telefono=u['telefono']
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully seeded all test users and profiles!'))
