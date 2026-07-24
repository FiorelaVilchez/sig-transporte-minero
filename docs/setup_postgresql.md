# Guía: Configuración de PostgreSQL para el SIG Transporte Minero

> **Sistema:** SIG — Gestión y Asignación de Recursos en Transporte Minero  
> **Fase:** 11 — Migración a PostgreSQL (RNF-04: Escalabilidad)  
> **Autores:** Proyecto académico — Universidad Nacional del Altiplano  

---

## ¿Por qué PostgreSQL?

El documento del proyecto define en la sección 4.2 una arquitectura de dos motores:  
- **SQLite** → desarrollo local rápido, sin instalación de servidor.  
- **PostgreSQL** → versión final de producción/sustentación, con concurrencia real y mejor soporte de Power BI.  

Ambos conviven en el mismo código: `settings.py` detecta automáticamente cuál usar según la variable `DB_ENGINE` del archivo `.env`.

---

## Parte 1 — Instalar PostgreSQL

Elige la opción que te resulte más cómoda:

### Opción A — Instalador oficial (recomendada para usuarios de escritorio)

| SO | Enlace |
|----|--------|
| **Windows** | <https://www.postgresql.org/download/windows/> — instalador gráfico de EnterpriseDB |
| **macOS** | <https://www.postgresql.org/download/macosx/> — o `brew install postgresql@16` con Homebrew |
| **Ubuntu/Debian** | `sudo apt install postgresql postgresql-contrib` |

**Durante el instalador de Windows:**
1. Deja el puerto en **5432** (predeterminado).
2. Pon una contraseña para el superusuario `postgres` — guárdala, la necesitarás.
3. No necesitas instalar Stack Builder al final.

### Opción B — Docker (la más rápida, sin instalador)

Si ya tienes Docker Desktop instalado:

```bash
docker run --name sig_postgres \
  -e POSTGRES_PASSWORD=mi_contraseña_segura \
  -e POSTGRES_DB=sig_transporte_minero \
  -e POSTGRES_USER=postgres \
  -p 5432:5432 \
  -d postgres:16
```

Esto levanta PostgreSQL 16 en el puerto 5432 con la base de datos `sig_transporte_minero` ya creada.  
Para detenerlo: `docker stop sig_postgres`  
Para volver a iniciarlo: `docker start sig_postgres`

---

## Parte 2 — Crear la base de datos y el usuario (solo si usas Opción A)

Si instalaste PostgreSQL con el instalador (no Docker), necesitas crear la base de datos manualmente.

### Vía psql (línea de comandos)

```bash
# Abre la consola psql como superusuario
psql -U postgres

# Dentro de psql, ejecuta:
CREATE DATABASE sig_transporte_minero;
\q
```

El usuario `postgres` ya tiene todos los permisos. Si quieres un usuario específico del proyecto:

```sql
CREATE USER sig_user WITH PASSWORD 'mi_contraseña_segura';
GRANT ALL PRIVILEGES ON DATABASE sig_transporte_minero TO sig_user;
-- En PostgreSQL 15+, también necesitas:
\c sig_transporte_minero
GRANT ALL ON SCHEMA public TO sig_user;
```

### Vía pgAdmin (interfaz gráfica)

1. Abre **pgAdmin 4** (se instala junto con PostgreSQL en Windows).
2. Expande **Servers → PostgreSQL 16 → Databases**.
3. Clic derecho en **Databases** → **Create → Database**.
4. Nombre: `sig_transporte_minero` → **Save**.

---

## Parte 3 — Configurar el .env del proyecto

Abre el archivo `.env` en la raíz del proyecto y ajusta las líneas de base de datos:

```ini
# .env — configuración para PostgreSQL

SECRET_KEY=django-insecure-tu-clave-aqui
DEBUG=True

# Motor de base de datos
DB_ENGINE=postgresql
DB_NAME=sig_transporte_minero
DB_USER=postgres
DB_PASSWORD=mi_contraseña_segura
DB_HOST=localhost
DB_PORT=5432
```

> **Nota:** Si en algún momento quieres volver a SQLite (por ejemplo, para trabajar sin internet), simplemente comenta o elimina la línea `DB_ENGINE=postgresql`. El sistema usará `db.sqlite3` automáticamente.

---

## Parte 4 — Migración de datos SQLite → PostgreSQL

Si ya tienes datos reales en SQLite (conductores, vehículos, asignaciones, etc.) y no quieres perderlos al cambiar de motor, sigue este flujo completo:

### Paso 1 — Hacer el respaldo de SQLite

Asegúrate de que el `.env` **NO tiene** `DB_ENGINE=postgresql` (o que está comentado) para que Django use SQLite:

```bash
# En Windows PowerShell (forzando el motor SQLite temporalmente):
$env:DB_ENGINE='sqlite'
python -c "
import subprocess, sys
result = subprocess.run(
    [sys.executable, 'manage.py', 'dumpdata',
     '--natural-foreign', '--natural-primary',
     '-e', 'contenttypes', '-e', 'auth.Permission',
     '--indent', '2'],
    capture_output=True, text=True, encoding='utf-8'
)
with open('respaldo_datos.json', 'w', encoding='utf-8') as f:
    f.write(result.stdout)
print(f'Registros volcados: {len(__import__(\"json\").loads(result.stdout))}')
"
```

> **¿Por qué este método y no `dumpdata > archivo.json`?**  
> PowerShell en Windows agrega un BOM (Byte Order Mark) cuando usa `>` para redirigir, y Django no puede leer ese BOM. El método con `subprocess` escribe el archivo directamente en UTF-8 sin BOM.

### Paso 2 — Configurar PostgreSQL en el .env

Edita el `.env` para activar PostgreSQL según la Parte 3 de esta guía.

### Paso 3 — Crear el esquema vacío en PostgreSQL

```bash
python manage.py migrate
```

Esto aplica todas las migraciones del proyecto en la base PostgreSQL (crea las tablas vacías).

### Paso 4 — Cargar los datos en PostgreSQL

```bash
python manage.py loaddata respaldo_datos.json
```

Si la carga es exitosa verás: `Installed 74 object(s) from 1 fixture(s)` (el número puede variar según los datos que tengas).

### Paso 5 — Verificar la migración

```bash
python manage.py check          # No debe mostrar errores
python manage.py runserver      # Levanta el servidor
```

Luego abre el navegador en:
- **http://127.0.0.1:8000/admin/** → verifica conductores, vehículos, documentos.
- **http://127.0.0.1:8000/** → prueba login con `admin_operaciones` / `admin123`.
- Navega a Asignación Automática, Alertas, Dashboard — todo debe funcionar igual que con SQLite.

### Notas sobre integridad referencial

El proyecto usa `on_delete=PROTECT` en varias relaciones (Fase 2). El orden de carga del `loaddata` está garantizado por Django: primero carga los modelos sin dependencias (Conductor, Vehiculo) y luego los que dependen de ellos (DocumentoConductor, Asignacion, etc.). No es necesario ajustar el orden manualmente.

---

## Parte 5 — Volver a SQLite en cualquier momento

Si necesitas trabajar localmente sin PostgreSQL:

```ini
# .env — descomentar o eliminar DB_ENGINE para volver a SQLite
# DB_ENGINE=postgresql
# DB_NAME=...
```

El proyecto usará `db.sqlite3` automáticamente. Los datos que tengas en SQLite no se ven afectados.

---

## Resumen de verificación

Después de completar la migración, confirma:

| Verificación | Resultado esperado |
|---|---|
| `python manage.py check` | `System check identified no issues (0 silenced)` |
| `python manage.py test assignments` | `12 tests OK` |
| Login en `/` con `admin_operaciones` | Acceso correcto al dashboard |
| Conductores en `/admin/` | Mismo número que en SQLite |
| Asignación automática funciona | Sin errores en pantalla |
| Dashboard con KPIs | Valores idénticos a SQLite |

---

*Documento generado en la Fase 11 del proyecto SIG Transporte Minero — Universidad Nacional del Altiplano, 2026.*
