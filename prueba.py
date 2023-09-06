from requests import get
import io
import face_recognition
import sqlite3
import base64
from PIL import Image


conn = sqlite3.connect('prueba.db')
cursor = conn.cursor()

def imato_to_blob(image):
  with open(image, "rb") as f:
    image_data = f.read()
    return image_data

nombreCompleto = 'BENITO OTERO'

blobAnverso = imato_to_blob('./BENITO OTERO CARREIRA anverso.png')
blobReverso = imato_to_blob('./BENITO OTERO CARREIRA reverso.png')

cursor.execute('INSERT INTO cedula_usuario (nombre_completo, anverso, reverso) VALUES (?,?,?)', (nombreCompleto, blobAnverso, blobReverso,))


conn.commit()
cursor.close()
conn.close()

# def descargarRecursos(url):
#   response = get(url, stream=True)
#   stream = io.BytesIO(response.content)

#   return stream, response.content

# data, reponseData = descargarRecursos('https://media.prod.metamap.com/file?location=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmaWxlTmFtZSI6ImUyZGZlNWVlLTQ3NWUtNDkxZi05YjU5LTkzZWFkOWZjZTQzYy5qcGVnIiwiZm9sZGVyIjoiZG9jdW1lbnQiLCJpYXQiOjE2OTM1OTMyMzEsImV4cCI6MTY5Mzg1MjQzMSwiYXVkIjoiYzkyNmQ1MDItYmEzYi00N2FhLTg0YjItZjJmZGNiODQxYjdlIn0.rhEiHogJ1-FfL2KT8Q8HqiBpHOdjdrTxfHxvhhasuZc')

# print(data, reponseData['code'])


