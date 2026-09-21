import json
import os
import re
import tempfile

import request.controlador_db as controlador_db

PROGRESS_DIR = "./progreso-validacion"

_ID_RE = re.compile(r"^\d+$")
_COUNTRY_RE = re.compile(r"^[A-Za-z]{2,5}$")


def _resolve_country(country=None):
  if country:
    country = str(country).strip().upper()
  else:
    country = controlador_db.get_country_code()

  if not _COUNTRY_RE.match(country):
    raise ValueError("El país es inválido")

  return country


def _progress_path(id_usuario, country=None):
  id_usuario = str(id_usuario).strip()

  if not _ID_RE.match(id_usuario):
    raise ValueError("El id de usuario es inválido")

  country = _resolve_country(country)

  return os.path.join(PROGRESS_DIR, country, f"{id_usuario}.json")


def save_progress(id_usuario, data, country=None):
  path = _progress_path(id_usuario, country)
  folder = os.path.dirname(path)

  os.makedirs(folder, exist_ok=True)

  fd, tmp_path = tempfile.mkstemp(dir=folder, suffix=".tmp")
  try:
    with os.fdopen(fd, "w", encoding="utf-8") as file:
      json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
  except Exception:
    if os.path.exists(tmp_path):
      os.remove(tmp_path)
    raise

  return path


def get_progress(id_usuario, country=None):
  path = _progress_path(id_usuario, country)

  if not os.path.exists(path):
    return None

  with open(path, "r", encoding="utf-8") as file:
    return json.load(file)
