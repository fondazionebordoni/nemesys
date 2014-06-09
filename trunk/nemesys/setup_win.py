from distutils.core import setup
import py2exe
import sys, os
from SysProf.windows import profiler
from xml.etree import ElementTree as ET
import modulefinder
from glob import glob

sys.path.append("C:\\Microsoft.VC90.CRT")

data_files = [("Microsoft.VC90.CRT", glob(r'C:\Microsoft.VC90.CRT\*.*'))]

profiler = profiler.Profiler()
data = profiler.profile({'CPU'})
print ET.tostring(data)


class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = "2.2.1"
        self.company_name = "Fondazione Ugo Bordoni"
        self.copyright = "(c)2010-2013 Fondazione Ugo Bordoni"
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
    version = '2.1.5',
    service = [myservice],
    windows = [
        {"script": "gui.py", 'uac_info': "requireAdministrator", "icon_resources": [(1, "..\\nemesys.ico")]},
        {"script": "login.py", 'uac_info': "requireAdministrator", "icon_resources": [(1, "..\\nemesys.ico")]},
    ],
    #packages = ['nemesys'],
)
