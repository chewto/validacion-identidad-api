import subprocess
import os
import sys

args = []
args.append('./BarcodeReaderCLI')
args.append('-type=pdf417')
args.append('../fotos-prueba/reverso_documento.jpeg')
# args.append('@./brcli-example.config')  # Additional options and sources in configuration file

cp = subprocess.run(args, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
output=cp.stdout
error=cp.stderr

if output != "": print("STDOUT:\n" + output)
if error != "":  print("STDERR:\n" + error)
# print("RETURN CODE:"  + str(print(cp.returncode)))