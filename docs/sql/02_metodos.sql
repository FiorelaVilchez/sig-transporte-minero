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
