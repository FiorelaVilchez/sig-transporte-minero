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

DROP TRIGGER IF EXISTS asignacion_vehiculo_habilitado ON assignments_asignacion;

CREATE TRIGGER asignacion_vehiculo_habilitado
    BEFORE INSERT OR UPDATE OF vehiculo_id ON assignments_asignacion
    FOR EACH ROW
    EXECUTE FUNCTION trg_validar_vehiculo_asignacion();
