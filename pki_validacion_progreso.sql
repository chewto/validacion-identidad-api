-- ------------------------------------------------------------------
-- Migración: guardado de progreso de validación (continuar en otro dispositivo)
-- Crear tablas en pki_validacion de AMBAS bases: COL y HND
-- Ejecutar este mismo archivo en cada base de datos (DB_COL y DB_HON).
-- ------------------------------------------------------------------

-- ------------------------------------------------------------------
-- Tabla progreso_validacion
-- 1 fila por sesión activa (id_firmador) para el resume rápido.
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pki_validacion`.`progreso_validacion` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `id_firmador` bigint(20) NOT NULL COMMENT 'id del firmador (flujo eFirma)',
  `paso_actual` varchar(25) NOT NULL DEFAULT 'INICIO' COMMENT 'INICIO|ANVERSO|REVERSO|SELFIE|FINALIZADO',
  `estado` varchar(20) NOT NULL DEFAULT 'EN_PROGRESO' COMMENT 'EN_PROGRESO|COMPLETADO|ABANDONADO',
  `progreso_json` json DEFAULT NULL COMMENT 'resumen de resultados por paso (sin imágenes)',
  `creado_en` datetime NOT NULL DEFAULT current_timestamp(),
  `actualizado_en` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `completado_en` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_firmador_estado` (`id_firmador`,`estado`),
  KEY `idx_actualizado_en` (`actualizado_en`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ------------------------------------------------------------------
-- Tabla eventos_validacion
-- 1 fila por transición de paso (analítica / funnel).
-- ------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `pki_validacion`.`eventos_validacion` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `id_firmador` bigint(20) NOT NULL COMMENT 'id del firmador (flujo eFirma)',
  `paso` varchar(25) NOT NULL COMMENT 'INICIO|ANVERSO|REVERSO|SELFIE|FINALIZADO',
  `resultado` varchar(50) DEFAULT NULL COMMENT 'OK|!OK',
  `metadata_json` json DEFAULT NULL COMMENT 'detalle del resultado del paso',
  `creado_en` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `idx_firmador` (`id_firmador`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
