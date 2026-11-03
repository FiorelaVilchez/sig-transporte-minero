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
