from distutils.core import setup
import py2exe
import re, sys
from xml.etree import ElementTree as ET
from glob import glob

sys.path.append("C:\\Microsoft.VC90.CRT")

data_files = [("Microsoft.VC90.CRT", glob(r'C:\Microsoft.VC90.CRT\*.*'))]

def get_version():
    try:
        f = open("_generated_version.py")
    except EnvironmentError:
        return None
    ver = None
    for line in f.readlines():
        mo = re.match("__version__ = '([^']+)'", line)
        if mo:
            ver = mo.group(1)
            break

    # Fix version in Inno Setup file too!
    with open('../nemesys.iss', 'r') as fd:
        filedata = fd.read()
    
    # Replace the target string
    if '@version@' in filedata:
        filedata = filedata.replace('@version@', ver)
    
    # Write the file out again
    with open('../nemesys.iss', 'w') as fd:
        fd.write(filedata)

    return ver


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = get_version()
        self.company_name = "Fondazione Ugo Bordoni"
        self.copyright = "(c)2010-2016 Fondazione Ugo Bordoni"
        self.name = "Nemesys"

myservice = Target(
    # used for the versioninfo resource
    description = "Nemesys Service",
    # what to build.  For a service, the module name (not the
    # filename) must be specified!
    modules = ['Nemesys'],
    icon_resources = [(1, "..\\nemesys.ico")],
    cmdline_style = 'pywin32',
    )

setup(
        data_files=data_files,
    options = {
        'py2exe': {
            'packages': 'encodings',
            'optimize': 2,
        }
    },
    name = 'Nemesys',
    version = get_version(),
    service = [myservice],
    windows = [
        {"script": "login.py", 'uac_info': "requireAdministrator", "icon_resources": [(1, "..\\nemesys.ico")]},
    ],
    #packages = ['nemesys'],
)
