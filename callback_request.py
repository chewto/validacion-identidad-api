import requests
import logs


def callbackRequest(data, state, validationParams, validationPercent, id):

  callback = {
    'url': data[0],
    'bearer': data[1]
  }

  callbackBody = {
    'claveApi':callback['bearer'],
    'estadoValidacion':state,
    'parametrosValidacion':validationParams,
    'porcentajeValidacion':validationPercent,
    'enlaceFirma': f'https://honducert.firma.e-custodia.com/mostrar_validacion?idUsuario={id}'
    # 'enlaceFirma': f'https://desarrollo.e-custodia.com/mostrar_validacion?idUsuario={id}'
  }

  print(callback)

  if(callback['url'] == None):
    return ''
  
  try:
    
    res = requests.post(url=callback['url'], json=callbackBody)
  except requests.RequestException as e:
    path = logs.checkLogsFile()
    writeLog = logs.writeLogs(path, f'{e}, ha fallado la callback')