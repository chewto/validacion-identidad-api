import os
import string
import urllib
import uuid
import pickle
import datetime
import time
import shutil

import cv2
from fastapi import FastAPI, File, UploadFile, Form, UploadFile, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import face_recognition
import starlette
from pydantic import BaseModel
import requests
import sqlite3


ATTENDANCE_LOG_DIR = './logs'
DB_PATH = './db'
for dir_ in [ATTENDANCE_LOG_DIR, DB_PATH]:
    if not os.path.exists(dir_):
        os.mkdir(dir_)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/login")
async def login(file: UploadFile = File(...)):

    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()

    # example of how you can save the file
    with open(file.filename, "wb") as f:
        f.write(contents)

    user_name, match_status = recognize(file.filename)

    if match_status:
        epoch_time = time.time()
        date = time.strftime('%Y%m%d', time.localtime(epoch_time))
        with open(os.path.join(ATTENDANCE_LOG_DIR, '{}.csv'.format(date)), 'a') as f:
            f.write('{},{},{}\n'.format(user_name, datetime.datetime.now(), 'IN'))
            f.close()

    return {'user': user_name, 'match_status': match_status}


@app.post("/logout")
async def logout(file: UploadFile = File(...)):

    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()

    # example of how you can save the file
    with open(file.filename, "wb") as f:
        f.write(contents)

    user_name, match_status = recognize(cv2.imread(file.filename))

    if match_status:
        epoch_time = time.time()
        date = time.strftime('%Y%m%d', time.localtime(epoch_time))
        with open(os.path.join(ATTENDANCE_LOG_DIR, '{}.csv'.format(date)), 'a') as f:
            f.write('{},{},{}\n'.format(user_name, datetime.datetime.now(), 'OUT'))
            f.close()

    return {'user': user_name, 'match_status': match_status}

@app.post("/register_new_user")
async def register_new_user(file: UploadFile = File(...), text=None):
    file.filename = f"{uuid.uuid4()}.png"
    contents = await file.read()

    # example of how you can save the file
    with open(file.filename, "wb") as f:
        f.write(contents)

    shutil.copy(file.filename, os.path.join(DB_PATH, '{}.png'.format(text)))

    embeddings = face_recognition.face_encodings(cv2.imread(file.filename))

    file_ = open(os.path.join(DB_PATH, '{}.pickle'.format(text)), 'wb')
    pickle.dump(embeddings, file_)
    print(file.filename, text)

    os.remove(file.filename)

    return {'registration_status': 200}

@app.get("/get_attendance_logs")
async def get_attendance_logs():

    filename = 'out.zip'

    shutil.make_archive(filename[:-4], 'zip', ATTENDANCE_LOG_DIR)

    ##return File(filename, filename=filename, content_type="application/zip", as_attachment=True)
    return starlette.responses.FileResponse(filename, media_type='application/zip',filename=filename)

def recognize(img):
    # it is assumed there will be at most 1 match in the db
    image = face_recognition.load_image_file(img)
    embeddings_unknown = face_recognition.face_encodings(image)
    if len(embeddings_unknown) == 0:
        print('no reconocido')
        return 'no_persons_found', False
    else:
        embeddings_unknown = embeddings_unknown[0]

    match = False
    nombre = ''
    j = 0

    db_dir = sorted([j for j in os.listdir(DB_PATH) if j.endswith('.png') or j.endswith('.jpg')])

    print(db_dir)
    while ((not match) and (j < len(db_dir))):
        path_ = os.path.join(DB_PATH, db_dir[j])

        print(path_)

        loadImage = face_recognition.load_image_file(path_)
        compareImage = face_recognition.face_encodings(loadImage)

        if len(compareImage) == 0:
            return 'no se ha reconocido a una persona'
        else:
            compareImage = compareImage[0]

        match = face_recognition.compare_faces([compareImage], embeddings_unknown)

        match = match[0]

        if match:
            nombre = db_dir[j]
            nombre = nombre.replace('.jpg', '')
        else:
            nombre = ''

        j+= 1

    if match:
        print('reconocido', nombre)
        return nombre, True
    else:
        print('no reconocido')
        return 'no reconocido', False

# python3 -m uvicorn main:app