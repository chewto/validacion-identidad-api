import datetime
import re

import PIL.Image
from ocr import ocr
from utilidades import listToText
from utilidades import extraerPorcentaje
import io
import PIL
import cv2
from passporteye import read_mrz
from passporteye.mrz.text import MRZ
import pytesseract as tess


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

def extractMRZ(mrzImage):

  tess.pytesseract.tesseract_cmd = r'C:/Program Files/Tesseract-OCR/tesseract.exe'

  mrzRGB = cv2.cvtColor(mrzImage, cv2.COLOR_BGR2RGB)
  pilImage = PIL.Image.fromarray(mrzRGB)

  imageBytes = io.BytesIO()
  pilImage.save(imageBytes, format='JPEG')
  imageBytes.seek(0)

  mrz = read_mrz(imageBytes)

  if(mrz is None):
    return {'name': '', 'surname': ''}, False

  mrzData = mrz.to_dict()

  data = {
    'name': mrzData['names'],
    'surname': mrzData['surname'],
    'code':  mrzData['raw_text']
  }

  return data, True



def mrzClean(mrz: str) -> str:
  translationTable = str.maketrans('KX', '<<')
  cleanedMrz = mrz.translate(translationTable)
  return cleanedMrz


def mrzInfo(mrz, searchTerm):

  found = []
  
  if mrz in searchTerm or searchTerm in mrz:
    stripData = mrz.strip()
    found.append(stripData)

  joinedFounds = ' '.join(found)

  return joinedFounds

def comparisonMRZInfo(termList,  comparisonTerm):

  percentages = []

  for term in termList:
    percent = extraerPorcentaje(comparisonTerm, term)
    print({'percent': percent, 'data': term})
    percentages.append({'percent': percent, 'data': term})

  maxPercentage = max(percentages, key=lambda x: x['percent'])

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