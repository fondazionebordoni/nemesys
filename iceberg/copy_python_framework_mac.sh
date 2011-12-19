#!/bin/bash

for app in gui.app executer.app license.app; do

  if [ -e ${app} ]; then

    mkdir -p ${app}/Contents/Frameworks/Python.framework/Versions/2.6/Resources
    mkdir -p ${app}/Contents/Frameworks/Python.framework/Versions/2.6/include/python2.6     
    mkdir -p ${app}/Contents/Frameworks/Python.framework/Versions/2.6/lib/python2.6/config

    cp /System/Library/Frameworks/Python.framework/Versions/2.6/Python ${app}/Contents/Frameworks/Python.framework/Versions/2.6/
    cp /System/Library/Frameworks/Python.framework/Versions/2.6/Resources/Info.plist ${app}/Contents/Frameworks/Python.framework/Versions/2.6/Resources/
    cp /System//Library/Frameworks/Python.framework/Versions/2.6/include/python2.6/pyconfig.h ${app}/Contents/Frameworks/Python.framework/Versions/2.6/include/python2.6/
    cp /System/Library/Frameworks/Python.framework/Versions/2.6/lib/python2.6/config/Makefile ${app}/Contents/Frameworks/Python.framework/Versions/2.6/lib/python2.6/config/

  fi

done


