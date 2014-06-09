# utils.py
# -*- coding: utf-8 -*-

# Copyright (c) 2014 Fondazione Ugo Bordoni.
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

import platform

def is_windows():
    if platform.system().lower().startswith('win'):
        return True
    else:
        return False

def is_linux():
    if platform.system().lower().startswith('lin'):
         return True
    else:
        return False

def is_darwin():
    if platform.system().lower().startswith('darwin'):
        return True
    else:
        return False
