-- =============================================================================
-- 99_verificacion.sql
-- Consultas de verificación post-DDL
-- Proyecto: Feminicidio Bogotá — Base de Datos Espacial
-- =============================================================================

-- 1. Conteo total de tablas en schema public (esperado: 30, sin contar spatial_ref_sys)
\echo '=== 1. CONTEO DE TABLAS (esperado: 30) ==='
SELECT count(*) AS total_tablas
  FROM information_schema.tables
 WHERE table_schema = 'public'
   AND table_type = 'BASE TABLE'
   AND table_name <> 'spatial_ref_sys';

-- 2. Listado de todas las tablas
\echo ''
\echo '=== 2. LISTADO DE TABLAS ==='
SELECT tablename
  FROM pg_tables
 WHERE schemaname = 'public'
 ORDER BY tablename;

-- 3. Conteo de índices (esperado: 45 idx_*, 79 en total, 7 GiST)
\echo ''
\echo '=== 3. CONTEO DE ÍNDICES (esperado: idx=45, total=79, gist=7) ==='
SELECT count(*) FILTER (WHERE indexname LIKE 'idx_%')      AS idx,
       count(*)                                           AS total,
       count(*) FILTER (WHERE indexdef ILIKE '%USING gist%') AS gist
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND tablename <> 'spatial_ref_sys';

-- 4. Listado de índices
\echo ''
\echo '=== 4. LISTADO DE ÍNDICES ==='
SELECT tablename, indexname, indexdef
  FROM pg_indexes
 WHERE schemaname = 'public'
   AND indexname LIKE 'idx_%'
 ORDER BY tablename, indexname;

-- 5. Columnas de geometría (esperado: 7 filas, SRID 4326; zona/localidad/upl MULTIPOLYGON)
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

-- 10. Reglas ON DELETE (esperado: RESTRICT=22, CASCADE=14, SET NULL=1)
\echo ''
\echo '=== 10. REGLAS ON DELETE (esperado: RESTRICT 22, CASCADE 14, SET NULL 1) ==='
SELECT CASE confdeltype WHEN 'r' THEN 'RESTRICT' WHEN 'c' THEN 'CASCADE'
                        WHEN 'n' THEN 'SET NULL' WHEN 'a' THEN 'NO ACTION'
                        ELSE confdeltype::text END AS on_delete,
       count(*) AS fks
  FROM pg_constraint
 WHERE contype = 'f'
   AND connamespace = 'public'::regnamespace
 GROUP BY 1
 ORDER BY 1;

-- 11. Catálogo de estratos sin duplicados (esperado: 6)
\echo ''
\echo '=== 11. ESTRATOS (esperado: 6) ==='
SELECT count(*) AS estratos FROM estrato;

-- =============================================================================
\echo ''
\echo '=== VERIFICACIÓN COMPLETADA ==='
-- =============================================================================
