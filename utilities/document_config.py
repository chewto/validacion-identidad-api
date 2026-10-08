"""Configuracion de validacion de ubicacion y politica anti-VPN, por entidad.

La config vive en columnas de `usuarios.entidades` (`validar_ubicacion`,
`bloquear_vpn`, `radio_ubicacion_m`, `ubicacion_lat`, `ubicacion_lng`), junto
al resto de parametros de validacion por entidad que ya existen ahi
(`validacion_vida`, `porcentaje_acierto`, `intentos_documentos`,
`intentos_deteccion`, `intentos_rostro`). No hay tabla nueva.

El documento se resuelve a su entidad con los mismos joins que usa
`/validation-params`: por `parametros_hash` (standalone) o por `id_firmador`
(embebido), que en los dos casos termina en `usuarios.entidades.entity_id`.

Si las columnas todavia no existen en la base de datos, o la entidad no
devuelve fila, se entrega el default fail-open que ya usa el frontend
(`DEFAULT_DOCUMENT_CONFIG`): `false/false`, y queda el log. El backend sigue
siendo la autoridad: si `validar_ubicacion` esta activo, el rechazo ocurre en
la firma con LOCATION_REQUIRED aunque la consulta al endpoint haya fallado.
"""
import os
from dataclasses import dataclass
from typing import Optional

import request.controlador_db as controlador_db
import utilities.logs as logs

_COLS = (
    "ent.validar_ubicacion, ent.bloquear_vpn, ent.radio_ubicacion_m, "
    "ent.ubicacion_lat, ent.ubicacion_lng, ent.entity_id"
)

_SELECT_HASH = f"""
SELECT {_COLS}
FROM pki_validacion.parametros_validacion AS params
INNER JOIN usuarios.usuarios AS usu ON usu.id = params.id_usuario
INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id
WHERE params.parametros_hash = %s
LIMIT 1
"""

_SELECT_FIRMADOR = f"""
SELECT {_COLS}
FROM pki_firma_electronica.firmador_pki AS fir
INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id
INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id
INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id
WHERE fir.id = %s
LIMIT 1
"""


def _log(message):
    try:
        logs.addLog(logs.checkLogsFile(), message)
    except Exception:
        pass


def default_radius_meters():
    """Radio por defecto si la entidad no lo define.
    Logs a warning when the environment variable is missing or malformed.
    """
    try:
        return int(os.getenv("LOCATION_DEFAULT_RADIUS_METERS", "500"))
    except (TypeError, ValueError):
        _log("WARNING: LOCATION_DEFAULT_RADIUS_METERS not set or invalid – using default 500.")
        return 500


@dataclass(frozen=True)
class DocumentConfig:
    require_location_validation: bool = False
    block_on_vpn: bool = False
    location_radius_meters: Optional[int] = None
    region_lat: Optional[float] = None
    region_lng: Optional[float] = None
    entity_id: Optional[int] = None

    @property
    def radius_meters(self) -> int:
        """Radio efectivo: el configurado o el de entorno."""
        return self.location_radius_meters or default_radius_meters()

    @property
    def has_region(self) -> bool:
        return self.region_lat is not None and self.region_lng is not None


DEFAULT_CONFIG = DocumentConfig()


def _to_config(row) -> DocumentConfig:
    return DocumentConfig(
        require_location_validation=bool(row[0]),
        block_on_vpn=bool(row[1]),
        location_radius_meters=int(row[2]) if row[2] is not None else None,
        region_lat=float(row[3]) if row[3] is not None else None,
        region_lng=float(row[4]) if row[4] is not None else None,
        entity_id=int(row[5]) if len(row) > 5 and row[5] is not None else None,
    )


def load_document_config(hash_=None, efirma_id=None, country=None) -> DocumentConfig:
    """Config de seguridad del documento, resuelta a traves de su entidad.

    `hash_` (standalone) tiene prioridad sobre `efirma_id` (embebido).
    Cualquier fallo (columnas no aplicadas, error de conexion, entidad sin
    fila) devuelve DEFAULT_CONFIG y queda registrado en el log.
    """
    if hash_:
        query, value, origen = _SELECT_HASH, hash_, "parametros_hash"
    elif efirma_id:
        query, value, origen = _SELECT_FIRMADOR, efirma_id, "id_firmador"
    else:
        return DEFAULT_CONFIG

    query = f"""
SELECT {_COLS}
FROM pki_firma_electronica.firmador_pki AS fir
INNER JOIN pki_firma_electronica.firma_electronica_pki AS fe ON fe.id = fir.firma_electronica_id
INNER JOIN usuarios.usuarios AS usu ON usu.id = fe.usuario_id
INNER JOIN usuarios.entidades AS ent ON ent.entity_id = usu.entity_id
WHERE fir.id = {value}
LIMIT 1
"""

    try:
        row = controlador_db.selectData(query, (), pais=country)
    except Exception as e:
        _log(f"entidades: fallo consultando {origen}={value}: {e}")
        return DEFAULT_CONFIG

    # `selectData` no propaga los pymysql.Error: devuelve () tanto si no hay
    # fila como si las columnas de seguridad todavia no existen (Unknown
    # column). Los dos casos son fail-open, pero conviene distinguirlos en el
    # log porque el segundo significa "falta el ALTER en esta base".
    if not row:
        _log(
            f"entidades: sin config de seguridad para {origen}={value} "
            "(entidad no encontrada o columnas validar_ubicacion/bloquear_vpn "
            "sin aplicar en esta base de datos)"
        )
        return DEFAULT_CONFIG

    try:
        return _to_config(row)
    except Exception as e:
        _log(f"entidades: fila invalida para {origen}={value}: {e}")
        return DEFAULT_CONFIG