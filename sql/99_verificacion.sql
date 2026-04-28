-- =============================================================================
-- 99_verificacion.sql
-- Consultas de verificación post-DDL
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- =============================================================================

-- 1. Conteo total de tablas en schema public (esperado: 29)
\echo '=== 1. CONTEO DE TABLAS (esperado: 29) ==='
SELECT count(*) AS total_tablas
  FROM information_schema.tables
 WHERE table_schema = 'public'
   AND table_type = 'BASE TABLE';

-- 2. Listado de todas las tablas
\echo ''
\echo '=== 2. LISTADO DE TABLAS ==='
SELECT tablename
  FROM pg_tables
 WHERE schemaname = 'public'
 ORDER BY tablename;

-- 3. Conteo de índices creados con prefijo idx_ (esperado: 37)
\echo ''
\echo '=== 3. CONTEO DE ÍNDICES idx_* (esperado: 37) ==='
SELECT count(*) AS total_indices
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND indexname LIKE 'idx_%';

-- 4. Listado de índices
\echo ''
\echo '=== 4. LISTADO DE ÍNDICES ==='
SELECT tablename, indexname, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND indexname LIKE 'idx_%'
 ORDER BY tablename, indexname;

-- 5. Columnas de geometría registradas (esperado: 7 filas, todas SRID 4326)
\echo ''
\echo '=== 5. GEOMETRY_COLUMNS (esperado: 7 filas, SRID 4326) ==='
SELECT f_table_name, f_geometry_column, srid, type
  FROM geometry_columns
 WHERE f_table_schema = 'public'
 ORDER BY f_table_name;

-- 6. Verificar extensión PostGIS
\echo ''
\echo '=== 6. VERSIÓN POSTGIS ==='
SELECT PostGIS_Full_Version();

-- 7. Verificar constraints CHECK
\echo ''
\echo '=== 7. CONSTRAINTS CHECK ==='
SELECT conname, conrelid::regclass AS tabla, pg_get_constraintdef(oid) AS definicion
  FROM pg_constraint
 WHERE contype = 'c'
   AND connamespace = 'public'::regnamespace
 ORDER BY conrelid::regclass::text, conname;

-- 8. Verificar constraints UNIQUE
\echo ''
\echo '=== 8. CONSTRAINTS UNIQUE ==='
SELECT conname, conrelid::regclass AS tabla, pg_get_constraintdef(oid) AS definicion
  FROM pg_constraint
 WHERE contype = 'u'
   AND connamespace = 'public'::regnamespace
 ORDER BY conrelid::regclass::text, conname;

-- 9. Verificar foreign keys
\echo ''
\echo '=== 9. FOREIGN KEYS (conteo por tabla) ==='
SELECT conrelid::regclass AS tabla, count(*) AS num_fks
  FROM pg_constraint
 WHERE contype = 'f'
   AND connamespace = 'public'::regnamespace
 GROUP BY conrelid::regclass
 ORDER BY conrelid::regclass::text;

-- =============================================================================
\echo ''
\echo '=== VERIFICACIÓN COMPLETADA ==='
-- =============================================================================
