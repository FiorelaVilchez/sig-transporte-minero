-- Dominios: reglas de formato y de valor que la base valida por sí misma.
CREATE DOMAIN dni_peru AS varchar(8)
    CHECK (VALUE ~ '^[0-9]{8}$');

CREATE DOMAIN placa_vehiculo AS varchar(15)
    CHECK (VALUE ~ '^[A-Z0-9]{3}-[0-9]{3}$');

CREATE DOMAIN monto_soles AS numeric(10,2)
    CHECK (VALUE >= 0);

-- Tipos enumerados para los estados del proceso.
CREATE TYPE estado_solicitud_t AS ENUM
    ('Pendiente', 'Asignada', 'Reprogramada', 'Completada', 'Cancelada');

CREATE TYPE estado_operativo_t AS ENUM
    ('Programado', 'Listo para salir', 'En ruta', 'Completado', 'Con incidencia', 'Cancelado');

-- Tipo compuesto que devuelve el cálculo de una valorización.
CREATE TYPE resultado_valorizacion AS (
    monto_base      monto_soles,
    km_adicionales  integer,
    monto_adicional monto_soles,
    total           monto_soles
);

-- Aplicación de los tipos a las tablas del sistema.
UPDATE drivers_conductor SET dni = trim(dni) WHERE dni <> trim(dni);
UPDATE trucks_vehiculo SET placa = upper(trim(placa)) WHERE placa <> upper(trim(placa));

ALTER TABLE drivers_conductor ALTER COLUMN dni TYPE dni_peru;
ALTER TABLE trucks_vehiculo ALTER COLUMN placa TYPE placa_vehiculo;

ALTER TABLE service_requests_solicitudservicio
    ALTER COLUMN estado_solicitud TYPE estado_solicitud_t
    USING estado_solicitud::estado_solicitud_t;

ALTER TABLE assignments_asignacion
    ALTER COLUMN estado_operativo TYPE estado_operativo_t
    USING estado_operativo::estado_operativo_t;

ALTER TABLE billing_tarifa ALTER COLUMN tarifa_base TYPE monto_soles;
ALTER TABLE billing_valorizacion ALTER COLUMN monto_base TYPE monto_soles;
ALTER TABLE billing_valorizacion ALTER COLUMN monto_adicional TYPE monto_soles;
ALTER TABLE billing_valorizacion ALTER COLUMN total TYPE monto_soles;
ALTER TABLE assignments_gastoservicio ALTER COLUMN monto TYPE monto_soles;
