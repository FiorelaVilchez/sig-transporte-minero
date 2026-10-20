"""Matriz inicial de requisitos documentales (M1)."""

# aplica_a, tipo_documento, bloqueante, vence, visto bueno de mina, solo para tipos
REQUISITOS_INICIALES = [
    ('Conductor', 'Licencia de conducir', True, True, False, []),
    ('Conductor', 'Manejo defensivo', True, True, False, []),
    ('Conductor', 'Inducción en mina', True, True, True, []),
    ('Conductor', 'Examen médico', True, True, True, []),
    ('Conductor', 'Seguro Vida Ley', True, True, False, []),
    ('Conductor', 'Récord de conductor', False, True, False, []),
    ('Vehículo', 'SOAT', True, True, False, []),
    ('Vehículo', 'Revisión técnica', True, True, False, []),
    ('Vehículo', 'Póliza todo riesgo', True, True, False, []),
    ('Vehículo', 'Seguro de ocupantes', True, True, False, ['Minibús', 'Bus']),
    ('Vehículo', 'Tarjeta de propiedad', True, False, False, []),
    ('Vehículo', 'Certificado GPS', True, True, True, []),
]


def cargar_requisitos(RequisitoDocumental, TipoVehiculo):
    for aplica, tipo_doc, bloq, vence, mina, tipos in REQUISITOS_INICIALES:
        req, creado = RequisitoDocumental.objects.get_or_create(
            aplica_a=aplica, tipo_documento=tipo_doc,
            defaults={'bloqueante': bloq, 'vence': vence, 'requiere_visto_bueno_mina': mina},
        )
        if creado and tipos:
            req.tipos_vehiculo.set(TipoVehiculo.objects.filter(nombre__in=tipos))
