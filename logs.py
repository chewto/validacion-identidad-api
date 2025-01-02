import os
import datetime

def writeLogs(path, error):

  date = datetime.datetime.now()

  with open(path, 'a') as file:
    file.writelines(f'{date} | {error}\n')

def checkLogsFile():
  logsFolder = './logs'
  logsFolderExist = os.path.exists(logsFolder)
  logsFile = '/logs.txt'
  logsFileExist = os.path.exists(f'{logsFolder}{logsFile}')

  completePath = f'{logsFolder}{logsFile}'

  if(not logsFolderExist):
    os.mkdir(logsFolder)

  if(not logsFileExist):
    with open(completePath,'w') as file:
      file.write('init log')

  return completePath