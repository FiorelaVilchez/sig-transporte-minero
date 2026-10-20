"""
Datos de demostración de la versión 2.0 (empresa ficticia de transporte de
personal minero en Puno). Carga catálogos, conductores, unidades, documentos
según la matriz de requisitos, tarifas, solicitudes y servicios en distintas
etapas para recorrer todos los módulos.

Uso:  python manage.py seed_data   y luego   python manage.py seed_users
"""
import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from alerts.models import Alerta
from assignments.models import (
    Asignacion, ChecklistPreoperacional, GastoServicio, Incidencia, Notificacion,
)
from billing.models import Tarifa, Valorizacion
from billing.services import cambiar_estado, generar_valorizacion
from documents.catalogo import cargar_requisitos
from documents.models import DocumentoConductor, DocumentoVehiculo, RequisitoDocumental
from drivers.models import Conductor
from service_requests.models import CambioSolicitud, SolicitudServicio
from trucks.catalogo import TIPOS_INICIALES
from trucks.models import TipoVehiculo, Vehiculo

CLIENTES = [
    'Andes Perforaciones S.A.C.',
    'Montajes Titicaca S.R.L.',
    'Geoservicios del Sur E.I.R.L.',
    'Construcciones Altiplánicas S.A.C.',
]

# nombres, apellidos, dni, categoría, fecha de licencia, tipos, estado, teléfono, ingreso
CONDUCTORES = [
    ('Juan Alberto', 'Pérez Quispe', '41258763', 'A-IIb', '2015-03-10', ['Camioneta', 'Van / Sprinter'], 'Disponible', '951204118', '2019-02-01'),
    ('Roberto', 'Choque Vargas', '40117652', 'A-IIIc', '2010-06-21', ['Minibús', 'Bus'], 'Disponible', '951330274', '2016-08-15'),
    ('Jorge', 'Cutipa Flores', '45210987', 'A-IIa', '2018-11-05', ['Camioneta'], 'Disponible', '952118403', '2021-04-12'),
    ('Luis Fernando', 'Apaza Coila', '44123876', 'A-IIb', '2017-01-18', ['Camioneta', 'Van / Sprinter'], 'No apto', '954567890', '2023-03-20'),
    ('Carlos', 'Ramos Mamani', '42876501', 'A-IIIa', '2014-09-02', ['Bus'], 'Disponible', '953771026', '2018-10-01'),
    ('Edwin', 'Huanca Larico', '43901276', 'A-IIIa', '2016-05-30', ['Van / Sprinter', 'Minibús'], 'Disponible', '951889640', '2020-07-06'),
    ('Wilber', 'Condori Ticona', '46550231', 'A-IIa', '2020-02-14', ['Camioneta'], 'Disponible', '955402337', '2022-01-10'),
    ('Ronald', 'Mamani Quispe', '40987312', 'A-IIIc', '2009-04-08', ['Minibús', 'Bus'], 'Disponible', '951145908', '2015-05-04'),
    ('Percy', 'Calla Huarachi', '42310894', 'A-IIIa', '2012-12-01', ['Camioneta', 'Van / Sprinter', 'Bus'], 'Disponible', '952663105', '2017-09-18'),
    ('Hugo', 'Pari Chambi', '47019284', 'A-IIb', '2019-07-22', ['Van / Sprinter'], 'De baja', '954210776', '2022-06-01'),
]

# placa, tipo, asientos, estado
VEHICULOS = [
    ('ABK-101', 'Camioneta', 4, 'Disponible'),
    ('ABK-102', 'Camioneta', 4, 'Disponible'),
    ('ABK-103', 'Camioneta', 4, 'En mantenimiento'),
    ('C3T-201', 'Van / Sprinter', 15, 'Disponible'),
    ('C3T-202', 'Van / Sprinter', 15, 'Disponible'),
    ('D5M-301', 'Minibús', 30, 'Disponible'),
    ('D5M-302', 'Minibús', 30, 'Disponible'),
    ('F7B-401', 'Bus', 45, 'Disponible'),
    ('F7B-402', 'Bus', 45, 'Disponible'),
    ('F7B-403', 'Bus', 49, 'Disponible'),
]

# tipo, tarifa base, km incluidos, precio por km adicional
TARIFAS_BASE = [
    ('Camioneta', '680.00', 380, '3.20'),
    ('Van / Sprinter', '1150.00', 380, '4.50'),
    ('Minibús', '1650.00', 380, '5.80'),
    ('Bus', '2250.00', 380, '7.00'),
]


class Command(BaseCommand):
    help = 'Carga datos de demostración coherentes para el SIG de transporte minero (versión 2.0).'

    @transaction.atomic
    def handle(self, *args, **options):
        hoy = datetime.date.today()
        d = lambda n: hoy + datetime.timedelta(days=n)  # noqa: E731

        self.stdout.write('Eliminando datos operativos anteriores...')
        Valorizacion.objects.all().delete()
        Alerta.objects.all().delete()
        Notificacion.objects.all().delete()
        GastoServicio.objects.all().delete()
        Incidencia.objects.all().delete()
        ChecklistPreoperacional.objects.all().delete()
        Asignacion.objects.all().delete()
        CambioSolicitud.objects.all().delete()
        SolicitudServicio.objects.all().delete()
        DocumentoConductor.objects.all().delete()
        DocumentoVehiculo.objects.all().delete()
        Tarifa.objects.all().delete()
        Vehiculo.objects.all().delete()
        Conductor.objects.all().delete()

        self.stdout.write('Catálogo de tipos y matriz de requisitos...')
        for nombre, asientos, exp, cat, activo in TIPOS_INICIALES:
            TipoVehiculo.objects.update_or_create(
                nombre=nombre,
                defaults={'asientos_referencia': asientos, 'experiencia_minima_anios': exp,
                          'categoria_licencia_minima': cat, 'activo': activo},
            )
        cargar_requisitos(RequisitoDocumental, TipoVehiculo)

        self.stdout.write('Conductores...')
        conductores = []
        for nom, ape, dni, cat, flic, tipos, estado, tel, ingreso in CONDUCTORES:
            c = Conductor.objects.create(
                nombres=nom, apellidos=ape, dni=dni, licencia=f'Q{dni}', categoria_licencia=cat,
                fecha_obtencion_licencia=datetime.date.fromisoformat(flic), estado=estado, telefono=tel,
                especialidad=', '.join(tipos), fecha_nacimiento=datetime.date(1980 + len(ape) % 15, 3, 14),
                fecha_ingreso=datetime.date.fromisoformat(ingreso),
            )
            c.tipos_habilitados.set(TipoVehiculo.objects.filter(nombre__in=tipos))
            conductores.append(c)

        self.stdout.write('Unidades...')
        vehiculos = [
            Vehiculo.objects.create(placa=p, tipo_id=t, capacidad=a, estado=e,
                                    homologacion=f'HOM-{p}', mantenimiento_programado=d(30 + i * 7))
            for i, (p, t, a, e) in enumerate(VEHICULOS)
        ]

        self.stdout.write('Documentos según la matriz...')
        for i, c in enumerate(conductores):
            for j, req in enumerate(RequisitoDocumental.objects.filter(aplica_a='Conductor')):
                vence = d(150 + (i * 37 + j * 23) % 300)
                DocumentoConductor.objects.create(
                    conductor=c, tipo_documento=req.tipo_documento, fecha_emision=vence - datetime.timedelta(days=365),
                    fecha_vencimiento=vence, estado_mina='Aprobado' if req.requiere_visto_bueno_mina else 'No requiere',
                )
        for i, v in enumerate(vehiculos):
            for j, req in enumerate(RequisitoDocumental.objects.filter(aplica_a='Vehículo').prefetch_related('tipos_vehiculo')):
                if not req.aplica_al_tipo(v.tipo):
                    continue
                vence = d(120 + (i * 41 + j * 19) % 280) if req.vence else None
                DocumentoVehiculo.objects.create(
                    vehiculo=v, tipo_documento=req.tipo_documento, fecha_emision=d(-200),
                    fecha_vencimiento=vence, estado_mina='Aprobado' if req.requiere_visto_bueno_mina else 'No requiere',
                )

        # Casos para demostrar las reglas
        def doc_c(idx, tipo):
            return DocumentoConductor.objects.get(conductor=conductores[idx], tipo_documento=tipo)

        def doc_v(idx, tipo):
            return DocumentoVehiculo.objects.get(vehiculo=vehiculos[idx], tipo_documento=tipo)

        x = doc_c(3, 'Examen médico'); x.fecha_emision, x.fecha_vencimiento = d(-395), d(-30); x.save()   # R2
        x = doc_c(4, 'Licencia de conducir'); x.fecha_vencimiento = d(15); x.save()                      # R3
        x = doc_c(5, 'Inducción en mina'); x.fecha_emision, x.fecha_vencimiento, x.estado_mina = d(-2), d(363), 'Pendiente'; x.save()  # R8
        doc_c(8, 'Seguro Vida Ley').delete()                                                              # R1
        x = doc_v(1, 'SOAT'); x.fecha_vencimiento = d(10); x.save()                                      # R3
        x = doc_v(4, 'Revisión técnica'); x.fecha_emision, x.fecha_vencimiento = d(-375), d(-10); x.save()  # R2
        x = doc_v(6, 'Certificado GPS'); x.estado_mina = 'Pendiente'; x.save()                            # R8
        doc_v(8, 'Seguro de ocupantes').delete()                                                          # R1

        self.stdout.write('Tarifas...')
        for cliente in CLIENTES:
            for tipo, base, km, pkm in TARIFAS_BASE:
                Tarifa.objects.create(cliente=cliente, tipo_vehiculo=TipoVehiculo.objects.get(nombre=tipo), tarifa_base=Decimal(base),
                                      km_incluidos=km, precio_km_adicional=Decimal(pkm))

        self.stdout.write('Solicitudes y servicios...')

        def sol(cliente, dia, hora, dur, origen, destino, tipo, pax, prioridad, estado, km=380):
            return SolicitudServicio.objects.create(
                cliente=CLIENTES[cliente], fecha_servicio=d(dia), hora_servicio=datetime.time(*hora),
                origen=origen, destino=destino, tipo_servicio='Traslado de personal', prioridad=prioridad,
                tipo_vehiculo_requerido_id=tipo, pasajeros=pax, duracion_horas=dur, km_estimados=km,
                estado_solicitud=estado,
            )

        def asig(s, ci, vi, operativo, km_ini=None, km_fin=None, checklist=None):
            a = Asignacion.objects.create(
                solicitud=s, conductor=conductores[ci], vehiculo=vehiculos[vi], estado_asignacion='Aprobada',
                estado_operativo=operativo, km_inicial=km_ini, km_final=km_fin,
            )
            if checklist is not None:
                ChecklistPreoperacional.objects.create(
                    asignacion=a, frenos=True, llantas=True, luces=True, cinturones=True, botiquin=True,
                    extintor=True, radio_gps=True, horas_sueno=Decimal('7.5'), km_inicial=km_ini or 0, aprobado=checklist,
                )
            return a

        ruta_ca = ('Juliaca', 'U.M. Cerro Azul')
        ruta_pb = ('Puno', 'U.M. Pampa Blanca')

        # Servicios cerrados con valorización en distintas etapas del cobro
        cerrados = [
            (sol(0, -26, (5, 30), 10, *ruta_ca, 'Van / Sprinter', 12, 'Media', 'Completada'), 0, 3, 52310, 52712, ['Enviada', 'Conforme', 'Facturada', 'Pagada']),
            (sol(1, -12, (5, 0), 10, *ruta_ca, 'Bus', 40, 'Alta', 'Completada'), 1, 7, 88120, 88540, ['Enviada', 'Conforme', 'Facturada']),
            (sol(2, -20, (6, 0), 8, *ruta_ca, 'Camioneta', 3, 'Media', 'Completada'), 2, 0, 40210, 40598, ['Enviada']),
            (sol(3, -3, (5, 30), 10, *ruta_ca, 'Minibús', 26, 'Alta', 'Completada'), 7, 5, 61020, 61455, []),
        ]
        for s, ci, vi, k0, k1, pasos in cerrados:
            a = asig(s, ci, vi, 'Completado', k0, k1, checklist=True)
            GastoServicio.objects.create(asignacion=a, concepto='Combustible', monto=Decimal('240.00'), detalle='Grifo Juliaca')
            GastoServicio.objects.create(asignacion=a, concepto='Peaje', monto=Decimal('18.50'))
            v = generar_valorizacion(s)
            for paso in pasos:
                cambiar_estado(v, paso, numero_factura=f'F001-{s.pk:06d}')
        # La valorización enviada hace 20 días aparece como cobro atrasado.
        Valorizacion.objects.filter(estado='Enviada').update(fecha_envio=d(-20))

        # Servicio con incidencia grave (reemplazo pendiente)
        s = sol(0, -1, (6, 0), 8, *ruta_pb, 'Van / Sprinter', 10, 'Alta', 'Reprogramada', km=460)
        a = asig(s, 5, 4, 'Con incidencia', 70120, checklist=True)
        Incidencia.objects.create(asignacion=a, tipo='Falla mecánica', gravedad='Alta',
                                  descripcion='Recalentamiento del motor en el km 85; personal a la espera en la vía.')
        CambioSolicitud.objects.create(solicitud=s, campo='Estado de Solicitud', valor_anterior='Asignada',
                                       valor_nuevo='Reprogramada', motivo='Incidencia grave: Falla mecánica. Requiere reemplazo.')

        # Servicio en ruta hoy
        s = sol(1, 0, (5, 30), 10, *ruta_ca, 'Bus', 38, 'Alta', 'Asignada')
        asig(s, 4, 8, 'En ruta', 90450, checklist=True)
        conductores[4].estado = 'Ocupado'; conductores[4].save()
        vehiculos[8].estado = 'En servicio'; vehiculos[8].save()

        # Servicios programados (para el portal del conductor y la agenda)
        s = sol(2, 1, (6, 0), 8, *ruta_ca, 'Camioneta', 3, 'Media', 'Asignada')
        asig(s, 0, 0, 'Programado')
        s = sol(3, 2, (5, 0), 10, *ruta_pb, 'Bus', 42, 'Alta', 'Asignada', km=460)
        asig(s, 1, 9, 'Programado')

        # Solicitudes por asignar
        sol(0, 2, (7, 0), 8, *ruta_ca, 'Camioneta', 3, 'Alta', 'Pendiente')
        sol(1, 3, (5, 30), 10, *ruta_pb, 'Minibús', 24, 'Media', 'Pendiente', km=460)
        sol(2, 4, (6, 0), 10, *ruta_ca, 'Bus', 44, 'Alta', 'Pendiente')
        sol(3, 1, (14, 0), 6, *ruta_ca, 'Van / Sprinter', 14, 'Baja', 'Pendiente')
        s = sol(0, -6, (7, 0), 8, *ruta_pb, 'Van / Sprinter', 10, 'Baja', 'Cancelada', km=460)
        CambioSolicitud.objects.create(solicitud=s, campo='Estado de Solicitud', valor_anterior='Pendiente',
                                       valor_nuevo='Cancelada', motivo='El cliente postergó la movilización de su personal.')
        for s in SolicitudServicio.objects.all():
            CambioSolicitud.objects.create(solicitud=s, campo='registro', valor_nuevo='Pendiente', motivo='Solicitud registrada')

        from alerts.services import escanear_documentos_y_generar_alertas
        escanear_documentos_y_generar_alertas()

        self.stdout.write(self.style.SUCCESS(
            f'Datos cargados: {len(conductores)} conductores, {len(vehiculos)} unidades, '
            f'{SolicitudServicio.objects.count()} solicitudes, {Valorizacion.objects.count()} valorizaciones.'
        ))
