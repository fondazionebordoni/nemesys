# -*- coding: utf-8 -*-
# setup for py2exe on Windows
#
import os
import py2exe  # noqa
import re
import sys
from distutils.core import setup
from glob import glob

sys.path.append('C:\\Microsoft.VC90.CRT')
sys.path.append(os.path.join('.', 'mist'))
sys.path.append(os.path.join('.', 'nemesys'))
sys.path.append(os.path.join('.', 'common'))

data_files = [('Microsoft.VC90.CRT', glob(r'C:\Microsoft.VC90.CRT\*.*'))]


def get_version():
    try:
        f = open(os.path.join('common', '_generated_version.py'))
    except EnvironmentError:
        return None
    ver = None
    for line in f.readlines():
        mo = re.match("__version__ = '([^']+)'", line)
        if mo:
            ver = mo.group(1)
            break

    # Fix version in Inno Setup file too!
    sub_iss_file(os.path.join('.', 'mist.iss'), ver)
    sub_iss_file(os.path.join('.', 'nemesys.iss'), ver)

    return ver


def sub_iss_file(f, ver):
    # Fix version in Inno Setup file too!
    with open(f, 'r') as fd:
        filedata = fd.read()

    # Replace the target string
    if '@version@' in filedata:
        filedata = filedata.replace('@version@', ver)

    # Write the file out again
    with open(f, 'w') as fd:
        fd.write(filedata)


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = get_version()
        self.company_name = 'Fondazione Ugo Bordoni'
        self.copyright = '(c)2010-2017 Fondazione Ugo Bordoni'
        # self.name = "MisuraInternet Speed Test"

nemesys_service = Target(
    # used for the versioninfo resource
    description='Nemesys Service',
    # what to build.  For a service, the module name (not the
    # filename) must be specified!
    modules=['nemesys.Nemesys'],
    icon_resources=[(1, '.\\nemesys.ico')],
    cmdline_style='pywin32',
    name='Nemesys'
    )


setup(
    data_files=data_files,
    options={
        'py2exe': {
            'packages': 'encodings',
            'optimize': 2,
        }
    },
    version=get_version(),
    service=[nemesys_service],
    windows=[
        {'name': 'MisuraInternet Speed Test',
         'script': '.\mist\mist.py',
         'uac_info': 'requireAdministrator',
         'icon_resources': [(1, '.\\mist.ico')]},
        {'name': 'Nemesys login',
         'script': os.path.join('nemesys', 'login.py'),
         'uac_info': 'requireAdministrator',
         'icon_resources': [(1, '.\\nemesys.ico')]}
    ],
)
