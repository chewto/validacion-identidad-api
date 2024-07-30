import json

from ocr import extraerPorcentaje

validationDataRaw = '{"validation_m2":{"standard_fields":{"test_date_of_expiry":"OK","test_side_correspondence":"FAIL","test_global_authenticity_ratio":0.99,"test_global_authenticity_value":"OK"},"test_date_of_expiry":"OK","test_side_correspondence":"FAIL","test_image_focus":"FAIL","test_global_authenticity_value":"OK","test_image_glares":"OK","test_global_authenticity_ratio":0.99},"ocr_m2":{"standard_fields":{"surname":["LCZADASALAR"],"date_of_expiry_viz":"2033-06-30","issuing_state_code_viz":"VEN","surname_viz":["LCZADASALAR"],"document_info":[{"icao_code":"VEN","description":"IdentityCard","type":12}],"name":"JESUS ENRIDUE","issuing_state_code":"VEN","document_number_viz":"V30205611","name_viz":"JESUS ENRIDUE","document_number":"V30205611","date_of_expiry":"2033-06-30","sides_number":"2"},"date_of_issue":"05/06/2023","years_since_issue_viz":"1","remainder_term_viz":"107","issuing_state_name_viz":"Venezuela, Bolivarian Republic of","given_names_viz":"JESUS ENRIDUE","surname_and_given_names":"LCZADASALAR JESUS ENRIDUE","remainder_term":"107","document_number":"V30205611","issuing_state_code":"VEN","sides_number":"2","surname_and_given_names_viz":"LCZADASALAR JESUS ENRIDUE","issuing_state_name":"Venezuela, Bolivarian Republic of","date_of_birth":"13/032002 OLTERO","surname":"LCZADASALAR","years_since_issue":"1","given_names":"JESUS ENRIDUE","date_of_expiry_viz":"30/06/2033","issuing_state_code_viz":"VEN","date_of_issue_viz":"05/06/2023","surname_viz":"LCZADASALAR","date_of_birth_viz":"13/032002 OLTERO","date_of_expiry":"30/06/2033","document_number_viz":"V30205611","document_types_candidates":[{"icao_code":"VEN","type":12,"year":"2010","name":"Venezuela, Bolivarian Republic of - Id Card (2010)","probability":0.711756348609924,"mrz":0,"country_name":"Venezuela, Bolivarian Republic of"}]},"face_m4":{"standard_fields":{"test_face_recognition_ratio":0.82465},"confidence":{"is_identical":0,"confidence":0.82465},"image2_data":{"face_attributes":{"noise":{"noise_level":"low","value":0.27},"blur":{"blur_level":"medium","value":0.34},"head_pose":{"pitch":-4,"roll":2.5,"yaw":-1},"accessories":[{"confidence":1,"type":"glasses"}],"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"exposure":{"exposure_level":"goodExposure","value":0.34},"glasses":"ReadingGlasses"},"face_rectangle":{"width":231,"left":185,"height":231,"top":144},"face_landmarks":{"eye_right_outer":{"x":365.7,"y":206.1},"eyebrow_right_inner":{"x":318.8,"y":175.3},"eye_left_inner":{"x":266.5,"y":204.9},"under_lip_top":{"x":302,"y":328.6},"eye_left_top":{"x":251.8,"y":197.7},"eyebrow_right_outer":{"x":385.2,"y":179.2},"eyebrow_left_inner":{"x":282,"y":172},"nose_root_left":{"x":288.7,"y":206.7},"nose_root_right":{"x":318.4,"y":206.7},"upper_lip_top":{"x":303.3,"y":303.3},"pupil_left":{"x":252.7,"y":203.9},"eyebrow_left_outer":{"x":210.8,"y":184.4},"nose_left_alar_out_tip":{"x":270.8,"y":269.4},"mouth_left":{"x":257.3,"y":318},"upper_lip_bottom":{"x":302.9,"y":312.6},"nose_left_alar_top":{"x":281.6,"y":244.3},"nose_right_alar_out_tip":{"x":333.7,"y":268.7},"nose_tip":{"x":303.8,"y":261.3},"mouth_right":{"x":339.4,"y":319},"eye_right_top":{"x":350.8,"y":198.9},"eye_right_inner":{"x":336.6,"y":205.9},"nose_right_alar_top":{"x":323.4,"y":243.4},"pupil_right":{"x":348.5,"y":204.7},"eye_left_outer":{"x":237.8,"y":204.3},"under_lip_bottom":{"x":302.3,"y":343.2},"eye_left_bottom":{"x":251.4,"y":209.9},"eye_right_bottom":{"x":350.5,"y":211.5}}},"image1_data":{"face_attributes":{"noise":{"noise_level":"medium","value":0.67},"blur":{"blur_level":"high","value":1},"head_pose":{"pitch":1,"roll":2.9,"yaw":-0.8},"accessories":[],"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"exposure":{"exposure_level":"goodExposure","value":0.51},"glasses":"NoGlasses"},"face_rectangle":{"width":221,"left":97,"height":221,"top":135},"face_landmarks":{"eye_right_outer":{"x":266.1,"y":194.7},"eyebrow_right_inner":{"x":230.8,"y":167.2},"eye_left_inner":{"x":173.9,"y":193.9},"under_lip_top":{"x":209,"y":308.6},"eye_left_top":{"x":158.7,"y":188.2},"eyebrow_right_outer":{"x":287.1,"y":171},"eyebrow_left_inner":{"x":192.1,"y":168.2},"nose_root_left":{"x":192.2,"y":197.3},"nose_root_right":{"x":220.2,"y":197.4},"upper_lip_top":{"x":207.3,"y":289.7},"pupil_left":{"x":160.6,"y":193.1},"eyebrow_left_outer":{"x":123,"y":176.3},"nose_left_alar_out_tip":{"x":177,"y":254},"mouth_left":{"x":170.1,"y":304.9},"upper_lip_bottom":{"x":207.5,"y":298.1},"nose_left_alar_top":{"x":188,"y":234},"nose_right_alar_out_tip":{"x":237.8,"y":252.2},"nose_tip":{"x":211,"y":245.9},"mouth_right":{"x":243.9,"y":303.3},"eye_right_top":{"x":252.4,"y":188.2},"eye_right_inner":{"x":237.9,"y":193.5},"nose_right_alar_top":{"x":229.3,"y":234},"pupil_right":{"x":252,"y":192.4},"eye_left_outer":{"x":142.8,"y":194.2},"under_lip_bottom":{"x":209.6,"y":321.9},"eye_left_bottom":{"x":158.1,"y":201},"eye_right_bottom":{"x":252.6,"y":199.8}}}}}'

dataDict = json.loads(validationDataRaw)

data = {

}

face = dataDict['face_m4']['standard_fields']

ocr = dataDict['ocr_m2']['standard_fields']

validationExtra = dataDict['validation_m2']['standard_fields']

if('test_face_recognition_ratio' in face):

  data['faceData'] = 'Verificado' if face['test_face_recognition_ratio'] >= 0.5 else 'Pendiente revisión'
else:
  data['faceData'] = 'Pendiente revisión'

if('name' in ocr):

  OCRname:str = ocr['name']
  OCRname = OCRname.lower()

  name = 'Jesus enrique'
  name = name.lower()

  coincidence = extraerPorcentaje(OCRname, name)

  data['name'] = {
    "ocrData": OCRname,
    "ocrPercent": coincidence
  }

else:
  data['name'] = {
    "ocrData": '',
    "ocrPercent": 0
  }

if('surname' in ocr):

  OCRsurnames = ocr['surname']

  normalizeSurname = ''

  if(len(OCRsurnames) >= 1):
    for surname in OCRsurnames:
      surnameLower:str = surname.lower()
      normalizeSurname += f"{surnameLower} "

  OCRsurname = normalizeSurname.strip()

  surname = 'Lozada Salazar'
  surnama = surname.lower()

  coincidence = extraerPorcentaje(OCRsurname,surname)

  data['surname'] = {
    "ocrData": OCRsurname,
    "ocrPercent": coincidence
  }

else:
  data['surname'] = ''

if('document_number' in ocr):
  OCRdocument = ocr['document_number']
  document = '30265611'

  coincidence = extraerPorcentaje(OCRdocument, document)

  data['document'] = {
    'ocrData': OCRdocument,
    'ocrPercent': coincidence
  }
else:
  data['document'] = ''

if('test_global_authenticity_value' in validationExtra):
  aunthenticity = validationExtra['test_global_authenticity_value']

  data['authenticity'] = aunthenticity
else:
  data['authenticity'] = ''

print(data)