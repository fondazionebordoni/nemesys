# myProp.py
# -*- coding: utf-8 -*-

# Copyright (c) 2010 Fondazione Ugo Bordoni.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

def readProps(filename):
    inf = open(filename,"r")
    line = inf.readline()
    prop=[]
    while line!='':
        line = line.rstrip()
        x=line.find('=')
        [name, value] = [line[0:x], line[x+1:]]
        prop.append((name.rstrip(),value.lstrip()))
        line = inf.readline()

    inf.close()

    return dict(prop)

def writeProps(filename, key, value):
    inf = open(filename,"a")
    inf.write("\r\n"+key+" = "+value)
    inf.close()

if __name__ == '__main__':
    a='./cfg/cfg.properties'
    writeProps(a,"prova","ciccio")
