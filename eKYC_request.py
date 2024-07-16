import requests

urlVideoToken = 'https://ekycvideoapiwest-test.lleida.net/api/rest/auth/get_video_token'

def postRequest(url, headers, data):
  # res = requests.post(urlVideoToken, data=data, headers=headers)
  try:
    res = requests.post(url=url, json=data, headers=headers)
    return res.json()
  except requests.RequestException as e:
    print(e)