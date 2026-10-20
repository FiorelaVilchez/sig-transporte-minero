# SIG Transporte Minero — Versión 2.0

Esta versión incorpora las mejoras M0 a M7 propuestas en el diagnóstico AS-IS / TO-BE.

## Resumen de mejoras

| Código | Mejora | Dónde se ve |
|---|---|---|
| M0 | Catálogo de tipos de vehículo (Camioneta, Van / Sprinter, Minibús, Bus). El tipo del vehículo y de la solicitud se elige de una lista. El conductor marca con casillas los tipos que puede manejar, su categoría de licencia y la fecha en que la obtuvo. | Configuración, Registro de Conductores, Registro de Vehículos |
| M1 | Matriz de requisitos documentales: qué documento exige cada conductor y cada unidad, si bloquea, si vence y si necesita visto bueno de la mina. Nuevos tipos: SOAT, póliza todo riesgo, seguro de ocupantes, tarjeta de propiedad, certificado GPS, manejo defensivo, inducción en mina, Seguro Vida Ley y récord de conductor. | Configuración, Control Documental, ficha del conductor y del vehículo |
| M2 | Bitácora de cambios de cada solicitud (quién, cuándo, qué y por qué). Si cambia una solicitud ya asignada, el sistema vuelve a validar la asignación y avisa al conductor. Cancelación con motivo. | Ficha de la solicitud |
| M3 | Checklist preoperacional del conductor. Si falla frenos, llantas, luces o cinturones, o durmió menos de 6 horas, la unidad no sale y se alerta a operaciones. | Mis Servicios (rol Conductor) |
| M4 | Estados del servicio (Programado, Listo para salir, En ruta, Completado, Con incidencia, Cancelado), reporte de incidencias y registro de gastos. Una incidencia grave libera los recursos y deja la solicitud para reasignar. | Mis Servicios, ficha de la solicitud |
| M5 | Disponibilidad por horario: un conductor puede tener varios servicios si no se cruzan y descansa 8 horas entre ellos; tope de 60 horas por semana; la asignación automática prioriza a quien tiene menos horas. Reglas R6 a R10. Programación semanal. | Asignación Automática, Programación Semanal |
| M6 | Tarifas por cliente y tipo de unidad. Cada servicio completado genera su valorización (tarifa base más km adicionales) con el ciclo Borrador, Enviada, Observada, Conforme, Facturada y Pagada. Alerta de cobro a los 15 días sin conformidad. Nuevo rol Finanzas. | Valorizaciones, Configuración |
| M7 | Indicadores de ejecución, cumplimiento y cobranza en el dashboard y dos nuevos CSV para Power BI (ejecución de servicios y valorizaciones). | Dashboard Operativo, Reportes Gerenciales |

## Reglas del motor de asignación

| Regla | Condición | Efecto |
|---|---|---|
| R1 | Falta un documento obligatorio, o la licencia está vencida | Bloquea |
| R2 | Documento obligatorio vencido (incluye revisión técnica) | Bloquea |
| R3 | Documento por vencer en 30 días o menos | Observa |
| R4 | Vehículo en mantenimiento o de baja | Bloquea |
| R5 | Conductor no apto, de baja u ocupado en ruta el mismo día | Bloquea |
| R6 | Conductor no habilitado para el tipo, experiencia o categoría insuficiente | Bloquea |
| R7 | Asientos menores que los pasajeros | Bloquea |
| R8 | Documento pendiente u observado por la mina | Bloquea |
| R9 | Cruce de horario (8 h de descanso para el conductor) | Bloquea |
| R10 | Superaría 60 horas de manejo en la semana | Bloquea |

## Actualizar una instalación existente

```bash
git pull
pip install -r requirements.txt
python manage.py migrate          # convierte los datos existentes; no se pierde información
python manage.py seed_data        # opcional: borra los datos operativos y carga la demostración 2.0
python manage.py seed_users       # opcional: usuarios de prueba, incluido finanzas1 / Finanzas2026*
python manage.py test             # 79 pruebas
```

Las migraciones crean el catálogo de tipos a partir de los valores existentes, marcan los tipos
habilitados de cada conductor leyendo su especialidad anterior y cargan la matriz de requisitos.
