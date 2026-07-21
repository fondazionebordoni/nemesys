# -*- coding: utf-8 -*-
# freeze script for py2exe on Windows (API py2exe>=0.14, no piu' distutils)
#
import os
import re
import sys

from py2exe import freeze

sys.path.append(os.path.join('.', 'nemesys'))
sys.path.append(os.path.join('.', 'common'))


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


freeze(
    service=[{
        # used for the versioninfo resource
        'description': 'Nemesys Service',
        # what to build.  For a service, the module name (not the
        # filename) must be specified!
        'modules': ['nemesys.Nemesys'],
        'icon_resources': [(1, '.\\icons\\nemesys.ico')],
        'cmdline_style': 'pywin32',
    }],
    windows=[{
        'script': os.path.join('nemesys', 'login.py'),
        'uac_info': 'requireAdministrator',
        'icon_resources': [(1, '.\\icons\\nemesys.ico')],
    }],
    version_info={
        'version': get_version(),
        'company_name': 'Fondazione Ugo Bordoni',
        'copyright': '(c)2010-2017 Fondazione Ugo Bordoni',
    },
    options={
        'packages': ['encodings', 'common', 'nemesys', 'charset_normalizer'],
        'includes': ['_cffi_backend'],
        'optimize': 2,
    },
)
