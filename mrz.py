import datetime
import re
import numpy as np
from passporteye import read_mrz
import PIL.Image
from ocr import ocr
import pytesseract as tess
from utilidades import listToText
from utilidades import extraerPorcentaje
import io
from PIL import ImageFilter, Image
import cv2

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

documentMRZ = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": False,
                "mrzLetter":"I<"
            },
            "Cédula de extranjería": {
                "anverso": False,
                "reverso": True,
                "mrzLetter":"I<"
            },
            "Permiso por protección temporal": {
                "anverso": False,
                "reverso": False
            },
            "Pasaporte":{
                "anverso":True,
                "reverso":False,
                "mrzLetter":"P<"
            },
            "Cédula digital": {
                "anverso":False,
                "reverso":True,
                "mrzLetter": "IC"
            }
        },
        "PTY":{
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": False
            },
            "Cédula de extranjería": {
                "anverso": False,
                "reverso": False
            }
        },
  'HND': {
    "DNI":{
      "anverso": False,
      "reverso": True,
      "mrzLetter":"I<"
    },
    "Carnet de residente": {
      "anverso": False,
      "reverso": True,
      "mrzLetter": "I<"
    },
    "Pasaporte": {
      "anverso": True,
      "reverso": False,
      "mrzLetter": "P<"
    }
  },
  'SLV': {
    "DNI":{
      "anverso": False,
      "reverso": True,
      "mrzLetter":"IDSLV"
    }
  }
}

def MRZSide(documentType, documentSide, mrzData):
  mrz = mrzData[documentType][documentSide]

  mrzLetter = mrzData[documentType]["mrzLetter"]

  return mrzLetter, mrz

def hasMRZ(documentType, mrzData):
  mrzDocumentType = mrzData[documentType]

  mrzCorrespondingSide = []

  for key,value in mrzDocumentType.items():
    if(key != 'mrzLetter'):
      mrzCorrespondingSide.append(value)

  totalMRZ = any(mrzCorrespondingSide)

  return totalMRZ

def validateMRZ(documentType, mrzKeys,mrzData):
  mrzDocumentType = mrzKeys[documentType]

  mrzDataLength =True if (len(mrzData) >= 1) else False

  mrzVerify = False

  if(mrzData.find(mrzDocumentType['mrzLetter']) != -1 ):
    mrzVerify = True
  elif(mrzData.find('<') != -1 ):
    mrzVerify = True

  mrzParameters = [mrzDataLength, mrzVerify]

  mrzValidationResult = all(mrzParameters)

  return mrzValidationResult

#REVISION
# def validateMRZ(documentType, mrzKeys,mrzData):
#   mrzDocumentType = mrzKeys[documentType]

#   mrzDataLength =True if (len(mrzData) >= 1) else False

#   mrzVerify = False

#   if(mrzData.find(mrzDocumentType['mrzLetter']) != -1 ):
#     mrzVerify = True
#   elif(mrzData.find('<') != -1 ):
#     mrzVerify = True

#   mrzParameters = [mrzDataLength, mrzVerify]

#   mrzValidationResult = all(mrzParameters)

#   return mrzValidationResult


def aplicar_filtro_sharp(imagen_pil):
  return imagen_pil.filter(ImageFilter.SHARPEN)

def extractMRZ(img):

  # Convierte la imagen de formato Mat (OpenCV) a PIL
  if isinstance(img, (np.ndarray,)):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
  else:
    img_pil = img

  # Aplica el filtro sharpen
  img_pil = aplicar_filtro_sharp(img_pil)

  best_result = None
  best_score = -1

  for i in range(4):
    # Convierte de nuevo a bytes para passporteye
    img_bytes = io.BytesIO()
    img_pil.save(img_bytes, format='JPEG')
    img_bytes.seek(0)

    mrz = read_mrz(img_bytes)
    if mrz is not None:
      score = mrz.valid_score
      if score is None:
        score = 0
      if score > best_score:
        best_score = score
        best_result = mrz.to_dict()
      if score >= 80:
        break

    # Rota la imagen para el siguiente intento
    img_pil = img_pil.rotate(-90, expand=True)

  if best_result:
    return best_result
  else:
    return "No se pudo detectar MRZ válido en la imagen."


  # stringOCR = listToText(ocr)
  # stringOCR = stringOCR.replace(' ','')
  # stringOCR = stringOCR.upper()

  # ocrLength = len(stringOCR)

  # findMrzIndex = stringOCR.find(mrzStartingLetter)

  # if(findMrzIndex == -1):
  #   findMrzIndex = stringOCR.find("<")

  #   if(findMrzIndex == -1):
  #     return 'Requiere verificar – DATOS INCOMPLETOS'

  # mrz = stringOCR[findMrzIndex:ocrLength]

  # mrz = mrzClean(mrz)

  # return mrz

#REVISION
# def extractMRZ(mrzImage):

#   tess.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

#   mrzRGB = cv2.cvtColor(mrzImage, cv2.COLOR_BGR2RGB)
#   pilImage = PIL.Image.fromarray(mrzRGB)

#   imageBytes = io.BytesIO()
#   pilImage.save(imageBytes, format='JPEG')
#   imageBytes.seek(0)

#   mrz = read_mrz(imageBytes)

#   if(mrz is None):
#     return {'name': '', 'surname': ''}, False

#   mrzData = mrz.to_dict()

#   data = {
#     'name': mrzData['names'],
#     'surname': mrzData['surname'],
#     'code':  mrzData['raw_text']
#   }

#   return data, True



def mrzClean(mrz: str) -> str:
  translationTable = str.maketrans('KX', '<<')
  cleanedMrz = mrz.translate(translationTable)
  return cleanedMrz

def mrzInfo(mrz, searchTerm):
    # Split the searchTerm into words
    search_terms = [term.strip().upper() for term in searchTerm.split() if term.strip()]

    # Clean MRZ: remove digits and extra '<', split by '<'
    mrz_parts = [re.sub(r'\d', '', part).strip('<').upper() for part in mrz.split('<') if part.strip('<')]

    found = []

    for search in search_terms:
      best_match = ""
      best_percent = 0
      for i, part in enumerate(mrz_parts):
        percent = extraerPorcentaje(search, part)
        if percent > best_percent:
          best_percent = percent
          best_match = part
      # Try joining with next part if not a good match
      if best_percent < 80:  # threshold, adjust as needed
        for i in range(len(mrz_parts) - 1):
          combined = mrz_parts[i] + mrz_parts[i + 1]
          percent = extraerPorcentaje(search, combined)
          if percent > best_percent:
            best_percent = percent
            best_match = combined
      if best_match:
        found.append(best_match)

    # Remove duplicates and empty strings
    found = list(dict.fromkeys([f for f in found if f]))

    return ' '.join(found)

#REVISION
# def mrzInfo(mrz, searchTerm):

#   found = []
  
#   if mrz in searchTerm or searchTerm in mrz:
#     stripData = mrz.strip()
#     found.append(stripData)

#   joinedFounds = ' '.join(found)

#   return joinedFounds

def comparisonMRZInfo(termList, comparisonTerm):
  """
  Compares a list of terms against a comparison term using extraerPorcentaje,
  returning the term with the highest percentage match and the list of all percentages.

  Args:
    termList (list): List of terms to compare.
    comparisonTerm (str): The term to compare against.

  Returns:
    dict: {
      'best_match': {'percent': float, 'data': str},
      'all_matches': [{'percent': float, 'data': str}, ...]
    }
  """
  if not termList or not comparisonTerm:
    return  {'percent': 0, 'data': ''}

  percentages = []
  for term in termList:
    percent = extraerPorcentaje(comparisonTerm, term)
    percentages.append({'percent': percent, 'data': term})

  maxPercentage = max(percentages, key=lambda x: x['percent'], default={'percent': 0, 'data': ''})

  return maxPercentage

def extractDate(data):
    datePattern = r'\d+[MF]\d+'

    datesFound = []
    
    for line in data:
        match = re.search(datePattern, line)
        if(match is not None):
            datesFound.append(match.string)

    dates = ' '.join(datesFound)

    return dates

def expiracyDateMRZ(ocrData):

    currentDate = datetime.date.today()

    extraction = extractDate(data=ocrData)

    expiracyDateFound = ''

    searchChars = ['M', 'F']

    for char in searchChars:
      find = extraction.find(char)
      if(find != -1):
        substringStart = find + 1
        substringEnd = substringStart + 6
        dateFound = extraction[substringStart:substringEnd]
        year = int('20'+dateFound[0:2])
        month = int(dateFound[2:4])
        day = int(dateFound[4:6])
        date = datetime.date(year, month, day)
        expiracyDateFound = date
    
    if(expiracyDateFound <= currentDate):
      return True

    return False