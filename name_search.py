import re

def searchName(ocr ):

  nombre = ""
  apellido = ""

  for i, (bbox, text, prob) in enumerate(ocr):

    text = text.upper()

    if "NOMBRE"  in text or "FORENAME" in text or "NAME" in text or "NOM" in text or "FORE" in text or "NON" in text:
        nombre = ocr[i + 1][1]
        if (not "APELLIDO" in text or not "FORENAME" in text):
          nombre += f' {ocr[i + 2][1]}'
    elif "APELLIDO" in text or "SURNAME" in text or "APELL" in text or "SUR" in text or "APE" in text or "SU" in text:
        apellido = ocr[i + 1][1]  
        if (not "NACI" in text or not "FEC" in text):
          apellido += f' {ocr[i + 2][1]}'

  return nombre, apellido

def searchId(ocr):
  document_number = ""

  # Regex pattern for the document number (e.g., d4 d4 d5)
  pattern = r'\b\d{4} \d{4} \d{5}\b'
  
  textOcr = ''
  for _, text, _ in ocr:
    textOcr += f"{text} "

  match = re.search(pattern, textOcr)
  if match:
    document_number = match.group()

  return document_number

  # ref = []
  
  # for coords, data, _ in ocr:
  #   print(coords, data)
  #   # if('NOMBRE' in data or 'FORENAME' in data):
  #   # if('APELLIDO' in data or 'SURNAME' in data):
  #   if('NÚMERO DE IDENTIFICACIÓN' in data):
  #     ref.append([coords,data])

  # print(ref, 'referencias')


  # refPosition = 'below'
  # nearestDates = []
  # min_distance = float('inf')

  # if(len(ref) <= 0):
  #   return False

  # reference = ref[0]

  # for (coords, data, _) in ocr:
  #       x, y = coords[0]
  #       if reference:
  #           refCoords, _ = reference
  #           rX, rY = refCoords[0]

  #           if(refPosition == 'right'):
  #               if x > rX:
  #                   distance = abs(x - rX) + abs(y - rY)
  #                   if distance < min_distance:
  #                       min_distance = distance
  #                       nearestDates = [data]
  #                   elif distance == min_distance:
  #                       nearestDates.append(data)
  #           if(refPosition == 'below'):
  #               if y > rY:
  #                 if(x > rX or (10-x) > rX or (10+x) > rX):
  #                   print(data , '=', y, rY, ' - ', x, rX)
  #                   # distance = abs(x - rX) + abs(y - rY)
  #                   # if distance < min_distance:
  #                     # min_distance = distance
  #                   nearestDates.append(data)
  #                   # elif distance == min_distance:
  #                   #   nearestDates.append(data)


  #           # if(refPosition == 'below'):
  #           #   if y > rY:
  #           #     if(x > rX or (10-x) > rX or (10+x) > rX):
  #           #       print(data , '=', y, rY, ' - ', x, rX)
  #           #       distance = abs(x - rX) + abs(y - rY)
  #           #       if distance < min_distance:
  #           #         min_distance = distance
  #           #         nearestDates = [data]  
  #           #       elif distance == min_distance:
  #           #         nearestDates.append(data)

  # print(nearestDates, 'aaa')

  # return ''