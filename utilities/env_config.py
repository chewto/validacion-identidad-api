"""Lectura de configuracion numerica desde variables de entorno.

Modulo deliberadamente liviano (solo ``os``) para poder testearse sin cargar
OpenCV, TensorFlow ni Flask.
"""

import os


def env_int(name, default, minimum=None):
    """Devuelve el entero de la variable de entorno ``name``.

    - Variable ausente, vacia o solo espacios -> ``default``.
    - Valor no entero -> advertencia y ``default`` (nunca lanza excepcion).
    - Valor por debajo de ``minimum`` -> advertencia y ``minimum``.
    """
    raw = os.environ.get(name)

    if raw is None or not str(raw).strip():
        return default

    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        print(f"[config] {name}={raw!r} no es un entero; se usa {default}.")
        return default

    if minimum is not None and value < minimum:
        print(f"[config] {name}={value} es menor que el minimo {minimum}; se usa {minimum}.")
        return minimum

    return value
