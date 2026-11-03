"""
Extensiones de PostgreSQL sobre las tablas del sistema: dominios, tipos
enumerados, un tipo compuesto, métodos sobre filas, un trigger y un
procedimiento almacenado. El mismo SQL está en docs/sql. En SQLite no se aplica.
"""
from django.db import migrations

SQL = [
    r"""
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
""",
    r"""
-- Métodos sobre filas: se pueden usar como atributos, por ejemplo a.km_recorridos.
CREATE OR REPLACE FUNCTION km_recorridos(a assignments_asignacion)
RETURNS integer
LANGUAGE sql STABLE
AS $$
    SELECT CASE
        WHEN a.km_inicial IS NOT NULL AND a.km_final IS NOT NULL AND a.km_final >= a.km_inicial
        THEN a.km_final - a.km_inicial
    END;
$$;

CREATE OR REPLACE FUNCTION dias_sin_conformidad(v billing_valorizacion)
RETURNS integer
LANGUAGE sql STABLE
AS $$
    SELECT CASE
        WHEN v.estado IN ('Enviada', 'Observada') AND v.fecha_envio IS NOT NULL
        THEN current_date - v.fecha_envio
        ELSE 0
    END;
$$;

-- Cálculo de una valorización con la misma regla que Valorizacion.calcular().
DROP FUNCTION IF EXISTS fn_calcular_valorizacion(bigint);

CREATE FUNCTION fn_calcular_valorizacion(p_valorizacion_id bigint)
RETURNS resultado_valorizacion
LANGUAGE plpgsql STABLE
AS $$
DECLARE
    v billing_valorizacion%ROWTYPE;
    t billing_tarifa%ROWTYPE;
    r resultado_valorizacion;
BEGIN
    SELECT * INTO v FROM billing_valorizacion WHERE id = p_valorizacion_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No existe la valorización %', p_valorizacion_id;
    END IF;

    IF v.tarifa_id IS NULL THEN
        r.monto_base      := v.monto_base;
        r.km_adicionales  := 0;
        r.monto_adicional := 0;
    ELSE
        SELECT * INTO t FROM billing_tarifa WHERE id = v.tarifa_id;
        r.monto_base      := t.tarifa_base;
        r.km_adicionales  := GREATEST(0, v.km_recorridos - t.km_incluidos);
        r.monto_adicional := r.km_adicionales * t.precio_km_adicional;
    END IF;

    r.total := r.monto_base + r.monto_adicional;
    RETURN r;
END;
$$;
""",
    r"""
-- Impide registrar una asignación con un vehículo en mantenimiento o de baja.
CREATE OR REPLACE FUNCTION trg_validar_vehiculo_asignacion()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_estado varchar(20);
    v_placa  varchar(15);
BEGIN
    IF NEW.vehiculo_id IS NULL OR NEW.estado_operativo NOT IN ('Programado', 'Listo para salir') THEN
        RETURN NEW;
    END IF;

    SELECT estado, placa INTO v_estado, v_placa
    FROM trucks_vehiculo WHERE truck_id = NEW.vehiculo_id;

    IF v_estado IN ('En mantenimiento', 'De baja') THEN
        RAISE EXCEPTION 'El vehículo % está "%" y no puede asignarse', v_placa, v_estado
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS asignacion_vehiculo_habilitado ON assignments_asignacion;

CREATE TRIGGER asignacion_vehiculo_habilitado
    BEFORE INSERT OR UPDATE OF vehiculo_id ON assignments_asignacion
    FOR EACH ROW
    EXECUTE FUNCTION trg_validar_vehiculo_asignacion();
""",
    r"""
-- Cierra un servicio en ruta y genera su valorización en una sola transacción.
CREATE OR REPLACE PROCEDURE sp_completar_servicio(p_asignacion_id bigint, p_km_final integer)
LANGUAGE plpgsql
AS $$
DECLARE
    a          assignments_asignacion%ROWTYPE;
    s          service_requests_solicitudservicio%ROWTYPE;
    t          billing_tarifa%ROWTYPE;
    v_km       integer;
    v_base     numeric(10,2) := 0;
    v_adic     integer := 0;
    v_monto    numeric(10,2) := 0;
    v_obs      text := '';
    v_cliente  varchar(150);
BEGIN
    SELECT * INTO a FROM assignments_asignacion
    WHERE assignment_id = p_asignacion_id FOR UPDATE;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No existe la asignación %', p_asignacion_id;
    END IF;
    IF a.estado_operativo <> 'En ruta' THEN
        RAISE EXCEPTION 'La asignación % no está en ruta (estado actual: %)', p_asignacion_id, a.estado_operativo;
    END IF;
    IF a.km_inicial IS NOT NULL AND p_km_final < a.km_inicial THEN
        RAISE EXCEPTION 'El kilometraje final (%) es menor que el inicial (%)', p_km_final, a.km_inicial;
    END IF;

    UPDATE assignments_asignacion
    SET km_final = p_km_final, estado_operativo = 'Completado', fin_real = now(), updated_at = now()
    WHERE assignment_id = a.assignment_id;

    UPDATE drivers_conductor SET estado = 'Disponible', updated_at = now()
    WHERE driver_id = a.conductor_id AND estado = 'Ocupado';

    UPDATE trucks_vehiculo SET estado = 'Disponible', updated_at = now()
    WHERE truck_id = a.vehiculo_id AND estado = 'En servicio';

    SELECT * INTO s FROM service_requests_solicitudservicio
    WHERE request_id = a.solicitud_id FOR UPDATE;

    UPDATE service_requests_solicitudservicio
    SET estado_solicitud = 'Completada', updated_at = now()
    WHERE request_id = s.request_id;

    INSERT INTO service_requests_cambiosolicitud
        (solicitud_id, usuario_id, fecha, campo, valor_anterior, valor_nuevo, motivo)
    VALUES
        (s.request_id, NULL, now(), 'Estado de Solicitud', s.estado_solicitud::text, 'Completada', 'Servicio finalizado');

    IF EXISTS (SELECT 1 FROM billing_valorizacion WHERE solicitud_id = s.request_id) THEN
        RETURN;
    END IF;

    v_km := CASE WHEN a.km_inicial IS NOT NULL THEN p_km_final - a.km_inicial END;
    v_km := COALESCE(NULLIF(v_km, 0), NULLIF(s.km_estimados, 0), 0);

    SELECT tf.* INTO t
    FROM billing_tarifa tf
    JOIN trucks_tipovehiculo tv ON tv.id = tf.tipo_vehiculo_id
    WHERE tf.cliente_id = s.cliente_id AND tv.nombre = s.tipo_vehiculo_requerido AND tf.activo
    LIMIT 1;

    IF FOUND THEN
        v_base  := t.tarifa_base;
        v_adic  := GREATEST(0, v_km - t.km_incluidos);
        v_monto := v_adic * t.precio_km_adicional;
    ELSE
        SELECT razon_social INTO v_cliente FROM crm_cliente WHERE id = s.cliente_id;
        v_obs := format('No hay tarifa activa para %s y %s. Registre la tarifa en Configuración y recalcule.',
                        v_cliente, s.tipo_vehiculo_requerido);
    END IF;

    INSERT INTO billing_valorizacion
        (solicitud_id, tarifa_id, monto_base, km_recorridos, km_adicionales, monto_adicional, total,
         estado, numero_factura, observacion, created_at, updated_at)
    VALUES
        (s.request_id, CASE WHEN v_obs = '' THEN t.id END, v_base, v_km, v_adic, v_monto, v_base + v_monto,
         'Borrador', '', v_obs, now(), now());
END;
$$;
""",
]

SQL_REVERSO = r"""
DROP PROCEDURE IF EXISTS sp_completar_servicio(bigint, integer);
DROP TRIGGER IF EXISTS asignacion_vehiculo_habilitado ON assignments_asignacion;
DROP FUNCTION IF EXISTS trg_validar_vehiculo_asignacion();
DROP FUNCTION IF EXISTS fn_calcular_valorizacion(bigint);
DROP FUNCTION IF EXISTS dias_sin_conformidad(billing_valorizacion);
DROP FUNCTION IF EXISTS km_recorridos(assignments_asignacion);
ALTER TABLE assignments_gastoservicio ALTER COLUMN monto TYPE numeric(10,2);
ALTER TABLE billing_valorizacion ALTER COLUMN total TYPE numeric(10,2);
ALTER TABLE billing_valorizacion ALTER COLUMN monto_adicional TYPE numeric(10,2);
ALTER TABLE billing_valorizacion ALTER COLUMN monto_base TYPE numeric(10,2);
ALTER TABLE billing_tarifa ALTER COLUMN tarifa_base TYPE numeric(10,2);
ALTER TABLE assignments_asignacion ALTER COLUMN estado_operativo TYPE varchar(20) USING estado_operativo::text;
ALTER TABLE service_requests_solicitudservicio ALTER COLUMN estado_solicitud TYPE varchar(20) USING estado_solicitud::text;
ALTER TABLE trucks_vehiculo ALTER COLUMN placa TYPE varchar(15);
ALTER TABLE drivers_conductor ALTER COLUMN dni TYPE varchar(8);
DROP TYPE IF EXISTS resultado_valorizacion;
DROP TYPE IF EXISTS estado_operativo_t;
DROP TYPE IF EXISTS estado_solicitud_t;
DROP DOMAIN IF EXISTS monto_soles;
DROP DOMAIN IF EXISTS placa_vehiculo;
DROP DOMAIN IF EXISTS dni_peru;
"""


def aplicar(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        for bloque in SQL:
            cursor.execute(bloque)


def revertir(apps, schema_editor):
    if schema_editor.connection.vendor != 'postgresql':
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_REVERSO)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_perfilusuario_rol'),
        ('assignments', '0003_asignacion_estado_operativo_asignacion_fin_real_and_more'),
        ('billing', '0003_cliente_fk_final'),
        ('service_requests', '0004_cliente_fk_final'),
        ('drivers', '0003_alter_conductor_dni'),
        ('trucks', '0004_alter_vehiculo_placa'),
        ('crm', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
