import requests
import logs


def callbackRequest(data, callbackBody):

  callback = {
    'url': data[0],
    'bearer': data[1]
  }

  
  # if(standalone == None):
  #   callbackBody['enlaceFirma'] = f'https://desarrollo.e-custodia.com/mostrar_validacion?idUsuario={idUser}'
  # else:
  #   callbackBody['enlaceValidacion'] = f'https://desarrollo.firma.e-custodia.com/resultado_validacion?id={idValidation}&idUsuario={idUser}&tipo={typeParam}',

  if(callback['url'] == None):
    return ''
  
  try:
    res = requests.post(url=callback['url'], json=callbackBody)
  except requests.RequestException as e:
    path = logs.checkLogsFile()
    writeLog = logs.writeLogs(path, f'{e}, ha fallado la callback')