-- Consultas de los tres KPI sobre el esquema en estrella del Data Mart.

-- KPI 1. Ingreso valorizado por cliente, mes y tipo de unidad
SELECT c.razon_social AS cliente,
       t.anio,
       t.mes,
       t.nombre_mes,
       v.tipo_unidad,
       count(*)           AS servicios,
       sum(f.monto_total) AS ingreso_valorizado
FROM datamart.fact_servicio f
JOIN datamart.dim_cliente c  ON c.sk_cliente = f.sk_cliente
JOIN datamart.dim_tiempo t   ON t.sk_tiempo = f.sk_tiempo
JOIN datamart.dim_vehiculo v ON v.sk_vehiculo = f.sk_vehiculo
GROUP BY c.razon_social, t.anio, t.mes, t.nombre_mes, v.tipo_unidad
ORDER BY t.anio, t.mes, ingreso_valorizado DESC;

-- KPI 1 (resumen). Ingreso valorizado por cliente
SELECT c.razon_social AS cliente,
       count(*)           AS servicios,
       sum(f.monto_total) AS ingreso_valorizado,
       round(100.0 * sum(f.monto_total) / sum(sum(f.monto_total)) OVER (), 1) AS participacion_pct
FROM datamart.fact_servicio f
JOIN datamart.dim_cliente c ON c.sk_cliente = f.sk_cliente
GROUP BY c.razon_social
ORDER BY ingreso_valorizado DESC;

-- KPI 2. Tasa de cumplimiento del servicio por cliente y por ruta
SELECT c.razon_social AS cliente,
       r.nombre_ruta  AS ruta,
       count(*)                 AS servicios_cerrados,
       sum(f.servicio_cumplido) AS servicios_completados,
       round(100.0 * sum(f.servicio_cumplido) / count(*), 1) AS cumplimiento_pct
FROM datamart.fact_servicio f
JOIN datamart.dim_cliente c ON c.sk_cliente = f.sk_cliente
JOIN datamart.dim_ruta r    ON r.sk_ruta = f.sk_ruta
GROUP BY c.razon_social, r.nombre_ruta
ORDER BY cumplimiento_pct, servicios_cerrados DESC;

-- KPI 2 (resumen). Tasa de cumplimiento por ruta
SELECT r.nombre_ruta AS ruta,
       count(*)                 AS servicios_cerrados,
       sum(f.servicio_cumplido) AS servicios_completados,
       round(100.0 * sum(f.servicio_cumplido) / count(*), 1) AS cumplimiento_pct
FROM datamart.fact_servicio f
JOIN datamart.dim_ruta r ON r.sk_ruta = f.sk_ruta
GROUP BY r.nombre_ruta
ORDER BY cumplimiento_pct;

-- KPI 3. Productividad de la flota por conductor
SELECT co.nombre_completo AS conductor,
       count(*)             AS servicios,
       sum(f.km_recorridos) AS km_recorridos,
       sum(f.horas_programadas) AS horas,
       round(100.0 * sum(f.km_adicionales) / NULLIF(sum(f.km_recorridos), 0), 1) AS km_adicionales_pct
FROM datamart.fact_servicio f
JOIN datamart.dim_conductor co ON co.sk_conductor = f.sk_conductor
GROUP BY co.nombre_completo
ORDER BY servicios DESC;

-- KPI 3. Productividad de la flota por vehículo
SELECT v.placa,
       v.tipo_unidad,
       count(*)             AS servicios,
       sum(f.km_recorridos) AS km_recorridos,
       sum(f.monto_total)   AS ingreso_valorizado,
       sum(f.gasto_total)   AS gasto,
       round(100.0 * sum(f.km_adicionales) / NULLIF(sum(f.km_recorridos), 0), 1) AS km_adicionales_pct
FROM datamart.fact_servicio f
JOIN datamart.dim_vehiculo v ON v.sk_vehiculo = f.sk_vehiculo
GROUP BY v.placa, v.tipo_unidad
ORDER BY servicios DESC;
