import face_recognition
import controlador_db
import io


def reconocerRostro(imgPersona, imgDocumento):


    cargarImg = face_recognition.load_image_file(imgPersona)
    reconocerImagen = face_recognition.face_encodings(cargarImg)
    if len(reconocerImagen) == 0:
        return False,'pendiente revision'
    else:
        reconocerImagen = reconocerImagen[0]

    reconocido = False

    cargarImgComparar = face_recognition.load_image_file(imgDocumento)
    reconocerImagenComparar = face_recognition.face_encodings(cargarImgComparar)

    if len(reconocerImagenComparar) == 0:
      return False, 'pendiente revision'
    else:
      reconocerImagenComparar = reconocerImagenComparar[0]

    reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

    reconocido = reconocido[0]

    if reconocido:
        return True, 'verificado'
    else:
        return False, 'pendiente revision'


# def reconocerRostro(img, tabla):

#     filas = controlador_db.obtenerTodos(tabla)

#     cargarImg = face_recognition.load_image_file(img)
#     reconocerImagen = face_recognition.face_encodings(cargarImg)
#     if len(reconocerImagen) == 0:
#         return 'no se encontro ninguna persona', False
#     else:
#         reconocerImagen = reconocerImagen[0]

#     reconocido = False
#     nombre = ''
#     vueltas = 0

#     nombres = []
#     imagenes = []

#     for row in filas:
#         b = io.BytesIO(row[1])
#         imagenes.append(b)
#         # nombre = row[1]
#         # apellido = row[2]
#         # nombreCompleto = f"{nombre} {apellido}"
#         # nombres.append(nombreCompleto)

#     dbData = [imagen for imagen in imagenes]

#     while ((not reconocido) and (vueltas < len(dbData))):
#         imagenComparar = imagenes[vueltas]

#         # nombreUsuario = nombres[vueltas]


#         cargarImgComparar = face_recognition.load_image_file(imagenComparar)
#         reconocerImagenComparar = face_recognition.face_encodings(cargarImgComparar)

#         if len(reconocerImagenComparar) == 0:
#             return 'no se ha reconocido a una persona'
#         else:
#             reconocerImagenComparar = reconocerImagenComparar[0]

#         reconocido = face_recognition.compare_faces([reconocerImagenComparar], reconocerImagen)

#         reconocido = reconocido[0]

#         vueltas+= 1

#     if reconocido:
#         return 'reconocido', True
#     else:
#         return 'no reconocido', False