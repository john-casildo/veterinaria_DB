# Veterinary Clinic Management — Project README

This repository contains a small FastAPI application and Alembic migrations for a veterinary clinic management system. The project includes models for veterinarians, owners, pets, appointments and several feature migrations (medical records, vaccination, invoices, metrics).

Quick start (development)
1. Create and activate a Python virtual environment. On Windows (PowerShell):
```powershell
python -m venv .env
& .\.env\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Start the database (recommended via Docker Compose):
```powershell
docker-compose -f "${PWD}\docker-compose.yml" up -d
```

3. Configure DB connection for Alembic (one of the following):
- Set env var for the session:
```powershell
$env:DATABASE_URL = "postgresql://postgres:amigo123@localhost:5432/veterinaria_db"
```
- or ensure `database.py` exposes `SQLALCHEMY_DATABASE_URL` and is importable by Alembic's `env.py`.

4. Apply migrations:
```powershell
alembic upgrade head
```

5. Run the app (development):
```powershell
uvicorn main:app --reload
```

Project structure (important files)
- `main.py` — FastAPI application and route handlers for core resources (veterinarians, owners, pets, appointments).
- `models.py` — SQLAlchemy ORM models used by the app.
- `alembic/versions/` — Alembic migration scripts (several migrations added for features).
- `MIGRATIONS.md` — Detailed guidance about each migration, ordering, and data considerations.
- `docs/er_diagram.puml` — PlantUML ER diagram for the schema after current migrations.

Applying and reverting migrations
- Apply all migrations: `alembic upgrade head`
- Revert last migration: `alembic downgrade -1`
- Revert to specific revision: `alembic downgrade <revision>`

Backups and data safety
- Always run a full DB backup before applying migrations on production: `pg_dump` or other backup strategy.
- Many migrations create backup tables during `downgrade()` (and some create backups during `upgrade()` then drop them). Review the specific migration files in `alembic/versions` for exact behavior.

ER Diagram
- The file `docs/er_diagram.puml` contains a PlantUML diagram you can render with PlantUML to produce a PNG/SVG.

Development notes
- `main.py` intentionally contains placeholders (501 responses) for resources that depend on later migrations (medical records, vaccines, invoices). Implement the API endpoints only after applying the relevant migrations in your dev DB.

Contact
- If you need help applying the migrations or implementing endpoints, tell me which endpoint(s) or migration(s) to prioritize and I will implement them.
# Veterinaria - API y conjunto de utilidades

Este repositorio contiene una API REST para gestionar una clínica veterinaria (veterinarios, dueños, mascotas, citas) y utilidades relacionadas: migraciones (Alembic), scripts de *seed* para poblar datos de ejemplo y un `docker-compose.yml` para levantar una base PostgreSQL local.

El proyecto está escrito con FastAPI y SQLAlchemy.

## Resumen rápido
- Framework API: FastAPI (`main.py` expone `app`)
- ORM: SQLAlchemy
- Migraciones: Alembic (carpeta `alembic/` y `alembic.ini`)
- Base de datos: PostgreSQL (detalle en `database.py` y `docker-compose.yml`)
- Seeds: `seed.py`, `seed_initial.py`, `seed_after_migration.py` (scripts para poblar datos)

---

## Requisitos
- Python 3.10+ (recomendado)
- PostgreSQL (se puede usar el contenedor en `docker-compose.yml`)
- `pip` y `virtualenv` (o venv integrado)

Dependencias principales (ver `requirements.txt`):
- fastapi
- uvicorn
- SQLAlchemy==1.4.49
- psycopg2-binary
- pydantic (v2)
- python-dotenv
- alembic
- pytest

---

## Estructura principal de archivos
- `main.py` - punto de entrada de la API (FastAPI)
- `database.py` - configuración de SQLAlchemy (URL por defecto en el archivo)
- `models.py` - definiciones de modelos/entidades
- `schemas.py` - Pydantic schemas
- `alembic/` - migraciones
- `seed.py` - helpers `get_or_create_*` y `seed()`
- `seed_initial.py` - script para poblar dataset inicial (usa `--yes` para forzar)
- `seed_after_migration.py` - seeds que deben correrse después de migraciones (si aplica)
- `docker-compose.yml` - servicio `db` (Postgres) usado para desarrollo

---

## Configuración de la base de datos
Por defecto la cadena de conexión está definida en `database.py`:

```
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:amigo123@localhost:5432/veterinaria_db"
```

Opciones:
- Para desarrollo rápido, usa `docker-compose` (ver la sección siguiente).
- Para producción o entornos locales, cambia la URL en `database.py` o adapta el fichero para leer `DATABASE_URL` desde variables de entorno (recomendado). El proyecto ya incluye `python-dotenv` en `requirements.txt` para cargar variables desde un `.env` si decides integrar esa funcionalidad.

---

## Levantar la base de datos con Docker (desarrollo)
Este proyecto incluye `docker-compose.yml` con el servicio `db`:

- Usuario: `postgres`
- Password: `amigo123`
- Base de datos: `veterinaria_db`
- Puerto mapeado: `5432:5432`

Comandos (PowerShell):

```powershell
# Levantar DB en segundo plano
docker-compose up -d

# Ver logs del contenedor
docker-compose logs -f db

# Parar y eliminar contenedores
docker-compose down
```

Nota: la URL por defecto en `database.py` coincide con los valores de `docker-compose.yml`.

---

## Instalar dependencias y activar entorno virtual
PowerShell (Windows):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

Linux / macOS (ejemplo):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Migraciones (Alembic)
Alembic ya está presente (`alembic/` y `alembic.ini`). Pautas comunes:

```powershell
# Generar nueva migración (autogenerate)
alembic revision --autogenerate -m "mensaje"

# Aplicar migraciones a la última versión
alembic upgrade head

# Revertir a una revisión anterior
alembic downgrade -1
```

Asegúrate de que `SQLALCHEMY_DATABASE_URL` en `database.py` apunta a la base de datos correcta antes de ejecutar migraciones.

---

## Ejecutar la API (modo desarrollo)
`main.py` expone una aplicación FastAPI llamada `app`. Usa `uvicorn` para arrancar:

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- La documentación interactiva estará en `http://127.0.0.1:8000/docs` (Swagger UI).
- También puedes abrir `http://127.0.0.1:8000/redoc` para ReDoc.

---

## Seeds / Poblar datos de ejemplo
Hay varios scripts para poblar datos:

- `seed.py` - helpers y un `seed()` general que crea un conjunto moderado de datos.
- `seed_initial.py` - genera dataset inicial más grande (10 veterinarios, 20 dueños, 30 mascotas, 50 citas). Incluye preflight que chequea si ya hay datos.
- `seed_after_migration.py` - (si existe) para datos dependientes de migraciones posteriores.

Uso de `seed_initial.py` (PowerShell):

```powershell
# visualiza counts y aborta si ya hay datos
python seed_initial.py

# forzar ejecución incluso si hay datos (usa helpers get_or_create para evitar duplicados exactos)
python seed_initial.py --yes
```

Uso de `seed.py` (simple):

```powershell
python seed.py
```

Los helpers en `seed.py` (`get_or_create_vet`, `get_or_create_owner`, `get_or_create_pet`, `get_or_create_appointment`) intentan evitar duplicados usando claves razonables (email, license_number, owner+name+birth_date, etc.).

---

## Tests
Se usa `pytest` (ver `requirements.txt`). Para ejecutar las pruebas:

```powershell
pytest -q
```

Nota: las pruebas pueden requerir configurar una base de datos de pruebas; revisa o crea fixtures para aislar la DB real.

---

## Buenas prácticas y notas para desarrolladores
- Considera mover la URL de conexión a variables de entorno (`DATABASE_URL`) y cargar con `python-dotenv` para no commitear credenciales.
- SQLAlchemy está fijado a `1.4.49`. Actualizar a SQLAlchemy 2.x requiere revisar patrones de uso del ORM.
- Alembic y las migraciones deben ejecutarse antes de correr seeds que dependen de cambios de esquema.
- Los endpoints de `main.py` devuelven errores 501 en recursos que requieren migraciones adicionales (registros médicos, vacunas, facturas, reportes) — revisar las migraciones enumeradas en `alembic/versions/`.

---

## Comandos útiles resumen (PowerShell)
```powershell
# Levantar DB
docker-compose up -d

# Instalar dependencias
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Aplicar migraciones
alembic upgrade head

# Correr server
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Ejecutar seed inicial (ver preflight)
python seed_initial.py --yes

# Ejecutar tests
pytest -q
```

---

## Estructura de migraciones y notas históricas
La carpeta `alembic/versions/` ya contiene migraciones numeradas (por ejemplo `0001_add_medical_records.py`, `0002_add_vaccination_system.py`, etc.). Lee los comentarios de cada migración si necesitas entender por qué algunas rutas en `main.py` retornan 501 (pendientes de migración).

---

## Contacto / Siguientes pasos
- Para problemas al iniciar la DB con Docker: revisa `docker-compose logs db` y asegúrate de que el puerto 5432 no esté ocupado.
- Si quieres que convierta la configuración para admitir `DATABASE_URL` desde `.env` o que añada GitHub Actions para tests automáticos, dime y lo implemento.

---

README generado automáticamente por asistente; adapta detalles sensibles (credenciales) antes de usar en producción.
