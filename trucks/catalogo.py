"""Valores iniciales del catálogo de tipos de vehículo (M0)."""

# nombre, asientos de referencia, experiencia mínima (años), categoría mínima, activo
TIPOS_INICIALES = [
    ('Camioneta', 4, 3, 'A-IIa', True),
    ('Van / Sprinter', 15, 3, 'A-IIb', True),
    ('Minibús', 30, 5, 'A-IIIa', True),
    ('Bus', 45, 5, 'A-IIIa', True),
    # Tipos de la versión 1.0 que la empresa no usa para transporte de personal.
    ('Camión', 3, 3, 'A-IIIb', False),
    ('Volquete', 3, 3, 'A-IIIc', False),
]
