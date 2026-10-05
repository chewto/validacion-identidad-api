"""Pipeline de seguridad de los endpoints de firma.

Orden (acordado en el plan):

    1. cargar la config de la entidad del documento (hash / efirmaId)
    2. si `require_location_validation`: validar `location` (400/403)
    3. si `block_on_vpn`: resolver la IP del firmante y consultar el proveedor
       de inteligencia (403, salvo fail-open del proveedor)

Devuelve `(config, None)` si todo pasa, o `(config, (body, status))` con la
respuesta de error que hay que devolver tal cual.

El veredicto queda publicado en `flask.g.location_security` para que cada
endpoint lo persista dentro de `checks_json` como evidencia auditable.
"""
import datetime

from flask import g, has_request_context

from utilities import ip_intel, location_guard
from utilities.api_errors import (
    LOCATION_UNAVAILABLE,
    PROXY_DETECTED,
    VPN_DETECTED,
    error_response,
)
from utilities.document_config import DEFAULT_CONFIG, load_document_config

FAIL_OPEN = "fail_open"


def _now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _store_audit(audit):
    if has_request_context():
        g.location_security = audit


def _audit_base(config):
    return {
        "checked_at": _now(),
        "entity_id": config.entity_id,
        "require_location_validation": config.require_location_validation,
        "block_on_vpn": config.block_on_vpn,
        "result": "ok",
    }


def _location_audit(config, location):
    check = location_guard.check_location(location, config)
    return check, {
        "location_present": location is not None,
        "location": check["location"],
        "accuracy_m": check["accuracy"],
        "radius_meters": config.radius_meters,
        "distance_m": check["distance_m"],
        "region": (
            {"latitude": config.region_lat, "longitude": config.region_lng}
            if config.has_region
            else None
        ),
    }


def _vpn_audit(info_ip):
    ip = ip_intel.client_ip(fallback_ip=info_ip)
    audit = {"ip": ip, "ip_available": False, "ip_provider": None, "ip_flags": None}
    if not ip:
        audit["result"] = LOCATION_UNAVAILABLE
        return None, audit, LOCATION_UNAVAILABLE

    verdict = ip_intel.check_ip(ip)
    audit["ip_provider"] = verdict.provider
    audit["ip_available"] = verdict.available
    if verdict.available:
        audit["ip_flags"] = {
            "is_vpn": verdict.is_vpn,
            "is_proxy": verdict.is_proxy,
            "is_tor": verdict.is_tor,
            "is_datacenter": verdict.is_datacenter,
        }
        audit["ip_geo"] = {
            "country": verdict.country,
            "latitude": verdict.geo_lat,
            "longitude": verdict.geo_lon,
        }
        kind = ip_intel.blocked_kind(verdict)
        if kind == "proxy":
            audit["result"] = PROXY_DETECTED
            return verdict, audit, PROXY_DETECTED
        if kind == "vpn":
            audit["result"] = VPN_DETECTED
            return verdict, audit, VPN_DETECTED
        return verdict, audit, None

    # Proveedor caido / sin key / sin respuesta: no se bloquea, solo se audita.
    audit[FAIL_OPEN] = verdict.error
    return verdict, audit, None


def evaluate_signature_security(hash_=None, efirma_id=None, location=None, info_ip=None):
    """Evalua la politica de ubicacion y anti-VPN de un POST de firma.

    Returns:
        `(config, None)` si paso, o `(config, (body, status))` si hay que
        rechazar la peticion.
    """
    config = load_document_config(hash_=hash_, efirma_id=efirma_id) or DEFAULT_CONFIG
    audit = _audit_base(config)

    # --- 1. ubicacion obligatoria ---------------------------------------
    if config.require_location_validation:
        check, location_info = _location_audit(config, location)
        audit.update(location_info)
        if check["error"]:
            code, status = check["error"]
            audit["result"] = code
            _store_audit(audit)
            return config, error_response(code, status=status)
    else:
        audit["location_present"] = location is not None
        audit["location_ignored"] = location is not None

    # --- 2. politica anti-VPN -------------------------------------------
    if config.block_on_vpn:
        verdict, vpn_info, error_code = _vpn_audit(info_ip)
        audit.update(vpn_info)
        if error_code:
            audit["result"] = error_code
            _store_audit(audit)
            return config, error_response(error_code, status=403)

    _store_audit(audit)
    return config, None
