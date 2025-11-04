
# Migraciones y cómo aplicarlas

Este proyecto usa Alembic para gestionar cambios en el esquema. Este documento describe el propósito de cada migración, el orden de ejecución, comandos para aplicar/revertir, y consideraciones de datos.

IMPORTANTE: muchas migraciones usan SQL condicional específico de PostgreSQL (bloques DO $$ ... $$). Asegúrate de ejecutar las migraciones contra una base Postgres o adapta los bloques SQL.

Requisitos previos
- Docker (opcional): `docker-compose.yml` contiene un servicio `db` con credenciales usadas en `database.py`.
- Variable de entorno (opcional): `DATABASE_URL` si prefieres no importar `database.py` desde `env.py`.

Arrancar la base de datos (PowerShell):
```powershell
docker-compose -f "${PWD}\docker-compose.yml" up -d
docker logs veterinaria_container --tail 100
```

Comprobar conexión y contexto Alembic
```powershell
$env:DATABASE_URL = "postgresql://postgres:amigo123@localhost:5432/veterinaria_db"
alembic current
alembic history --verbose
```

Orden recomendado de migraciones (ya presentes en `alembic/versions`)
1. d8f3a1c9b4e2 — Crear `medical_records` y poblar desde citas completadas (Migración 1)
2. e1a2b3c4d5f6 — Crear `vaccines` y `vaccination_records` (Migración 2)
3. f7c6d8a9b0e1 — Modificar `pets` y `owners` (Migración 3)
4. a9b8c7d6e5f4 — Crear `invoices` y generar facturas retroactivas (Migración 4)
5. b1c2d3e4f5a6 — Añadir métricas a `veterinarians` y `pets` (Migración 5)

Cómo aplicar y revertir migraciones
- Aplicar todas hasta la última:
```powershell
alembic upgrade head
```
- Aplicar hasta una migración específica (por ejemplo Migración 3):
```powershell
alembic upgrade f7c6d8a9b0e1
```
- Revertir la última migración:
```powershell
alembic downgrade -1
```
- Revertir a una revisión específica (ej. retroceder a Migración 2):
```powershell
alembic downgrade e1a2b3c4d5f6
```

Resumen por migración

1) Migración 1 — `d8f3a1c9b4e2` — medical_records
- Propósito: Añadir tabla `medical_records` y poblarla con datos históricos de `appointments` con `status='completed'`.
- Consideraciones de datos: mapa razonable usado: `reason -> diagnosis`, `notes -> treatment`, `appointment_date -> created_at`.
- Backup/rollback: `downgrade()` crea `backup_{revision}_medical_records` antes de dropear la columna/tabla.

2) Migración 2 — `e1a2b3c4d5f6` — vacunas
- Propósito: Añadir `vaccines` (catálogo) y `vaccination_records` (registro de aplicaciones).
- Consideraciones: incluye un bloque para migrar desde una tabla legacy `vaccinations` si existe (name-matching), y FKs hacia `pets` y `veterinarians`.
- Backup/rollback: `downgrade()` crea backups `backup_{revision}_vaccination_records` y `backup_{revision}_vaccines`.

3) Migración 3 — `f7c6d8a9b0e1` — pets & owners
- Propósito: Añadir `microchip_number`, `is_neutered`, `blood_type` a `pets`; añadir `emergency_contact` y enum `preferred_payment_method` a `owners`.
- Consideraciones: se crean backups completos antes de alterar tablas. `microchip_number` es UNIQUE but nullable (Postgres allows multiple NULLs). `preferred_payment_method` implemented as Postgres ENUM `payment_method`.
- Backup/rollback: full-table backups and focused backups created by `downgrade()`.

4) Migración 4 — `a9b8c7d6e5f4` — invoices
- Propósito: Añadir `invoices` y generar facturas retroactivas para citas completadas.
- Consideraciones: No existe lógica de pricing en el esquema actual: la migración genera placeholder invoices (subtotal/tax/total = 0.00). Invoice numbers generated as `INV-{appointment_id}-{YYYYMMDD}` (deterministic).
- Backup/rollback: `downgrade()` creates `backup_{revision}_invoices`.

5) Migración 5 — `b1c2d3e4f5a6` — métricas
- Propósito: Añadir `consultation_fee`, `rating`, `total_appointments` a `veterinarians`; `last_visit_date`, `visit_count` a `pets`.
- Consideraciones: `total_appointments`, `visit_count` and `last_visit_date` are populated from `appointments` with `status='completed'`. `consultation_fee`/`rating` cannot be derived and are set to defaults/NULL.
- Backup/rollback: full-table backups created during upgrade and focused backups created during downgrade.

Comandos útiles de verificación (después de migrar)
- Contar citas completadas y facturas generadas:
```sql
SELECT COUNT(*) FROM appointments WHERE status='completed';
SELECT COUNT(*) FROM invoices;
```
- Verificar duplicados que romperían constraints (p. ej. microchip uniqueness):
```sql
SELECT microchip_number, COUNT(*) FROM pets GROUP BY microchip_number HAVING COUNT(*) > 1;
```

ER diagrams
- Un diagrama ER en PlantUML se encuentra en `docs/er_diagram.puml`. Actualiza/regenéralo cada vez que ejecutes migraciones.

Consideraciones generales de datos
- Haz siempre un backup completo (`pg_dump`) antes de ejecutar migraciones contra datos de producción.
- Algunos DROP/CREATE en los `downgrade()` son best-effort y usan excepciones para ser robustos; sin embargo, siempre revisa los backups si planeas revertir.

Notas finales
- Si necesitas que las migraciones conserven backups en vez de borrarlos al final del `upgrade()`, lo puedo cambiar para que sea condicional mediante la variable de entorno `KEEP_MIGRATION_BACKUPS=1`.

---
Ver también: `README.md` para instrucciones de desarrollo y despliegue.


Arrancar la base de datos (desde la raíz del proyecto, PowerShell):
```powershell
docker-compose -f "${PWD}\docker-compose.yml" up -d
docker logs veterinaria_container --tail 100
```

Prechecks recomendados antes de migrar (ver `scripts/check_medical_records_migration.py`):
1. Fijar la variable de entorno para Alembic en la sesión:
```powershell
$env:DATABASE_URL = "postgresql://postgres:amigo123@localhost:5432/veterinaria_db"
```
2. Ejecutar la comprobación:
```powershell
python .\scripts\check_medical_records_migration.py
```
Esta comprobación mostrará el número de citas con `status='completed'` y si existen `appointment_id` duplicados que romperían la UNIQUE contraint.

Aplicar migraciones (PowerShell):
```powershell
# usar la misma sesión donde se definió $env:DATABASE_URL o asegurar que database.py es importable
alembic upgrade head
```

Si ves errores de conexión, revisa que el contenedor de Postgres esté arriba y que `database.SQLALCHEMY_DATABASE_URL` coincida con la URL usada por Alembic.

Rollback y backups
- Las migraciones incluyen lógicas de backup cuando corresponde (p. ej. `medical_records` crea una tabla `backup_{revision}_medical_records` en `downgrade`).
- Aún así, haz siempre un `pg_dump` de la base antes de correr migraciones en producción.

Notas de desarrollo
- Evitar `models.Base.metadata.create_all()` en entornos donde se usen migraciones — en este proyecto está desactivado por defecto; usar `ENABLE_CREATE_ALL=1` sólo para pruebas rápidas y locales.