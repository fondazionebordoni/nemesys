# best_test.py
# -*- coding: utf-8 -*-

# Copyright (c) 2015-2017 Fondazione Ugo Bordoni.
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


class BestTest(object):
    """
    Structure to save Proof together with other information
    used for sending to backend
    """

    def __init__(self, proof, profiler_info, n_tests_done):
        """
        Constructor

        Keyword arguments:

        proof -- the proof containing test result
        profiler_info -- output from profiler (a dict)
        n_tests_done -- number of tests made from where this test was chosen
        """
        self._proof = proof
        self._profiler_info = profiler_info
        self._n_tests_done = n_tests_done
        
    @property
    def proof(self):
        return self._proof
    
    @property
    def profiler_info(self):
        return self._profiler_info
    
    @property
    def n_tests_done(self):
        return self._n_tests_done
