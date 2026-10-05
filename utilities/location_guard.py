"""Validacion geografica del payload `location` de los endpoints de firma.

`location = { latitude, longitude, accuracy }` en WGS84 decimal, con
`accuracy` en metros (radio de confianza del GPS).

Se devuelven exactamente los codigos que el frontend mapea a modal:
LOCATION_REQUIRED (400) y LOCATION_MISMATCH (403).
"""
import math

from utilities.api_errors import LOCATION_MISMATCH, LOCATION_REQUIRED

# Radio medio terrestre en metros (WGS84), usado por la formula haversine.
EARTH_RADIUS_M = 6371008.8


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Distancia en metros entre dos puntos WGS84."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def _number(value):
    """Convierte a float descartando bools, NaN, infinitos y no numericos."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


def check_location(location, config):
    """Valida `location` contra la config del documento.

    Returns:
        dict con:
          - `location`: coords ya normalizadas (o None si no pasaron los tipos)
          - `accuracy`: accuracy en metros (o None)
          - `distance_m`: distancia al centro configurado (o None)
          - `error`: `(code, status)` si hay que rechazar, o None
    """
    result = {"location": None, "accuracy": None, "distance_m": None, "error": None}

    if not isinstance(location, dict):
        result["error"] = (LOCATION_REQUIRED, 400)
        return result

    latitude = _number(location.get("latitude"))
    longitude = _number(location.get("longitude"))
    accuracy = _number(location.get("accuracy"))

    tipos_validos = (
        latitude is not None
        and longitude is not None
        and accuracy is not None
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
        and accuracy >= 0.0
    )
    if not tipos_validos:
        result["error"] = (LOCATION_REQUIRED, 400)
        return result

    result["location"] = {
        "latitude": latitude,
        "longitude": longitude,
        "accuracy": accuracy,
    }
    result["accuracy"] = accuracy

    radius = config.radius_meters

    # Un GPS menos preciso que el radio de tolerancia no garantiza estar dentro.
    if accuracy > radius:
        result["error"] = (LOCATION_MISMATCH, 403)
        return result

    if config.has_region:
        distance = haversine_m(latitude, longitude, config.region_lat, config.region_lng)
        result["distance_m"] = round(distance, 2)
        if distance > radius:
            result["error"] = (LOCATION_MISMATCH, 403)
            return result

    return result
