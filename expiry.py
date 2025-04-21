import re
import datetime

formats = {
    'DD/MM/YY':'DD/MM/YY',
    'YY/MM/DD':'YY/MM/DD'
}

documentHash = {
    'HND':{
        'DNI':{
            'anverso': {
                "hasExpiry": True,
                "namedMonth": False,
                "position": 'below',
                "keyword": ['EXPIRACIÓN', 'EXPIRY', 'EXPIRACION'],
                "format": formats['DD/MM/YY']
            },
            'reverso': {
                "hasExpiry": False,
                "namedMonth": False,
                "position": 'below',
                "keyword": ''
            }
        },
        'PASAPORTE': {
            'anverso': {
                "hasExpiry": True,
                "namedMonth": True,
                "position": 'below',
                "keyword": ['VENCIMIENTO', 'EXPIRY'],
                "format": formats['DD/MM/YY']
            },
            'reverso': {
                "hasExpiry": False,
                "namedMonth": False,
                "position": 'below',
                "keyword": ''
            }
        }
    },
    "COL": {
            "CEDULA DE CIUDADANIA": {
                'anverso': {
                  "hasExpiry": False,
                  "namedMonth": False,
                  "position": 'below',
                  "keyword": '',
                "format": formats['YY/MM/DD']
                },
                'reverso': {
                    "hasExpiry": False,
                    "namedMonth": False,
                    "position": 'below',
                    "keyword": ''
                }
            },
            "CEDULA DE EXTRANJERIA": {
                'anverso': {
                    "hasExpiry": True,
                    "namedMonth": False,
                    "position": 'right',
                    "keyword": ['VENCE'],
                    "format": formats['YY/MM/DD']
            },
                'reverso': {
                    "hasExpiry": False,
                    "namedMonth": False,
                    "position": 'below',
                    "keyword": ''
                }
            },
            "PASAPORTE": {
                'anverso': {
                "hasExpiry": True,
                "namedMonth": True,
                "position": 'below',
                "keyword": ['VENCIMIENTO', 'EXPIRY'],
                "format": formats['DD/MM/YY']
            },
            'reverso': {
                "hasExpiry": False,
                "namedMonth": False,
                "position": 'below',
                "keyword": ''
            }
            },
            "CEDULA DIGITAL": {
                'anverso': {
                "hasExpiry": True,
            "namedMonth": True,
                "position": 'below',
                "keyword": ['EXPIRACIÓN', 'EXPIRACION'],
                "format": formats['DD/MM/YY']
            },
            'reverso': {
                "hasExpiry": False,
                "namedMonth": False,
                "position": 'below',
                "keyword": ''
            }
            }
    },
    'SLV': {
        'DNI':{
            'anverso': {
                "hasExpiry": True,
                "namedMonth": False,
                "position": 'below',
                "keyword": ['EXPIRACIÓN', 'EXPIRATION', 'EXPIRACION'],
                "format": formats['DD/MM/YY']
            },
            'reverso': {
                "hasExpiry": False,
                "namedMonth": False,
                "position": 'below',
                "keyword": ''
            }
        }
    }
}

def dateFormatter(date, dateFormat):

    print(date)

    dateArray = date.split(' ')
    dateInt = [int(num) for num in dateArray if(len(num) >= 1)]


    if(formats['DD/MM/YY'] == dateFormat):
        
        day = dateInt[0]
        month = dateInt[1]
        year = dateInt[2]
        
        return day, month, year

    if(formats['YY/MM/DD'] == dateFormat):

        day = dateInt[2]
        month = dateInt[1]
        year = dateInt[0]
    
        return day, month, year


def extractDate(data, documentType):
    datePattern = r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b' 

    if(documentType == 'Pasaporte'):
        datePattern = r'\d{2}\s(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)/(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)\s\d{4}'

    datesFound = []
    
    for line in data:
        match = re.search(datePattern, line)
        if(match is not None):
            matchString = match.string
            dateString = matchString[match.start():match.end()]
            datesFound.append(dateString)

    return datesFound

monthDict = {
        'ENE':'01',
        'FEB':'02',
        'MAR':'03',
        'ABR':'04',
        'MAY':'05',
        'JUN':'06',
        'JUL':'07',
        'AGO':'08',
        'SEP':'09',
        'OCT':'10',
        'NOV':'11',
        'DIC':'12',
}
# def dateFormatter(dates):
#     monthPattern = r'(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)/(?:ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC)'


#     datesFound = []

#     for date in dates:
#         match = re.search(monthPattern, date)
#         if(match is not None):
#             matchStart = match.start()
#             matchEnd = match.end()
#             matchString = match.string
#             matchLength = len(matchString)
#             monthString = matchString[matchStart:matchEnd]
#             monthSplitted = monthString.split('/')
#             monthExtracted = monthSplitted[0]
#             month = monthDict[monthExtracted]
#             day = matchString[0:matchStart]
#             year = matchString[matchEnd:matchLength]
#             date = f'{day}-{month}-{year}'
#             datesFound.append(date)

#     return datesFound

def dateCleaning(data, hasNamedMonths):

    print(data)

    if(not hasNamedMonths):
        multipleData = ' '.join(data).upper()
        if('/' in multipleData):
            multipleData = multipleData.replace('/', ' ')

        cleanedLetters = ''.join(char for char in multipleData if char.isdigit() or char.isspace())
        print(len(cleanedLetters), cleanedLetters)
        cleanedLetters = cleanedLetters.strip()
        print(len(cleanedLetters), cleanedLetters)
        date = cleanedLetters
        return date

    date = None

    for date in data:
        month_replaced = False
        for key, value in monthDict.items():
            if key in date:
                if not month_replaced:  
                    date = date.replace(key, value, 1) 
                    month_replaced = True
                if month_replaced:
                    date = date.replace(key, '', 1)

    cleanedLetters = ''.join(char for char in date if char.isdigit() or char.isspace())
    cleanedLetters = cleanedLetters.strip()
    date = cleanedLetters
    return date

def hasExpiryDate(documentType, documentSide, country):

    print(country)

    data = documentHash[country][documentType][documentSide]
    
    hasExpiry = data['hasExpiry']
    namedMonth = data['namedMonth']
    position = data['position']
    keyword = data['keyword']
    dateFormat = data['format']

    return hasExpiry, namedMonth, position, keyword, dateFormat

def expiryDateOCR(ocrData, datePosition, keywords, namedMonth, dateFormat):

    currentDate = datetime.date.today()

    reference = []

    for (coords, data, _) in ocrData:

        dataUpper = data.upper()
        if(len(dataUpper) >= 4):
            for word in keywords:
                if(word in dataUpper or dataUpper in word):
                    reference.append([coords, data])

    nearestDates = []
    min_distance = float('inf')

    if(len(reference) <= 0):
        return False

    reference = reference[0]

    for (coords, data, _) in ocrData:
        x, y = coords[0]
        if reference:
            refCoords, _ = reference
            rX, rY = refCoords[0]

            # agregar if dependiendo de la direccion (realiza un hash map como siempre)
            # cedulade extrajeria
            if(datePosition == 'right'):
                if x > rX:
                    distance = abs(x - rX) + abs(y - rY)
                    if distance < min_distance:
                        min_distance = distance
                        nearestDates = [data]
                    elif distance == min_distance:
                        nearestDates.append(data)

            if(datePosition == 'below'):
                if(namedMonth):
                    if y > rY:
                        distance = abs(x - rX) + abs(y - rY)
                        if distance < min_distance:
                            min_distance = distance
                            nearestDates = [data]
                        elif distance == min_distance:
                            nearestDates.append(data)
                else:
                    if y > rY or y > rY and x > rX:
                        nearestDates.append(data)


    if(len(nearestDates) <= 0):
        print('no se pudo detectar la fecha de expiracion')
        return True

    cleanedDate = dateCleaning(nearestDates, namedMonth)
    day, month, year = dateFormatter(cleanedDate,dateFormat)

    try:
        convertedDate = datetime.date(year, month, day)
        if convertedDate > currentDate:
            return False
        else:
            return True
    except ValueError as e: 
            return True
    print(cleanedDate)
    # dateFormatter()



#  for (coords, data, _) in ocrData:
#         x, y, w, h = coords
#         if reference:
#             ref_coords, _ = reference
#             rX, rY, rW, rH = ref_coords
#             if x > rX + rW and abs(y - rY) < h:
#                 print(f"({x}, {y}) está al lado derecho y verticalmente más cercano a la referencia ({rX}, {rY}, {rW}, {rH}), {data}")




    # extraction = extractDate(data=ocrData, documentType=documentType)

    # if(documentType == 'Pasaporte'):
    #     extraction = dateFormatter(extraction)

    # extractedDates = filter(lambda x: len(x) >= 1, extraction)

    # lowerDates = []
    # higherDates = []

    # for date in extractedDates:
    #     splitedDate = date.split('-')

    #     try:
    #         day, month, year = int(splitedDate[0]), int(splitedDate[1]), int(splitedDate[2])

    #         if 1 <= month <= 12:
    #             convertedDate = datetime.date(year, month, day)
    #             if convertedDate > currentDate:
    #                 higherDates.append(convertedDate)
    #             else:
    #                 lowerDates.append(convertedDate)
    #         else: 
    #             raise ValueError("Month must be in 1..12") 
    #     except ValueError as e: 
    #         return True

    # return False if(len(higherDates) >= 1) else True
