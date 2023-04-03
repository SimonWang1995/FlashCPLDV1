import subprocess
import os
import re
import json

def runcmd(cmd):
    subpro = subprocess.Popen(cmd, shell=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    stdout, stderr = subpro.communicate()
    if stderr:
        return (False, stderr)
    else:
        return (True, stdout)

def parser_ver(log):
    comp = re.compile('CPLD VERSION:(.*)')
    return comp.search(log).groups()[0].split()[-1]

def json_dump(file, data):
    with open(file, 'w') as fp:
        json.dump(data, fp)

def json_load(file):
    with open(file, 'r') as fp:
        data = json.load(fp)
        return data