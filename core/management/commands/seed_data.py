import datetime
from django.core.management.base import BaseCommand
from drivers.models import Conductor
from trucks.models import Vehiculo
from documents.models import DocumentoConductor, DocumentoVehiculo
from service_requests.models import SolicitudServicio
from assignments.models import Asignacion
from alerts.models import Alerta

class Command(BaseCommand):
    help = 'Seeds the database with realistic and coherent test data for SIG Transporte Minero'

    def handle(self, *args, **options):
        self.stdout.write('Clearing existing data...')
        # Clear existing records (respecting dependencies)
        Alerta.objects.all().delete()
        Asignacion.objects.all().delete()
        DocumentoConductor.objects.all().delete()
        DocumentoVehiculo.objects.all().delete()
        SolicitudServicio.objects.all().delete()
        Conductor.objects.all().delete()
        Vehiculo.objects.all().delete()

        today = datetime.date.today()

        self.stdout.write('Seeding Conductores...')
        conductores_data = [
            {
                'nombres': 'Juan Alberto',
                'apellidos': 'Pérez Quispe',
                'licencia': 'Q12345678',
                'especialidad': 'Camioneta y Bus',
                'estado': 'Disponible',
                'dni': '70123456',
                'telefono': '951123456',
                'fecha_nacimiento': datetime.date(1985, 5, 12),
                'fecha_ingreso': datetime.date(2020, 1, 15)
            },
            {
                'nombres': 'Carlos',
                'apellidos': 'Ramos Mamani',
                'licencia': 'A23456789',
                'especialidad': 'Camión y Volquete',
                'estado': 'Disponible',
                'dni': '45123456',
                'telefono': '952345678',
                'fecha_nacimiento': datetime.date(1990, 8, 22),
                'fecha_ingreso': datetime.date(2021, 6, 1)
            },
            {
                'nombres': 'Miguel Ángel',
                'apellidos': 'Lope Callo',
                'licencia': 'B34567890',
                'especialidad': 'Bus y Camión',
                'estado': 'Ocupado',
                'dni': '40876543',
                'telefono': '953456789',
                'fecha_nacimiento': datetime.date(1988, 3, 30),
                'fecha_ingreso': datetime.date(2019, 11, 10)
            },
            {
                'nombres': 'Luis Fernando',
                'apellidos': 'Apaza Coila',
                'licencia': 'C45678901',
                'especialidad': 'Camioneta',
                'estado': 'No apto',
                'dni': '44123876',
                'telefono': '954567890',
                'fecha_nacimiento': datetime.date(1995, 12, 5),
                'fecha_ingreso': datetime.date(2023, 3, 20)
            },
            {
                'nombres': 'Pedro Pablo',
                'apellidos': 'Quispe Vilca',
                'licencia': 'D56789012',
                'especialidad': 'Volquete',
                'estado': 'De baja',
                'dni': '30456123',
                'telefono': '955678901',
                'fecha_nacimiento': datetime.date(1980, 2, 18),
                'fecha_ingreso': datetime.date(2015, 5, 1)
            },
            {
                'nombres': 'Jorge',
                'apellidos': 'Cutipa Flores',
                'licencia': 'E67890123',
                'especialidad': 'Camioneta y Bus',
                'estado': 'Disponible',
                'dni': '46543210',
                'telefono': '956789012',
                'fecha_nacimiento': datetime.date(1992, 10, 10),
                'fecha_ingreso': datetime.date(2022, 2, 15)
            },
            {
                'nombres': 'Mario Augusto',
                'apellidos': 'Flores Condori',
                'licencia': 'F78901234',
                'especialidad': 'Camión pesado',
                'estado': 'Ocupado',
                'dni': '29876543',
                'telefono': '957890123',
                'fecha_nacimiento': datetime.date(1983, 7, 25),
                'fecha_ingreso': datetime.date(2018, 4, 10)
            },
            {
                'nombres': 'Roberto',
                'apellidos': 'Choque Vargas',
                'licencia': 'G89012345',
                'especialidad': 'Bus',
                'estado': 'Disponible',
                'dni': '42345678',
                'telefono': '958901234',
                'fecha_nacimiento': datetime.date(1987, 11, 30),
                'fecha_ingreso': datetime.date(2021, 9, 1)
            }
        ]

        conductores = []
        for c_data in conductores_data:
            conductor = Conductor.objects.create(**c_data)
            conductores.append(conductor)

        self.stdout.write('Seeding Vehículos...')
        vehiculos_data = [
            {
                'placa': 'V1A-100',
                'tipo': 'Camioneta',
                'capacidad': 5,
                'estado': 'Disponible',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-C-2026-01',
                'mantenimiento_programado': today + datetime.timedelta(days=45)
            },
            {
                'placa': 'V2B-200',
                'tipo': 'Bus',
                'capacidad': 45,
                'estado': 'En servicio',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-B-2026-02',
                'mantenimiento_programado': today + datetime.timedelta(days=30)
            },
            {
                'placa': 'V3C-300',
                'tipo': 'Camión',
                'capacidad': 12, # Toneladas
                'estado': 'Disponible',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-M-2026-03',
                'mantenimiento_programado': today + datetime.timedelta(days=15)
            },
            {
                'placa': 'V4D-400',
                'tipo': 'Volquete',
                'capacidad': 18,
                'estado': 'En mantenimiento',
                'revision_tecnica_vigente': False, # Vencido para pruebas
                'seguro_vigente': True,
                'homologacion': 'HOM-V-2026-04',
                'mantenimiento_programado': today + datetime.timedelta(days=2)
            },
            {
                'placa': 'V5E-500',
                'tipo': 'Camioneta',
                'capacidad': 5,
                'estado': 'De baja',
                'revision_tecnica_vigente': False,
                'seguro_vigente': False,
                'homologacion': '',
                'mantenimiento_programado': None
            },
            {
                'placa': 'V6F-600',
                'tipo': 'Bus',
                'capacidad': 30,
                'estado': 'Disponible',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-B-2026-06',
                'mantenimiento_programado': today + datetime.timedelta(days=60)
            },
            {
                'placa': 'V7G-700',
                'tipo': 'Camión',
                'capacidad': 15,
                'estado': 'En servicio',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-M-2026-07',
                'mantenimiento_programado': today + datetime.timedelta(days=25)
            },
            {
                'placa': 'V8H-800',
                'tipo': 'Volquete',
                'capacidad': 20,
                'estado': 'Disponible',
                'revision_tecnica_vigente': True,
                'seguro_vigente': True,
                'homologacion': 'HOM-V-2026-08',
                'mantenimiento_programado': today + datetime.timedelta(days=40)
            }
        ]

        vehiculos = []
        for v_data in vehiculos_data:
            vehiculo = Vehiculo.objects.create(**v_data)
            vehiculos.append(vehiculo)

        self.stdout.write('Seeding Documentos de Conductores...')
        # We need documents with different expiration dates:
        # - Expired (Vencido)
        # - Expiring in < 30 days (Por vencer)
        # - Active long term (Vigente)
        
        # Conductor 0 (Juan Pérez) - All active/vigente
        DocumentoConductor.objects.create(
            conductor=conductores[0],
            tipo_documento='Licencia de conducir',
            fecha_emision=today - datetime.timedelta(days=365),
            fecha_vencimiento=today + datetime.timedelta(days=365),
            estado_documento='Vigente'
        )
        DocumentoConductor.objects.create(
            conductor=conductores[0],
            tipo_documento='Examen médico',
            fecha_emision=today - datetime.timedelta(days=90),
            fecha_vencimiento=today + datetime.timedelta(days=270),
            estado_documento='Vigente'
        )

        # Conductor 1 (Carlos Ramos) - Licencia por vencer, Homologación vencida
        DocumentoConductor.objects.create(
            conductor=conductores[1],
            tipo_documento='Licencia de conducir',
            fecha_emision=today - datetime.timedelta(days=700),
            fecha_vencimiento=today + datetime.timedelta(days=15), # Por vencer
            estado_documento='Por vencer'
        )
        DocumentoConductor.objects.create(
            conductor=conductores[1],
            tipo_documento='Homologación',
            fecha_emision=today - datetime.timedelta(days=370),
            fecha_vencimiento=today - datetime.timedelta(days=5), # Vencido
            estado_documento='Vencido'
        )

        # Conductor 2 (Miguel Lope) - Active
        DocumentoConductor.objects.create(
            conductor=conductores[2],
            tipo_documento='Licencia de conducir',
            fecha_emision=today - datetime.timedelta(days=100),
            fecha_vencimiento=today + datetime.timedelta(days=900),
            estado_documento='Vigente'
        )

        # Conductor 3 (Luis Apaza) - Examen médico vencido (justifica No apto)
        DocumentoConductor.objects.create(
            conductor=conductores[3],
            tipo_documento='Licencia de conducir',
            fecha_emision=today - datetime.timedelta(days=50),
            fecha_vencimiento=today + datetime.timedelta(days=600),
            estado_documento='Vigente'
        )
        DocumentoConductor.objects.create(
            conductor=conductores[3],
            tipo_documento='Examen médico',
            fecha_emision=today - datetime.timedelta(days=395),
            fecha_vencimiento=today - datetime.timedelta(days=30), # Vencido hace un mes
            estado_documento='Vencido'
        )

        # Rest of active drivers get valid documents
        for c in [conductores[5], conductores[6], conductores[7]]:
            DocumentoConductor.objects.create(
                conductor=c,
                tipo_documento='Licencia de conducir',
                fecha_emision=today - datetime.timedelta(days=200),
                fecha_vencimiento=today + datetime.timedelta(days=500),
                estado_documento='Vigente'
            )
            DocumentoConductor.objects.create(
                conductor=c,
                tipo_documento='Autorización',
                fecha_emision=today - datetime.timedelta(days=30),
                fecha_vencimiento=today + datetime.timedelta(days=335),
                estado_documento='Vigente'
            )

        self.stdout.write('Seeding Documentos de Vehículos...')
        # Vehículo 0 (V1A-100) - Active
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[0],
            tipo_documento='Seguro',
            fecha_emision=today - datetime.timedelta(days=100),
            fecha_vencimiento=today + datetime.timedelta(days=265),
            estado_documento='Vigente'
        )
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[0],
            tipo_documento='Revisión técnica',
            fecha_emision=today - datetime.timedelta(days=180),
            fecha_vencimiento=today + datetime.timedelta(days=185),
            estado_documento='Vigente'
        )

        # Vehículo 1 (V2B-200) - Active
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[1],
            tipo_documento='Seguro',
            fecha_emision=today - datetime.timedelta(days=300),
            fecha_vencimiento=today + datetime.timedelta(days=65),
            estado_documento='Vigente'
        )

        # Vehículo 2 (V3C-300) - Seguro por vencer
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[2],
            tipo_documento='Revisión técnica',
            fecha_emision=today - datetime.timedelta(days=350),
            fecha_vencimiento=today + datetime.timedelta(days=15), # Por vencer
            estado_documento='Por vencer'
        )
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[2],
            tipo_documento='Seguro',
            fecha_emision=today - datetime.timedelta(days=360),
            fecha_vencimiento=today - datetime.timedelta(days=5), # Vencido
            estado_documento='Vencido'
        )

        # Vehículo 3 (V4D-400) - Revisión técnica vencida
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[3],
            tipo_documento='Revisión técnica',
            fecha_emision=today - datetime.timedelta(days=375),
            fecha_vencimiento=today - datetime.timedelta(days=10), # Vencido
            estado_documento='Vencido'
        )
        DocumentoVehiculo.objects.create(
            vehiculo=vehiculos[3],
            tipo_documento='Seguro',
            fecha_emision=today - datetime.timedelta(days=50),
            fecha_vencimiento=today + datetime.timedelta(days=315),
            estado_documento='Vigente'
        )

        # Active vehicles 5, 6, 7 get valid docs
        for v in [vehiculos[5], vehiculos[6], vehiculos[7]]:
            DocumentoVehiculo.objects.create(
                vehiculo=v,
                tipo_documento='Seguro',
                fecha_emision=today - datetime.timedelta(days=150),
                fecha_vencimiento=today + datetime.timedelta(days=215),
                estado_documento='Vigente'
            )
            DocumentoVehiculo.objects.create(
                vehiculo=v,
                tipo_documento='Revisión técnica',
                fecha_emision=today - datetime.timedelta(days=50),
                fecha_vencimiento=today + datetime.timedelta(days=315),
                estado_documento='Vigente'
            )

        self.stdout.write('Seeding Solicitudes de Servicio...')
        solicitudes_data = [
            {
                'cliente': 'Minera San Rafael',
                'fecha_servicio': today + datetime.timedelta(days=2),
                'hora_servicio': datetime.time(8, 0),
                'origen': 'Juliaca',
                'destino': 'Unidad Minera San Rafael',
                'tipo_servicio': 'Traslado de personal',
                'prioridad': 'Alta',
                'tipo_vehiculo_requerido': 'Camioneta',
                'estado_solicitud': 'Pendiente'
            },
            {
                'cliente': 'Minera Minsur',
                'fecha_servicio': today + datetime.timedelta(days=3),
                'hora_servicio': datetime.time(10, 30),
                'origen': 'Arequipa',
                'destino': 'Unidad Minera San Rafael',
                'tipo_servicio': 'Traslado de carga',
                'prioridad': 'Media',
                'tipo_vehiculo_requerido': 'Camión',
                'estado_solicitud': 'Pendiente'
            },
            {
                'cliente': 'Compañía Minera Antamina',
                'fecha_servicio': today + datetime.timedelta(days=1),
                'hora_servicio': datetime.time(6, 0),
                'origen': 'Huaraz',
                'destino': 'Unidad Minera Antamina',
                'tipo_servicio': 'Traslado mixto',
                'prioridad': 'Alta',
                'tipo_vehiculo_requerido': 'Camión',
                'estado_solicitud': 'Asignada'
            },
            {
                'cliente': 'Minera Cerro Verde',
                'fecha_servicio': today - datetime.timedelta(days=2),
                'hora_servicio': datetime.time(14, 0),
                'origen': 'Arequipa',
                'destino': 'Unidad Minera Cerro Verde',
                'tipo_servicio': 'Traslado de personal',
                'prioridad': 'Baja',
                'tipo_vehiculo_requerido': 'Bus',
                'estado_solicitud': 'Completada'
            },
            {
                'cliente': 'Minera Las Bambas',
                'fecha_servicio': today + datetime.timedelta(days=5),
                'hora_servicio': datetime.time(7, 0),
                'origen': 'Cusco',
                'destino': 'Unidad Minera Las Bambas',
                'tipo_servicio': 'Traslado de carga',
                'prioridad': 'Alta',
                'tipo_vehiculo_requerido': 'Volquete',
                'estado_solicitud': 'Cancelada'
            },
            {
                'cliente': 'Minera Buenaventura',
                'fecha_servicio': today + datetime.timedelta(days=4),
                'hora_servicio': datetime.time(9, 0),
                'origen': 'Puno',
                'destino': 'Mina Tambomayo',
                'tipo_servicio': 'Traslado de personal',
                'prioridad': 'Media',
                'tipo_vehiculo_requerido': 'Bus',
                'estado_solicitud': 'Reprogramada'
            }
        ]

        for s_data in solicitudes_data:
            SolicitudServicio.objects.create(**s_data)

        self.stdout.write(self.style.SUCCESS('Successfully seeded all test data!'))
