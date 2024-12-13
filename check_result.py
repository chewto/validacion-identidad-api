def results(percent, validatioAttendance, checksDict):

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
    return True,'iniciando segunda validacion', totalPercent
  elif validatioAttendance == 'MANUAL':
    return True,'esperando aprobacion', totalPercent
  else:
    return False,'No verificado', totalPercent

def testingType(array):

  filt = filter(lambda x: x['validation'] == 'OK' ,array)

  filteredList = list(filt)

  if(len(filteredList) >= 1):
    firstElement = filteredList[0]
    return firstElement['type'],firstElement['validation']
  else:
    return 'no detectado', '!OK'
  
  
def testingCountry(array):

  filt = filter(lambda x: x['validation'] == 'OK' ,array)

  filteredList = list(filt)

  if(len(filteredList) >= 1):
    firstElement = filteredList[0]
    return firstElement['country'], firstElement['countryDetected'], firstElement['validation']
  else:
    return 'no detectado','no detectado', '!OK'