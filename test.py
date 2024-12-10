import pytesseract as tess
import cv2
import numpy as np

tess.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def ocr(imagenPath: str, preprocesado):
    
    imagen = cv2.imread(imagenPath)

    if(preprocesado == False):
        txt: str = tess.image_to_string(imagen)
        lineas: list[str] = txt.splitlines()
        print('no preprocesado', lineas)
        
        cv2.imshow('Original Image', imagen) 
        cv2.waitKey(0) 
        cv2.destroyAllWindows()
        
        return lineas

    if(preprocesado):

        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

        kernel = np.array([[0, -1, 0], [-1, 5,-1], [0, -1, 0]]) 
        sharpened = cv2.filter2D(gris, -1, kernel)

        invertedImage = cv2.bitwise_not(sharpened)

        enhancedImage = cv2.convertScaleAbs(invertedImage, alpha=1.0, beta=-25)

        _, otsu = cv2.threshold(enhancedImage, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
        opened = cv2.morphologyEx(otsu, cv2.MORPH_RECT, kernel, iterations=1) 

        txt: str = tess.image_to_string(enhancedImage)

        lineas: list[str] = txt.splitlines()
        print('preprocesado', lineas)

        # cv2.imshow('Grayscale Image', gris) 
        # cv2.imshow('contore Image', invertedImage)
        # cv2.imshow('sapoora Image', threshold) 
        # cv2.imshow('blur Image', sharpened) 
        cv2.imshow('thres Image', opened) 
        # cv2.imshow('opened Image', opened) 
        # cv2.imshow('contrast Image', contrast) 
        cv2.waitKey(0) 
        cv2.destroyAllWindows()
        return lineas

ocr('../fotos-prueba/test - Copie.jpeg', True)
# ocr('../fotos-prueba/download.jpg', True)