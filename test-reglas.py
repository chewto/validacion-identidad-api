import base64
import json

validation_info = "eyJ2YWxpZGF0aW9uX20yIjp7InN0YW5kYXJkX2ZpZWxkcyI6eyJ0ZXN0X2dsb2JhbF9hdXRoZW50aWNpdHlfcmF0aW8iOjAuOTksInRlc3RfZ2xvYmFsX2F1dGhlbnRpY2l0eV92YWx1ZSI6Ik9LIiwidGVzdF9kYXRlX29mX2V4cGlyeSI6Ik9LIiwidGVzdF9zaWRlX2NvcnJlc3BvbmRlbmNlIjoiRkFJTCJ9LCJ0ZXN0X2dsb2JhbF9hdXRoZW50aWNpdHlfdmFsdWUiOiJPSyIsInRlc3RfZ2xvYmFsX2F1dGhlbnRpY2l0eV9yYXRpbyI6MC45OSwidGVzdF9kYXRlX29mX2V4cGlyeSI6Ik9LIiwidGVzdF9pbWFnZV9mb2N1cyI6IkZBSUwiLCJ0ZXN0X3NpZGVfY29ycmVzcG9uZGVuY2UiOiJGQUlMIn0sIm9jcl9tMiI6eyJpc3N1aW5nX3N0YXRlX25hbWVfdml6IjoiVmVuZXp1ZWxhLCBCb2xpdmFyaWFuIFJlcHVibGljIG9mIiwiZG9jdW1lbnRfbnVtYmVyX3ZpeiI6IlYzMDI2NTYxMSIsImRvY3VtZW50X3R5cGVzX2NhbmRpZGF0ZXMiOlt7InR5cGUiOjEyLCJtcnoiOjAsImNvdW50cnlfbmFtZSI6IlZlbmV6dWVsYSwgQm9saXZhcmlhbiBSZXB1YmxpYyBvZiIsImljYW9fY29kZSI6IlZFTiIsInByb2JhYmlsaXR5IjowLjc3MzQ0ODEwOTYyNjc3LCJuYW1lIjoiVmVuZXp1ZWxhLCBCb2xpdmFyaWFuIFJlcHVibGljIG9mIC0gSWQgQ2FyZCAoMjAxMCkiLCJ5ZWFyIjoiMjAxMCJ9XSwic3VybmFtZV9hbmRfZ2l2ZW5fbmFtZXNfdml6IjoiTE9aQURBU0FMQVpSIiwiaXNzdWluZ19zdGF0ZV9jb2RlX3ZpeiI6IlZFTiIsInJlbWFpbmRlcl90ZXJtX3ZpeiI6IjEwNSIsImRhdGVfb2ZfaXNzdWVfdml6IjoiMDUvMDYvMjAyMyIsInNpZGVzX251bWJlciI6IjIiLCJzdXJuYW1lX2FuZF9naXZlbl9uYW1lcyI6IkxPWkFEQVNBTEFaUiIsImRvY3VtZW50X251bWJlciI6IlYzMDI2NTYxMSIsImRhdGVfb2ZfYmlydGgiOiIxNS8wMzIwMDIgU09MVEVSTyIsImRhdGVfb2ZfZXhwaXJ5X3ZpeiI6IjMwLzA2LzIwMzMiLCJzdGFuZGFyZF9maWVsZHMiOnsiZGF0ZV9vZl9leHBpcnkiOiIyMDMzLTA2LTMwIiwiaXNzdWluZ19zdGF0ZV9jb2RlIjoiVkVOIiwic3VybmFtZV92aXoiOlsiTE9aQURBU0FMQVpSIl0sImRvY3VtZW50X251bWJlcl92aXoiOiJWMzAyNjU2MTEiLCJzdXJuYW1lIjpbIkxPWkFEQVNBTEFaUiJdLCJpc3N1aW5nX3N0YXRlX2NvZGVfdml6IjoiVkVOIiwic2lkZXNfbnVtYmVyIjoiMiIsImRvY3VtZW50X251bWJlciI6IlYzMDI2NTYxMSIsImRvY3VtZW50X2luZm8iOlt7InR5cGUiOjEyLCJkZXNjcmlwdGlvbiI6IklkZW50aXR5Q2FyZCIsImljYW9fY29kZSI6IlZFTiJ9XSwiZGF0ZV9vZl9leHBpcnlfdml6IjoiMjAzMy0wNi0zMCJ9LCJkYXRlX29mX2V4cGlyeSI6IjMwLzA2LzIwMzMiLCJpc3N1aW5nX3N0YXRlX2NvZGUiOiJWRU4iLCJyZW1haW5kZXJfdGVybSI6IjEwNSIsInN1cm5hbWVfdml6IjoiTE9aQURBU0FMQVpSIiwic3VybmFtZSI6IkxPWkFEQVNBTEFaUiIsImlzc3Vpbmdfc3RhdGVfbmFtZSI6IlZlbmV6dWVsYSwgQm9saXZhcmlhbiBSZXB1YmxpYyBvZiIsInllYXJzX3NpbmNlX2lzc3VlIjoiMSIsImRhdGVfb2ZfaXNzdWUiOiIwNS8wNi8yMDIzIiwieWVhcnNfc2luY2VfaXNzdWVfdml6IjoiMSIsImRhdGVfb2ZfYmlydGhfdml6IjoiMTUvMDMyMDAyIFNPTFRFUk8ifSwiZmFjZV9tNCI6eyJzdGFuZGFyZF9maWVsZHMiOnt9fX0="
validation_check = "eyJyZXN1bHRDb2RlIjozLCJ2YWxpZGF0aW9uUmVzdWx0IjpbXX0="

data = '{"face_m4":{"image1_data":{"face_attributes":{"exposure":{"exposure_level":"goodExposure","value":0.71},"noise":{"value":0.35,"noise_level":"medium"},"blur":{"blur_level":"medium","value":0.37},"accessories":[],"head_pose":{"yaw":5,"pitch":-65.9,"roll":-8.7},"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"glasses":"NoGlasses"},"face_landmarks":{"nose_tip":{"y":170.4,"x":134.5},"nose_left_alar_top":{"y":157.8,"x":122.7},"nose_left_alar_out_tip":{"y":168.9,"x":115.1},"mouth_right":{"y":206.1,"x":167.1},"mouth_left":{"y":207.6,"x":111.5},"eye_left_outer":{"y":132,"x":94.6},"eyebrow_left_outer":{"y":114.8,"x":77.2},"eye_right_inner":{"y":131.3,"x":158.4},"pupil_right":{"y":129.5,"x":168.6},"eye_right_outer":{"y":129.7,"x":179.3},"upper_lip_top":{"y":198.2,"x":136.7},"eyebrow_right_inner":{"y":111.5,"x":150.2},"eye_right_top":{"y":124.4,"x":168.8},"eyebrow_left_inner":{"y":110.8,"x":118},"eye_left_top":{"y":125.1,"x":104.5},"eyebrow_right_outer":{"y":111.3,"x":196.1},"eye_left_inner":{"y":131.6,"x":114.8},"pupil_left":{"y":130.6,"x":105.5},"nose_root_left":{"y":134.2,"x":125.5},"eye_left_bottom":{"y":135.9,"x":104.3},"under_lip_bottom":{"y":229.2,"x":137.1},"nose_right_alar_top":{"y":157.9,"x":149.2},"nose_right_alar_out_tip":{"y":168.6,"x":156.5},"eye_right_bottom":{"y":134.9,"x":169.5},"under_lip_top":{"y":219.1,"x":137.3},"nose_root_right":{"y":134.1,"x":145.5},"upper_lip_bottom":{"y":205,"x":137}},"face_rectangle":{"top":90,"height":155,"left":60,"width":155}},"standard_fields":{"test_face_recognition_ratio":0.81886},"confidence":{"is_identical":0,"confidence":0.81886},"image2_data":{"face_attributes":{"exposure":{"exposure_level":"goodExposure","value":0.49},"noise":{"value":0.08,"noise_level":"low"},"blur":{"blur_level":"medium","value":0.32},"accessories":[],"head_pose":{"yaw":-0.1,"pitch":-3.9,"roll":0.5},"occlusion":{"eye_occluded":0,"mouth_occluded":0,"forehead_occluded":0},"glasses":"NoGlasses"},"face_landmarks":{"nose_tip":{"y":284.9,"x":324.9},"nose_left_alar_top":{"y":266.6,"x":305.3},"nose_left_alar_out_tip":{"y":287.2,"x":295.6},"mouth_right":{"y":340.3,"x":374.5},"mouth_left":{"y":339.7,"x":284.6},"eye_left_outer":{"y":230.8,"x":265.1},"eyebrow_left_outer":{"y":217.5,"x":244.2},"eye_right_inner":{"y":228.6,"x":357.2},"pupil_right":{"y":228.8,"x":374.2},"eye_right_outer":{"y":228.2,"x":388.6},"upper_lip_top":{"y":326.7,"x":328.5},"eyebrow_right_inner":{"y":207.2,"x":342.2},"eye_right_top":{"y":221.9,"x":372.5},"eyebrow_left_inner":{"y":208.2,"x":305.7},"eye_left_top":{"y":223.8,"x":279.5},"eyebrow_right_outer":{"y":209.1,"x":408},"eye_left_inner":{"y":229.2,"x":293.8},"pupil_left":{"y":230.5,"x":280.4},"nose_root_left":{"y":229.6,"x":311.2},"eye_left_bottom":{"y":235.7,"x":280.1},"under_lip_bottom":{"y":359.1,"x":333},"nose_right_alar_top":{"y":266.6,"x":345.5},"nose_right_alar_out_tip":{"y":287.5,"x":358.1},"eye_right_bottom":{"y":234.9,"x":374.5},"under_lip_top":{"y":344.7,"x":331.1},"nose_root_right":{"y":228.6,"x":340.5},"upper_lip_bottom":{"y":336.9,"x":328.9}},"face_rectangle":{"top":168,"height":229,"left":213,"width":229}}},"ocr_m2":{"surname_and_given_names_mrz":"QTERO CARREIRA BENITO","given_names":"BENITo","date_of_birth":"21/08/1972","surname_and_given_names_viz":"OTERO CARREIRA BENITo","mrz_type":"ID-1","date_of_birth_viz":"21/06/1972","mrz_type_mrz":"ID-1","document_class_code_mrz":"I","date_of_issue":"02/08/2021","final_check_digit_mrz":"0","age_at_issue_viz":"49","final_check_digit":"0","mrz_strings_mrz":"I<<BL423105<<<9<<<<<<<<<<<<<<<^7208218M2407290ESP<<<<<<<<<<<0^QTERO<CARREIRA<<BENITO<<<<<<<<","surname_viz":"OTERO CARREIRA","surname":"OTERO CARREIRA","nationality":"Spain","document_types_candidates":[{"icao_code":"COL","type":22,"probability":0.875918090343475,"mrz":0,"year":"2017","country_name":"Colombia","name":"Colombia - Alien Id Card (2017)"}],"age_viz":"52","given_names_viz":"BENITo","date_of_expiry_viz":"29/07/2024","date_of_birth_mrz":"21/08/1972","document_number_viz":"423105","issuing_state_code_mrz":"BL","nationality_code":"ESP","age_mrz":"52","issuing_state_name_mrz":"Saint Barthelemy","nationality_code_mrz":"ESP","remainder_term_mrz":"0","sides_number":"3","date_of_issue_viz":"02/08/2021","given_names_mrz":"BENITO","sex":"M","surname_and_given_names_transliteration_viz":"OTERO CARREIRA BENITO","document_number_mrz":"423105","age_at_issue":"49","remainder_term":"0","blood_group":"A","sex_viz":"M","standard_fields":{"nationality":"ESP","sex":"M","document_info":[{"description":"AliensIdentityCard","icao_code":"COL","type":22}],"date_of_expiry":"2024-07-29","document_number_mrz":"423105","document_number":"423105","date_of_expiry_viz":"2024-07-29","date_of_birth_mrz":"1972-08-21","document_number_viz":"423105","date_of_birth":"1972-08-21","sex_viz":"M","name_mrz":"BENITO","mrz":["I<<BL423105<<<9<<<<<<<<<<<<<<<","7208218M2407290ESP<<<<<<<<<<<0","QTERO<CARREIRA<<BENITO<<<<<<<<"],"surname_mrz":["QTERO","CARREIRA"],"date_of_birth_viz":"1972-06-21","name":"BENITo","sides_number":"3","nationality_mrz":"ESP","sex_mrz":"M","date_of_expiry_mrz":"2024-07-29","name_viz":"BENITo","issuing_state_code_viz":"COL","surname":["OTERO","CARREIRA"],"surname_viz":["OTERO","CARREIRA"]},"date_of_birth_check_digit":"8","sex_mrz":"M","age":"52","nationality_mrz":"Spain","issuing_state_name_viz":"Colombia","document_class_code":"I","document_number_check_digit":"9","nationality_viz":"ESP","document_number_check_digit_mrz":"9","issuing_state_code_viz":"COL","blood_group_viz":"A","date_of_expiry":"29/07/2024","document_number":"423105","years_since_issue_viz":"3","given_names_transliteration_viz":"BENITO","surname_and_given_names":"QTERO CARREIRA BENITO","surname_mrz":"QTERO CARREIRA","date_of_expiry_check_digit":"0","date_of_birth_check_digit_mrz":"8","date_of_expiry_check_digit_mrz":"0","issuing_state_name":"Saint Barthelemy","date_of_expiry_mrz":"29/07/2024","mrz_strings":"I<<BL423105<<<9<<<<<<<<<<<<<<<^7208218M2407290ESP<<<<<<<<<<<0^QTERO<CARREIRA<<BENITO<<<<<<<<","issuing_state_code":"BL","years_since_issue":"3","remainder_term_viz":"0"},"validation_m2":{"test_correspondence_viz_mrz_date_of_expiry":"OK","test_global_authenticity_ratio":0.8156918,"test_global_authenticity_value":"DOUBTFUL","test_image_focus":"FAIL","test_correspondence_viz_mrz_sex":"OK","test_mrz_fields_integrity_date_of_expiry_check_digit":"OK","test_correspondence_viz_mrz_surname_and_given_names":"FAIL","test_correspondence_viz_mrz_remainder_term":"OK","test_mrz_fields_integrity_document_class_code":"OK","standard_fields":{"test_correspondence_viz_mrz_date_of_expiry":"OK","test_global_authenticity_ratio":0.8156918,"test_global_authenticity_value":"DOUBTFUL","test_correspondence_viz_mrz_sex":"OK","test_mrz_fields_integrity_date_of_expiry":"OK","test_mrz_global_integrity":"OK","test_correspondence_viz_mrz_date_of_birth":"FAIL","test_mrz_fields_integrity_date_of_birth":"OK","test_mrz_fields_integrity_document_number":"OK","test_correspondence_viz_mrz_document_number":"OK","test_date_of_expiry":"FAIL","test_correspondence_viz_mrz_surname":"FAIL","test_date_of_birth":"FAIL","test_correspondence_viz_mrz_name":"OK","test_side_correspondence":"FAIL"},"test_mrz_fields_integrity_document_number_check_digit":"OK","test_correspondence_viz_mrz_document_number":"OK","test_correspondence_viz_mrz_age":"OK","test_correspondence_viz_mrz_issuing_state_name":"FAIL","test_mrz_fields_integrity_sex":"OK","test_mrz_fields_integrity_issuing_state_code":"OK","test_mrz_fields_integrity_mrz_strings":"OK","test_correspondence_viz_mrz_issuing_state_code":"FAIL","test_image_glares":"OK","test_mrz_fields_integrity_date_of_expiry":"FAIL","test_correspondence_viz_mrz_date_of_birth":"FAIL","test_mrz_fields_integrity_final_check_digit":"OK","test_mrz_fields_integrity_date_of_birth":"OK","test_mrz_fields_integrity_document_number":"OK","test_correspondence_viz_mrz_given_names":"OK","test_mrz_fields_integrity_nationality_code":"OK","test_date_of_expiry":"FAIL","test_correspondence_viz_mrz_surname":"FAIL","test_side_correspondence":"FAIL","test_mrz_fields_integrity_date_of_birth_check_digit":"OK"}}'


def ekycRules(rulesDict):

  rulesData = []

  approvedRulesCount = 0
  deniedRulesCount = 0

  dataDictionary = json.loads(rulesDict)

  rules = dataDictionary['validation_m2']
  standardFields = rules['standard_fields']


  for key in standardFields:
    value = standardFields.get(key)

    if(isinstance(value, float)):
      floatValues = True if value >= 0.5 else False
      rulesData.append(floatValues)

    if(isinstance(value, str)):
      strValues = True if value == 'OK' else False
      rulesData.append(strValues)

  for rule in rulesData:
    if(rule):
      approvedRulesCount += 1
    else:
      deniedRulesCount += 1

  print(approvedRulesCount, deniedRulesCount)

  if(approvedRulesCount >= deniedRulesCount):
    return rules, True
  else:
    return rules, False
  
  # if(deniedRulesCount > approvedRulesCount):
  #   return rules, False



def decode(data):
  base64Decode = base64.b64decode(data)
  decodedData = base64Decode.decode("utf-8")

  print(decodedData)


test = ekycRules(data)
print(test)

