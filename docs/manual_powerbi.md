# Manual: Dashboard Gerencial en Power BI Desktop

> **Sistema:** SIG — Gestión y Asignación de Recursos en Transporte Minero  
> **Fase:** 10 — Integración con Power BI  
> **Requisito:** Power BI Desktop instalado (descarga gratuita desde [microsoft.com/power-bi](https://powerbi.microsoft.com/es-es/desktop/))

---

## Antes de empezar

Asegúrate de haber generado los archivos CSV ejecutando el siguiente comando desde la raíz del proyecto Django:

```bash
python manage.py exportar_csv_powerbi
```

Esto creará (o actualizará) los 8 archivos en la carpeta `exports/` del proyecto. Anota la ruta completa de esa carpeta — la necesitarás en el Paso 1. Por ejemplo:

```
D:\Fio\sig-transporte-minero\exports\
```

---

## Paso 1 — Abrir Power BI Desktop y cargar los datos

### Opción A: Cargar los 8 archivos uno a uno (recomendada para principiantes)

1. Abre **Power BI Desktop**.
2. En la pantalla de inicio, haz clic en **"Obtener datos"** → **"Texto o CSV"**.
3. Navega a la carpeta `exports/` del proyecto y selecciona `powerbi_asignaciones_completas.csv`. Haz clic en **Abrir**.
4. En la vista previa, verifica que las columnas se muestren correctamente. Haz clic en **"Cargar"** (no en Transformar datos todavía).
5. Repite el proceso para cada uno de los 8 archivos:
   - `driver_documents.csv`
   - `truck_documents.csv`
   - `service_requests.csv`
   - `assignments.csv`
   - `alerts.csv`
   - `powerbi_asignaciones_completas.csv`
   - `powerbi_drivers_con_documentos.csv`
   - `powerbi_trucks_con_documentos.csv`

> **Atajo:** Puedes usar **"Obtener datos" → "Más..." → "Carpeta"**, escribir la ruta de `exports/`, y seleccionar solo los archivos `.csv`. Power BI los combina automáticamente en consultas separadas.

### Opción B: Cargar desde una carpeta (todos a la vez)

1. Haz clic en **"Obtener datos" → "Más..."** → busca **"Carpeta"** → clic en **Conectar**.
2. Escribe o pega la ruta de la carpeta `exports/`, por ejemplo: `D:\Fio\sig-transporte-minero\exports`.
3. Power BI listará los 8 archivos CSV. Haz clic en **"Transformar datos"**.
4. En Power Query, para cada archivo: haz clic en el ícono de tabla a la derecha de `Content` (columna `Binary`) para expandir su contenido.
5. Repite para cada archivo cargado, dando a cada consulta el nombre del archivo correspondiente (sin extensión).

---

## Paso 2 — Transformaciones en Power Query

> En la mayoría de los casos, las columnas ya vienen nombradas correctamente desde la Fase 9. Solo necesitas verificar y ajustar los **tipos de datos**.

Para cada tabla cargada:

1. En el panel izquierdo "Consultas", haz clic en la tabla.
2. Ve a la pestaña **"Transformar"** → **"Detectar tipo de datos"** (o ajusta manualmente).
3. Aplica estos tipos por columna:

### `powerbi_asignaciones_completas`

| Columna | Tipo de dato |
|---|---|
| `assignment_id`, `request_id`, `driver_id`, `truck_id` | Número entero |
| `fecha_servicio`, `fecha_asignacion` | Fecha / Fecha y hora |
| Todas las demás | Texto |

### `driver_documents` y `powerbi_drivers_con_documentos`

| Columna | Tipo de dato |
|---|---|
| `document_id`, `driver_id` | Número entero |
| `fecha_emision`, `fecha_vencimiento` | Fecha |
| Todas las demás | Texto |

### `truck_documents` y `powerbi_trucks_con_documentos`

| Columna | Tipo de dato |
|---|---|
| `document_id`, `truck_id` | Número entero |
| `capacidad` | Número decimal |
| `fecha_emision`, `fecha_vencimiento` | Fecha |
| Todas las demás | Texto |

### `service_requests`

| Columna | Tipo de dato |
|---|---|
| `request_id` | Número entero |
| `fecha_servicio` | Fecha |
| `hora_servicio` | Hora |
| Todas las demás | Texto |

### `alerts`

| Columna | Tipo de dato |
|---|---|
| `alert_id` | Número entero |
| `fecha_generacion` | Fecha y hora |
| Todas las demás | Texto |

4. Cuando hayas ajustado todos los tipos, haz clic en **"Cerrar y aplicar"** (esquina superior izquierda de Power Query).

---

## Paso 3 — Construir los 8 KPIs del Dashboard

Una vez de vuelta en el lienzo principal, sigue los pasos para crear cada visual:

---

### KPI 1 — Total de asignaciones

**Visual:** Tarjeta (Card)  
**Tabla:** `powerbi_asignaciones_completas`  
**Campo:** `assignment_id` → Recuento (Count)

**Pasos:**
1. En el panel "Visualizaciones", haz clic en el ícono de **"Tarjeta"** (Card).
2. Arrastra el campo `assignment_id` de la tabla `powerbi_asignaciones_completas` al campo **"Valores"**.
3. Haz clic en la flecha junto al campo → selecciona **"Recuento"**.
4. En el panel "Formato visual" (ícono de pincel), cambia el título a: **"Total de Asignaciones"**.

---

### KPI 2 — Asignaciones aprobadas

**Visual:** Tarjeta (Card)  
**Filtro:** `estado_asignacion = "Aprobada"`

**Pasos:**
1. Inserta una nueva **Tarjeta**. Arrastra `assignment_id` a Valores → **"Recuento"**.
2. Arrastra el campo `estado_asignacion` al panel **"Filtros en este objeto visual"** (panel Filtros, lado derecho).
3. Selecciona tipo **"Filtrado básico"** y marca solo **"Aprobada"**.
4. Título: **"Asignaciones Aprobadas"**.

---

### KPI 3 — Asignaciones rechazadas

Igual que el KPI 2, pero filtrando `estado_asignacion = "Rechazada"`.  
Título: **"Asignaciones Rechazadas"**.

---

### KPI 4 — Documentos vencidos

**Visual:** Tarjeta (Card)  
**Método:** Medida DAX combinando conductores + vehículos

1. En el panel "Datos" (derecha), haz clic derecho sobre cualquier tabla → **"Nueva medida"**.
2. Escribe esta fórmula y presiona Enter:

```dax
Docs Vencidos =
CALCULATE(COUNTROWS(powerbi_drivers_con_documentos),
    powerbi_drivers_con_documentos[estado_documento] = "Vencido") +
CALCULATE(COUNTROWS(powerbi_trucks_con_documentos),
    powerbi_trucks_con_documentos[estado_documento] = "Vencido")
```

3. Inserta una **Tarjeta** y arrastra la medida `Docs Vencidos` a Valores.
4. Título: **"Documentos Vencidos"**.

---

### KPI 5 — Documentos por vencer

Crea una nueva medida DAX:

```dax
Docs Por Vencer =
CALCULATE(COUNTROWS(powerbi_drivers_con_documentos),
    powerbi_drivers_con_documentos[estado_documento] = "Por vencer") +
CALCULATE(COUNTROWS(powerbi_trucks_con_documentos),
    powerbi_trucks_con_documentos[estado_documento] = "Por vencer")
```

Inserta una **Tarjeta** y arrastra la medida. Título: **"Documentos por Vencer"**.

---

### KPI 6 — Alertas de riesgo alto

**Visual:** Tarjeta (Card)  
**Tabla:** `alerts` | `alert_id` → Recuento  
**Filtros:** `nivel_riesgo = "Alto"` y `estado_alerta = "Activa"`

**Pasos:**
1. Inserta una **Tarjeta**. Arrastra `alert_id` a Valores → **"Recuento"**.
2. En el panel de filtros del visual, arrastra `nivel_riesgo` → marca **"Alto"**.
3. Arrastra `estado_alerta` → marca **"Activa"**.
4. Título: **"Alertas de Riesgo Alto"**.

---

### KPI 7 — Solicitudes por estado

**Visual:** Gráfico de barras agrupadas (horizontal)  
**Tabla:** `service_requests`

**Pasos:**
1. Selecciona el ícono de **"Gráfico de barras agrupadas"** en Visualizaciones.
2. Arrastra `estado_solicitud` al campo **"Eje Y"**.
3. Arrastra `request_id` al campo **"Valores"** → selecciona **"Recuento"**.
4. Título: **"Solicitudes por Estado"**.
5. Opcional: en Formato → Colores de datos, asigna colores distintos a cada estado (verde para Completada, rojo para Cancelada, etc.).

> **Alternativa:** Puedes usar un **Gráfico circular (Pie chart)**: `estado_solicitud` en "Leyenda" y `request_id` (Count) en "Valores".

---

### KPI 8a — Asignaciones por conductor

**Visual:** Gráfico de barras horizontales  
**Tabla:** `powerbi_asignaciones_completas`

**Pasos:**
1. Selecciona **"Gráfico de barras agrupadas"** (horizontal).
2. Arrastra `conductor_nombre` al **"Eje Y"**.
3. Arrastra `assignment_id` a **"Valores"** → **"Recuento"**.
4. En Formato → Eje Y → activa **"Ordenar datos"** → elige "Valores" de mayor a menor.
5. Título: **"Asignaciones por Conductor"**.

---

### KPI 8b — Asignaciones por vehículo

Igual que 8a pero arrastrando `placa` al Eje Y en lugar de `conductor_nombre`.  
Título: **"Asignaciones por Vehículo (Placa)"**.

---

## Paso 4 — Organizar el lienzo

1. Ve a la pestaña **"Insertar"** → **"Cuadro de texto"**.
2. Escribe: `Dashboard Gerencial — Transporte Minero`. Aplica fuente grande (28-36pt), negrita.
3. **Distribución sugerida del lienzo:**

```
┌─────────────────────────────────────────────────────────────────────┐
│          Dashboard Gerencial — Transporte Minero                    │
├──────────┬──────────┬──────────┬──────────┬──────────┬─────────────┤
│  Total   │ Aprob.   │ Rechoz.  │ Docs     │ Docs por │ Alertas     │
│ Asignac. │ Asignac. │ Asignac. │ Vencidos │ Vencer   │ Riesgo Alto │
│ [Card]   │ [Card]   │ [Card]   │ [Card]   │ [Card]   │ [Card]      │
├────────────────────────────────┬────────────────────────────────────┤
│   Solicitudes por Estado       │  Asignaciones por Conductor        │
│   [Barras / Circular]          │  [Barras horizontal]               │
├────────────────────────────────┴────────────────────────────────────┤
│                Asignaciones por Vehículo (Placa)                    │
│                [Barras horizontal]                                  │
└─────────────────────────────────────────────────────────────────────┘
```

4. Para mover un visual: haz clic y arrástralo. Para redimensionar: arrastra desde las esquinas.
5. Para alinear: selecciona varios visuals con Ctrl+clic → pestaña **"Formato"** → **"Alinear"**.

---

## Paso 5 — Guardar el archivo .pbix

**Archivo → Guardar como** → nombra el archivo `dashboard_transporte_minero.pbix`.

> Guarda con frecuencia mientras trabajas con Ctrl+S.

---

## Paso 6 — Exportar a PDF

1. Ve a **Archivo → Exportar → Exportar a PDF**.
2. Power BI generará un PDF con cada página del informe.
3. Guarda el archivo como: `dashboard_transporte_minero.pdf`.

> **Alternativa: capturas de pantalla individuales**
>
> Si prefieres imágenes separadas en lugar de un PDF completo:
> - Usa `Win + Shift + S` (Windows) para abrir la herramienta de recorte y capturar el área exacta de cada visual.
> - Guarda cada captura con nombres descriptivos: `kpi_total_asignaciones.png`, `grafico_solicitudes_estado.png`, etc.
>
> El sistema SIG acepta ambos formatos: un único PDF o varias imágenes individuales.

---

## Paso 7 — Subir el resultado al sistema SIG

Una vez exportado el PDF o las capturas:

1. Ingresa al sistema SIG con tu usuario (rol Administrador de operaciones o Gerencia).
2. En el menú lateral, haz clic en **"Reportes Gerenciales"**.
3. En la sección **"Subir nuevo reporte"**, completa:
   - **Descripción:** ej. `Dashboard gerencial - Fase 10`
   - **Reporte PDF:** adjunta el archivo `.pdf` exportado (opcional si prefieres usar capturas).
   - **Capturas de pantalla:** adjunta las imágenes PNG/JPG capturadas (opcional si usas PDF).
4. Haz clic en **"Subir reporte"**.
5. El reporte aparecerá de inmediato en la sección de visualización con el PDF embebido o las imágenes en galería.

---

## Nota: Integración futura con PostgreSQL (Fase 11)

En la versión actual del prototipo, Power BI lee los datos desde los 8 archivos CSV estáticos de la carpeta `exports/`. Esto es suficiente para la etapa de demostración académica.

En una versión posterior del proyecto **(Fase 11)**, al migrar la base de datos de SQLite a **PostgreSQL**, Power BI podrá conectarse directamente sin necesidad de CSV intermedios:

1. En Power BI Desktop: **Obtener datos → Base de datos → Base de datos de PostgreSQL**.
2. Servidor: dirección del servidor (ej. `localhost:5432`).
3. Base de datos: nombre de la base de datos del proyecto.
4. Power BI realizará consultas SQL directas, con datos siempre actualizados sin pasos manuales adicionales.

---

*Manual generado como parte del SIG — Gestión y Asignación de Recursos en Transporte Minero (Fase 10).*
