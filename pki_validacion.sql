-- --------------------------------------------------------
-- Host:                         93.93.119.219
-- Versión del servidor:         10.6.12-MariaDB-0ubuntu0.22.04.1 - Ubuntu 22.04
-- SO del servidor:              debian-linux-gnu
-- HeidiSQL Versión:             12.5.0.6677
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Volcando estructura de base de datos para pki_validacion
CREATE DATABASE IF NOT EXISTS `pki_validacion` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci */;
USE `pki_validacion`;

-- Volcando estructura para tabla pki_validacion.documento_usuario
CREATE TABLE IF NOT EXISTS `documento_usuario` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `nombres` varchar(50) NOT NULL,
  `apellidos` varchar(50) NOT NULL,
  `numero_documento` varchar(50) NOT NULL,
  `tipo_documento` varchar(50) NOT NULL,
  `email` varchar(50) NOT NULL,
  `id_evidencias` int(11) NOT NULL,
  `id_evidencias_adicionales` int(11) NOT NULL,
  `id_usuario_efirma` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=105 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- La exportación de datos fue deseleccionada.

-- Volcando estructura para tabla pki_validacion.evidencias_adicionales
CREATE TABLE IF NOT EXISTS `evidencias_adicionales` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `estado_verificacion` varchar(50) NOT NULL,
  `dispositivo` varchar(50) NOT NULL,
  `navegador` varchar(50) NOT NULL,
  `ip_privada` varchar(25) NOT NULL,
  `latitud` varchar(50) NOT NULL,
  `longitud` varchar(50) NOT NULL,
  `hora` varchar(50) NOT NULL,
  `fecha` varchar(50) NOT NULL,
  `ip_publica` varchar(25) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=92 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- La exportación de datos fue deseleccionada.

-- Volcando estructura para tabla pki_validacion.evidencias_usuario
CREATE TABLE IF NOT EXISTS `evidencias_usuario` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `anverso_documento` mediumblob NOT NULL,
  `reverso_documento` mediumblob NOT NULL,
  `foto_usuario` mediumblob NOT NULL,
  `estado_verificacion` varchar(10) NOT NULL,
  `tipo_documento` varchar(50) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=106 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- La exportación de datos fue deseleccionada.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
