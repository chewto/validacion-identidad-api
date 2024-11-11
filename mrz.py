from ocr import ocr
from utilidades import listToText

country = 'HND'

documentMRZ = {
  "COL": {
            "Cédula de ciudadanía": {
                "anverso": False,
                "reverso": False
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
  }
}

def MRZSide(documentType, documentSide):
  mrz = documentMRZ[country][documentType][documentSide]

  mrzLetter = documentMRZ[country][documentType]["mrzLetter"]

  return mrzLetter, mrz

def hasMRZ(documentType):
  mrzDocumentType = documentMRZ[country][documentType]

  mrzCorrespondingSide = []

  for key,value in mrzDocumentType.items():
    if(key != 'mrzLetter'):
      mrzCorrespondingSide.append(value)

  totalMRZ = any(mrzCorrespondingSide)

  return totalMRZ

def validateMRZ(documentType, mrzData):
  mrzDocumentType = documentMRZ[country][documentType]

  mrzDataLength =True if (len(mrzData) >= 1) else False

  mrzVerify = False

  if(mrzData.find(mrzDocumentType['mrzLetter']) != -1 ):
    mrzVerify = True
  elif(mrzData.find('<') != -1 ):
    mrzVerify = True

  mrzParameters = [mrzDataLength, mrzVerify]

  mrzValidationResult = all(mrzParameters)

  return mrzValidationResult

def extractMRZ(ocr, mrzStartingLetter):
  stringOCR = listToText(ocr)

  ocrLength = len(stringOCR)

  findMrzIndex = stringOCR.find(mrzStartingLetter)

  if(findMrzIndex == -1):
    findMrzIndex = stringOCR.find("<")

    if(findMrzIndex == -1):
      return 'no se encontro el codigo mrz'


  mrz = stringOCR[findMrzIndex:ocrLength]

  return mrz