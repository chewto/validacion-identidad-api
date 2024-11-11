def results(percent, validatioAttendance, checksDict):

  values = []

  totalPercent = 0

  for key, value in checksDict.items():
    values.append(value)

  valuesLength = len(values)

  valuePercent = 100 / valuesLength

  for value in values:
    if value == True:
      totalPercent += valuePercent

  if totalPercent >= percent and validatioAttendance == 'AUTOMATICA':
    return 'verificado', totalPercent
  elif totalPercent >= percent and validatioAttendance == 'MIXTA':
    return 'iniciando segunda validacion', totalPercent
  elif validatioAttendance == 'MANUAL':
    return 'esperando aprobacion', totalPercent
  else:
    return 'No verificado', totalPercent