from distutils.core import setup
import py2exe
import sys,os
import netifaces
import modulefinder
#sys.path.append(os.path.dirname(netifaces.__file__))
#modulefinder.AddPackagePath("logger", "nemesys")

class Target:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        # for the versioninfo resources
        self.version = "2.0"
        self.company_name = "Fondazione Ugo Bordoni"
        self.copyright = "(c)2011 Fondazione Ugo Bordoni"
        self.name = "Nemesys"

myservice = Target(
    # used for the versioninfo resource
    description = "Nemesys Service",
    # what to build.  For a service, the module name (not the
    # filename) must be specified!
    modules = ['Nemesys'],
    icon_resources = [(1, "..\\nemesys.ico")],
    cmdline_style='pywin32',
    )

setup(
	options = {
		'py2exe': {
			'packages': 'encodings',
		}
	},
	name = 'Nemesys',
	version = '2.0',
	service = [myservice],
	windows = [
		{"script": "gui.py", 'uac_info': "requireAdministrator", "icon_resources": [(1,"..\\nemesys.ico")]},
		{"script": "SystemProfiler.py", 'uac_info': "requireAdministrator", "icon_resources": [(1,"..\\hp.ico")]}
	],
	#packages = ['nemesys'],
)
