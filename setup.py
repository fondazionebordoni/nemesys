#!/usr/bin/env python

from distutils.command.sdist import sdist
from distutils.core import setup
import os
import sys
from nemesys.executer import __version__

if sys.platform == 'win':
  import py2exe

setup(name='NeMeSys',
      version=__version__,
      description='NEtwork MEasurement SYStem',
      long_description=open('README').read(),
      license='GPL',
      author='Giuseppe Pantanetti',
      author_email='gpantanetti@fub.it',
      url='http://code.google.com/p/nemesys-qos/',
      packages=['nemesys'],
      requires=['M2Crypto', 'glib', 'gtk', 'gobject'],
      provides=['nemesys'],
      platforms=['Linux', 'Windows', 'MacOS'],
      windows=[
        {
          'script': 'nemesys/gui.py',
          'icon_resources': [(1, "nemesys.ico")],
        }
      ],
      options={
        'py2exe': {
          'includes': 'asyncore, glib, sys, time, webbrowser, gtk, gobject',
        },
        'sdist': {
          'formats': 'zip',
        }
      }
      )
