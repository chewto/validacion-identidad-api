import datetime
import re
from ocr import ocr
from utilidades import listToText
from utilidades import extraerPorcentaje

country = 'COL'

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
  stringOCR = stringOCR.replace(' ','')
  stringOCR = stringOCR.upper()

  ocrLength = len(stringOCR)

  findMrzIndex = stringOCR.find(mrzStartingLetter)

  if(findMrzIndex == -1):
    findMrzIndex = stringOCR.find("<")

    if(findMrzIndex == -1):
      return 'Requiere verificar – DATOS INCOMPLETOS'

  mrz = stringOCR[findMrzIndex:ocrLength]

  mrz = mrzClean(mrz)

  return mrz

def parse_mrz(mrz:str):
    print(mrz)
    splitMRZ = mrz.split(' ')
    print(splitMRZ)
    # print(mrz)

    # newMrz = mrz.replace('<', ' ')
    # print(newMrz)

    # firstLine = mrz[0:30] if isLetter else mrz[0:29]
    # print(firstLine)
    # secondLine = mrz[30:60] if isLetter else mrz[29:]
    # print(secondLine)
    # thirdLine = mrz[60:90] if isLetter else mrz[0:29]
    # print(thirdLine)
    # # Line 1
    # document_type = firstLine[0]
    # issuing_country = firstLine[2:5]
    # document_number = firstLine[5:14].replace('<', '')
    
    # # Line 2
    # birth_date = secondLine[0:6]
    # sex = secondLine[7]
    # expiry_date = secondLine[8:14]
    # nationality = secondLine[15:18].replace('<', '')
    
    # # Line 3
    # names = thirdLine.split('<<')
    # surname = names[0].replace('<', ' ').strip()
    # given_names = names[1].replace('<', ' ').strip()

    # print({
    #     'Document Type': document_type,
    #     'Issuing Country': issuing_country,
    #     'Document Number': document_number,
    #     'Date of Birth': birth_date,
    #     'Sex': sex,
    #     'Expiry Date': expiry_date,
    #     'Nationality': nationality,
    #     'Surname': surname,
    #     'Given Names': given_names
    # })

def mrzClean(mrz: str) -> str:
  translationTable = str.maketrans('KX', '<<')
  cleanedMrz = mrz.translate(translationTable)
  return cleanedMrz


def mrzInfo(mrz, searchTerm):

  splitData = mrz.split('<')

  searchSplit = searchTerm.split(' ')

  found = []

  for search in searchSplit:
    for data in splitData:
      if(search in data):
        found.append(data)

  joinedFounds = ' '.join(found)

  return joinedFounds

def comparisonMRZInfo(termList,  comparisonTerm):

  percentages = []

  for term in termList:
    percent = extraerPorcentaje(comparisonTerm, term)
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