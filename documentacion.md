# Explicacion de las rutas

## Rutas ocr

### /ocr-anverso

metodo http: POST

la ruta ocr-anverso, realiza una validacion de la parte frontal de los documentos enviados a la ruta en cuestion. 

Primero, se realiza una deteccion de rostros en el documento, junto a esta rotacion se va ejecutando la rotacion del documento en caso de no conseguir ningun rostro.

Segundo, se valida el lado del documento por medio de OCR para evitar posibles errores de parte del usuario. La validacion se realiza dos veces, la primera vez, se realiza sin preprocesado y la segunda se realiza con preprocesado, de esta forma, conseguimos mas exactitud en la extraccion de la informacion.

Tercero, se realiza el ocr sencillo(sin pre procesado) y despues se realiza con el preprocesado por los mismos motivos mencionados en el punto anterior.

Cuarto, por ultimo se valida la informacion extraida del OCR contra la informacion traida del usuario traida desde el frontend, sacando los porcentajes y la data respectiva de cada validacion de la informacion. Sacando un aproximado(comparado) entre los datos extraidos por medio del ocr.

la respuesta retornada por esta ruta es la siguienta:

{
  'ocr': {
    'nombreOCR': nombreComparado,
    'apellidoOCR': apellidoComparado,
    'documentoOCR': documentoComparado
  },
  'porcentajes': {
    'porcentajeNombreOCR': porcentajeNombreComparado,
    'porcentajeApellidoOCR': porcentajeApellidoComparado,
    'porcentajeDocumentoOCR': porcentajeDocumentoComparado
  },
  'rostro': coincidencia,
  'ladoValido': ladoValido
}

### /ocr-reverso

metodo http: POST

A pesar de ser parecidas, esta ruta es un poco menos compleja, debido a que los documentos en el reverso, no contienen informacion que sea suministrada por el frontend, por lo tanto solo se realiza la validacion del lado. Aun se sigue buscando servicios que nos permitan leer el codigo de barras por lo tanto, es un punto a mejorar a futuro.

Primero, validacion del reverso por medio del ocr para determinar si el usuario ha pasado el lado correcto del documento.

la respuesta retornada por esta ruta es la siguiente:

{
  "codigoBarra":{
    'reconocido': 'false',
    'nombre':'false',
    'apellido':'false',
    'documento':'false'
  },
  'ladoValido': ladoValido
}