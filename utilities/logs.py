import os
import datetime

def writeLogs(path, error):

  date = datetime.datetime.now()

  with open(path, 'a') as file:
    file.writelines(f'{date} | {error}\n')

def addLog(path, message):

  date = datetime.datetime.now()

  with open(path, 'a') as file:
    file.writelines(f'{date} | {message}\n')

def checkLogsFile():
  logsFolder = './Logs/ekyc'
  logsFolderExist = os.path.exists(logsFolder)
  logsFile = 'logs_python.txt'
  logsFilePath = os.path.join(logsFolder, logsFile)

  if not logsFolderExist:
    os.makedirs(logsFolder)

  if not os.path.exists(logsFilePath):
    with open(logsFilePath, 'w') as file:
      file.write('init log\n')

  return logsFilePath
