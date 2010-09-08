#!/usr/bin/env python

from distutils.command.sdist import sdist
from distutils.core import setup
import os

VERSION="1.0"

class sdist_svn(sdist):

  user_options = sdist.user_options + [
    ('dev', None, "Add a dev marker")
    ]

  def initialize_options(self):
    sdist.initialize_options(self)
    self.dev = 0

  def run(self):
    if self.dev:
      revision = self.get_tip_revision()
      if revision > 0:
        self.distribution.metadata.version += '.dev%d' % revision
    sdist.run(self)

    cmd = (""" sed -e 's/OptionParser(version="[0-9\.]*"/OptionParser(version="%s"/g' < nemesys/executer.py """ % 
        self.distribution.metadata.version) + " > nemesys/executer.py.new; mv nemesys/executer.py.new nemesys/executer.py"
    os.system(cmd)

  def get_tip_revision(self, path=os.getcwd()):
    import re, commands
    revision = re.search(':(\d*)', commands.getoutput('svnversion'))
    try:
      return int(revision.group(1))
    except:
      return 0

setup(name='Nemesys',
      version=VERSION,
      description='NEtwork MEasurement SYStem',
      long_description=open('README').read(),
      license='GPL',
      author='Giuseppe Pantanetti',
      author_email='gpantanetti@fub.it',
      url='http://code.google.com/p/nemesys-qos/',
      packages=['nemesys', 'nemesys.test'],
      requires=['M2Crypto'],
      provides=['nemesys'],
      platforms=['Linux', 'Windows', 'MacOS'],
      cmdclass={'sdist': sdist_svn},
      )
