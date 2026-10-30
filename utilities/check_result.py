# Tolerancias de comparacion de datos personales. Se mantienen los valores que
# ya usaba el proyecto: 50% para OCR y 51 para la zona MRZ.
OCR_MATCH_THRESHOLD = 50
MRZ_MATCH_THRESHOLD = 51
MRZ_VALID_SCORE_MIN = 51

FIELD_LABELS = {
  'name': 'nombre',
  'lastName': 'apellido',
  'ID': 'número de documento',
}

_OCR_MISMATCH_MESSAGES = {
  'name': 'Su nombre no coincide con los datos legibles del documento.',
  'lastName': 'Su apellido no coincide con los datos legibles del documento.',
  'ID': 'Su número de documento no coincide con los datos detectados.',
}

_MRZ_MISMATCH_MESSAGES = {
  'name': 'Su nombre no coincide con la zona de lectura mecánica (MRZ).',
  'lastName': 'Su apellido no coincide con la zona de lectura mecánica (MRZ).',
}

_OCR_UNREADABLE_MESSAGES = {
  'name': 'No se pudo leer el nombre en el documento. Verifique que la imagen esté nítida e intente nuevamente.',
  'lastName': 'No se pudo leer el apellido en el documento. Verifique que la imagen esté nítida e intente nuevamente.',
  'ID': 'No se pudo leer el número de documento en el documento. Verifique que la imagen esté nítida e intente nuevamente.',
}

_MRZ_UNREADABLE_MESSAGES = {
  'name': 'No se pudo leer el nombre en la zona de lectura mecánica (MRZ).',
  'lastName': 'No se pudo leer el apellido en la zona de lectura mecánica (MRZ).',
}


def hasReadableOcr(ocrLines):
  """True si hay al menos una linea de OCR con contenido util.

  Evita reportar un dato como "no coincide" cuando el OCR no devolvio texto.
  """
  if not ocrLines:
    return False

  if isinstance(ocrLines, str):
    ocrLines = [ocrLines]

  try:
    return any(isinstance(line, str) and len(line.strip()) >= 2 for line in ocrLines)
  except TypeError:
    return False


def isValidMrz(mrz):
  """True solo si el MRZ extraido es un dict con valid_score >= 51."""
  if not isinstance(mrz, dict):
    return False

  score = mrz.get('valid_score')

  return isinstance(score, (int, float)) and not isinstance(score, bool) and score >= MRZ_VALID_SCORE_MIN


def _thresholdFor(source):
  return MRZ_MATCH_THRESHOLD if source == 'mrz' else OCR_MATCH_THRESHOLD


def _hasMismatchFor(mismatches, field):
  return any(item.get('field') == field for item in mismatches)


def _appendMessage(messages, message):
  if message and message not in messages:
    messages.append(message)


def registerFieldMismatch(mismatches, messages, field, source, percentage):
  """Registra un dato personal que no coincide. Un solo registro por campo."""
  if _hasMismatchFor(mismatches, field):
    return

  message = _MRZ_MISMATCH_MESSAGES.get(field) if source == 'mrz' else _OCR_MISMATCH_MESSAGES.get(field)

  if not message:
    return

  mismatches.append({
    'field': field,
    'label': FIELD_LABELS.get(field, field),
    'source': source,
    'message': message,
    'percentage': int(round(float(percentage or 0))),
    'threshold': _thresholdFor(source),
  })

  _appendMessage(messages, message)


def registerUnreadableField(mismatches, messages, field, source):
  """Registra que un dato no se pudo leer, sin marcarlo como discrepancia."""
  if _hasMismatchFor(mismatches, field):
    return

  message = _MRZ_UNREADABLE_MESSAGES.get(field) if source == 'mrz' else _OCR_UNREADABLE_MESSAGES.get(field)

  _appendMessage(messages, message)


def evaluateField(mismatches, messages, field, source, providedValue, percentage,
                  readable=True, detectedValue=''):
  """Compara un dato del usuario contra lo leido en el documento.

  - Si el usuario no envio el dato, no se evalúa.
  - Si la fuente no fue legible, agrega un mensaje de lectura, no un mismatch.
  - Si el porcentaje queda por debajo de la tolerancia, agrega el mismatch.
  """
  if not providedValue:
    return

  if not readable:
    registerUnreadableField(mismatches, messages, field, source)
    return

  if source == 'mrz' and not detectedValue:
    registerUnreadableField(mismatches, messages, field, source)
    return

  if float(percentage or 0) < _thresholdFor(source):
    registerFieldMismatch(mismatches, messages, field, source, percentage)


def results(percent, validatioAttendance, checksDict):

  print(checksDict)

  values = []

  totalPercent = 0

  for key, value in checksDict.items():
    values.append(value)

  valuesLength = len(values)

  valuePercent = 100 / valuesLength

  for value in values:
    if value == True or value == 'OK':
      totalPercent += valuePercent

  if totalPercent >= percent and validatioAttendance == 'AUTOMATICA':
    return True,'verificado', totalPercent
  elif totalPercent >= percent and validatioAttendance == 'MIXTA':
    return True,'iniciando segunda validación', totalPercent
  elif validatioAttendance == 'MANUAL':
    return True,'esperando aprobación', totalPercent
  else:
    return False,'validación fallida', totalPercent
    # return False,'Procesando validación', totalPercent

def testingType(array):

  filt = filter(lambda x: x['validation'] == True ,array)

  filteredList = list(filt)

  if(len(filteredList) >= 1):
    firstElement = filteredList[0]
    return firstElement['type'],firstElement['validation']
  else:
    return 'no detectado', False
  
  
def testingCountry(array):

  filt = filter(lambda x: x['validation'] == True ,array)

  filteredList = list(filt)

  if(len(filteredList) >= 1):
    firstElement = filteredList[0]
    return firstElement['country'], firstElement['countryDetected'], firstElement['validation']
  else:
    return 'no detectado','no detectado', False