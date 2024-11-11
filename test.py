import check_result

loco = {'movementCheck': True, 'antiSpoofing': False, 'coincidencia': False, 'frontSideCheck': True, 'mrzCheck': False, 'barcodeCheck': True, 'ocrNameCheck': True, 'ocrLastNameCheck': True, 'ocrIDCheck': True}

resulst = check_result.results(percent=90, validatioAttendance='AUTOMATICA', checksDict=loco)

print(resulst)