-- Data Mart del servicio de transporte (esquema en estrella, metodología Kimball).
-- Extrae de las tablas del SIG, limpia los datos y carga el esquema datamart.
-- Se puede ejecutar varias veces: cada carga reconstruye las tablas.

BEGIN;

CREATE SCHEMA IF NOT EXISTS datamart;

DROP TABLE IF EXISTS datamart.fact_servicio;
DROP TABLE IF EXISTS datamart.dim_tiempo;
DROP TABLE IF EXISTS datamart.dim_cliente;
DROP TABLE IF EXISTS datamart.dim_conductor;
DROP TABLE IF EXISTS datamart.dim_vehiculo;
DROP TABLE IF EXISTS datamart.dim_ruta;

-- 1. Dimensiones

CREATE TABLE datamart.dim_tiempo (
    sk_tiempo       integer PRIMARY KEY,          -- AAAAMMDD
    fecha           date NOT NULL UNIQUE,
    dia             smallint NOT NULL,
    nombre_dia      varchar(10) NOT NULL,
    semana          smallint NOT NULL,
    mes             smallint NOT NULL,
    nombre_mes      varchar(10) NOT NULL,
    trimestre       smallint NOT NULL,
    anio            smallint NOT NULL,
    fin_de_semana   boolean NOT NULL
);

CREATE TABLE datamart.dim_cliente (
    sk_cliente      integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente      bigint NOT NULL UNIQUE,
    razon_social    varchar(150) NOT NULL,
    ruc             varchar(11) NOT NULL,
    estado          varchar(10) NOT NULL
);

CREATE TABLE datamart.dim_conductor (
    sk_conductor        integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_conductor        bigint NOT NULL UNIQUE,
    nombre_completo     varchar(210) NOT NULL,
    dni                 varchar(8) NOT NULL,
    categoria_licencia  varchar(10) NOT NULL,
    anios_experiencia   smallint NOT NULL,
    estado              varchar(20) NOT NULL
);

CREATE TABLE datamart.dim_vehiculo (
    sk_vehiculo     integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_vehiculo     bigint NOT NULL UNIQUE,
    placa           varchar(15) NOT NULL,
    tipo_unidad     varchar(50) NOT NULL,
    capacidad       smallint NOT NULL,
    estado          varchar(20) NOT NULL
);

CREATE TABLE datamart.dim_ruta (
    sk_ruta         integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    origen          varchar(200) NOT NULL,
    destino         varchar(200) NOT NULL,
    nombre_ruta     varchar(410) NOT NULL,
    km_referencia   integer NOT NULL,
    UNIQUE (origen, destino)
);

-- 2. Extracción y limpieza: un registro por servicio cerrado (granularidad de la tabla de hechos)

DROP TABLE IF EXISTS stg_servicio;
CREATE TEMP TABLE stg_servicio ON COMMIT DROP AS
SELECT
    a.assignment_id,
    s.request_id,
    s.fecha_servicio,
    s.cliente_id,
    a.conductor_id,
    a.vehiculo_id,
    initcap(trim(regexp_replace(s.origen, '\s+', ' ', 'g')))           AS origen,
    trim(regexp_replace(s.destino, '\s+', ' ', 'g'))                  AS destino,
    s.km_estimados,
    a.estado_operativo::text                                           AS estado_servicio,
    COALESCE(s.pasajeros, 0)                                           AS pasajeros,
    COALESCE(s.duracion_horas, 0)                                      AS horas_programadas,
    CASE WHEN a.km_final >= a.km_inicial THEN a.km_final - a.km_inicial ELSE 0 END AS km_recorridos
FROM assignments_asignacion a
JOIN service_requests_solicitudservicio s ON s.request_id = a.solicitud_id
WHERE a.estado_operativo IN ('Completado', 'Con incidencia')
  AND a.conductor_id IS NOT NULL
  AND a.vehiculo_id IS NOT NULL;

-- 3. Carga de dimensiones

INSERT INTO datamart.dim_tiempo
SELECT
    to_char(d, 'YYYYMMDD')::integer,
    d::date,
    extract(day FROM d),
    (ARRAY['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo'])[extract(isodow FROM d)],
    extract(week FROM d),
    extract(month FROM d),
    (ARRAY['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto',
           'Septiembre','Octubre','Noviembre','Diciembre'])[extract(month FROM d)],
    extract(quarter FROM d),
    extract(year FROM d),
    extract(isodow FROM d) IN (6, 7)
FROM generate_series(
    (SELECT date_trunc('month', min(fecha_servicio)) FROM stg_servicio),
    (SELECT date_trunc('month', max(fecha_servicio)) + interval '1 month - 1 day' FROM stg_servicio),
    interval '1 day'
) AS d;

INSERT INTO datamart.dim_cliente (id_cliente, razon_social, ruc, estado)
SELECT id, trim(razon_social), COALESCE(NULLIF(trim(ruc), ''), 'Sin RUC'),
       CASE WHEN activo THEN 'Activo' ELSE 'Inactivo' END
FROM crm_cliente
WHERE id IN (SELECT cliente_id FROM stg_servicio);

INSERT INTO datamart.dim_conductor (id_conductor, nombre_completo, dni, categoria_licencia, anios_experiencia, estado)
SELECT driver_id,
       trim(apellidos) || ', ' || trim(nombres),
       dni,
       COALESCE(NULLIF(categoria_licencia, ''), 'Sin dato'),
       COALESCE(extract(year FROM age(current_date, fecha_obtencion_licencia)), 0),
       estado
FROM drivers_conductor
WHERE driver_id IN (SELECT conductor_id FROM stg_servicio);

INSERT INTO datamart.dim_vehiculo (id_vehiculo, placa, tipo_unidad, capacidad, estado)
SELECT truck_id, upper(trim(placa)), tipo, capacidad, estado
FROM trucks_vehiculo
WHERE truck_id IN (SELECT vehiculo_id FROM stg_servicio);

INSERT INTO datamart.dim_ruta (origen, destino, nombre_ruta, km_referencia)
SELECT origen, destino, origen || ' - ' || destino, max(km_estimados)
FROM stg_servicio
GROUP BY origen, destino;

-- 4. Tabla de hechos

CREATE TABLE datamart.fact_servicio (
    id_asignacion       bigint PRIMARY KEY,       -- dimensión degenerada: N.° de servicio en el SIG
    sk_tiempo           integer NOT NULL REFERENCES datamart.dim_tiempo (sk_tiempo),
    sk_cliente          integer NOT NULL REFERENCES datamart.dim_cliente (sk_cliente),
    sk_conductor        integer NOT NULL REFERENCES datamart.dim_conductor (sk_conductor),
    sk_vehiculo         integer NOT NULL REFERENCES datamart.dim_vehiculo (sk_vehiculo),
    sk_ruta             integer NOT NULL REFERENCES datamart.dim_ruta (sk_ruta),
    estado_servicio     varchar(20) NOT NULL,
    servicio_cumplido   smallint NOT NULL CHECK (servicio_cumplido IN (0, 1)),
    pasajeros           integer NOT NULL,
    horas_programadas   integer NOT NULL,
    km_recorridos       integer NOT NULL,
    km_adicionales      integer NOT NULL,
    monto_base          numeric(10,2) NOT NULL,
    monto_adicional     numeric(10,2) NOT NULL,
    monto_total         numeric(10,2) NOT NULL,
    gasto_total         numeric(10,2) NOT NULL,
    num_incidencias     integer NOT NULL
);

INSERT INTO datamart.fact_servicio
SELECT
    st.assignment_id,
    t.sk_tiempo,
    c.sk_cliente,
    co.sk_conductor,
    v.sk_vehiculo,
    r.sk_ruta,
    st.estado_servicio,
    CASE WHEN st.estado_servicio = 'Completado' THEN 1 ELSE 0 END,
    st.pasajeros,
    st.horas_programadas,
    st.km_recorridos,
    COALESCE(val.km_adicionales, 0),
    COALESCE(val.monto_base, 0),
    COALESCE(val.monto_adicional, 0),
    COALESCE(val.total, 0),
    COALESCE(g.gasto, 0),
    COALESCE(i.incidencias, 0)
FROM stg_servicio st
JOIN datamart.dim_tiempo t     ON t.fecha = st.fecha_servicio
JOIN datamart.dim_cliente c    ON c.id_cliente = st.cliente_id
JOIN datamart.dim_conductor co ON co.id_conductor = st.conductor_id
JOIN datamart.dim_vehiculo v   ON v.id_vehiculo = st.vehiculo_id
JOIN datamart.dim_ruta r       ON r.origen = st.origen AND r.destino = st.destino
-- la valorización pertenece a la solicitud y se asigna solo al servicio que la completó
LEFT JOIN billing_valorizacion val
       ON val.solicitud_id = st.request_id AND st.estado_servicio = 'Completado'
LEFT JOIN (SELECT asignacion_id, sum(monto) AS gasto FROM assignments_gastoservicio GROUP BY asignacion_id) g
       ON g.asignacion_id = st.assignment_id
LEFT JOIN (SELECT asignacion_id, count(*) AS incidencias FROM assignments_incidencia GROUP BY asignacion_id) i
       ON i.asignacion_id = st.assignment_id;

CREATE INDEX ON datamart.fact_servicio (sk_tiempo);
CREATE INDEX ON datamart.fact_servicio (sk_cliente);
CREATE INDEX ON datamart.fact_servicio (sk_conductor);
CREATE INDEX ON datamart.fact_servicio (sk_vehiculo);
CREATE INDEX ON datamart.fact_servicio (sk_ruta);

COMMIT;
