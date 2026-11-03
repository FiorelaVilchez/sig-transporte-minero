from django.db import migrations

# El trigger solo debe validar cuando se registra o se cambia el vehículo.
# Django actualiza todas las columnas al guardar, así que sin esta condición
# también se disparaba al guardar el checklist de una asignación ya existente.

FUNCION = """
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
    IF TG_OP = 'UPDATE' AND NEW.vehiculo_id = OLD.vehiculo_id THEN
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
"""

FUNCION_ANTERIOR = """
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
"""


def aplicar(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(FUNCION)


def revertir(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(FUNCION_ANTERIOR)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_base_activa_postgresql'),
    ]

    operations = [
        migrations.RunPython(aplicar, revertir),
    ]
