# test_deliverer.py
# -*- coding: utf-8 -*-

# Copyright (c) 2017 Fondazione Ugo Bordoni.
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
import hashlib
import unittest

import os

from common import deliverer

TEST_CERT_PATH = os.path.join(os.path.dirname(__file__), 'resources', 'tst100.pem')
TEST_FILE_TO_SIGN = os.path.join(os.path.dirname(__file__), 'resources', 'file_to_sign.txt')


class TestDeliverer(unittest.TestCase):

    def setUp(self):
        self.deliverer = deliverer.Deliverer('no url', TEST_CERT_PATH)

    def test_old_sign(self):
        res = get_signature_old(TEST_FILE_TO_SIGN)
        res2 = self.deliverer.get_signature(TEST_FILE_TO_SIGN)
        self.assertEqual(res, res2)

    def test_other_cert(self):
        res = get_signature_old(TEST_FILE_TO_SIGN)
        res2 = self.deliverer.get_signature(TEST_FILE_TO_SIGN)
        self.assertEqual(res, res2)


# This is the old way with M2Crypto, for comparison
def get_signature_old(filename):
    """
    Restituisce la stringa contenente la firma del digest SHA1 del
    file da firmare
    """
    try:
        from M2Crypto import RSA
    except Exception:
        print('Impossibile importare il modulo M2Crypto')
        return None

    data = open(filename, 'rb').read()
    digest = hashlib.sha1(data).digest()

    rsa = RSA.load_key(TEST_CERT_PATH)

    signature = rsa.sign(digest)
    if rsa.verify(digest, signature):
        return signature
    else:
        return None


def main():
    unittest.main()


if __name__ == '__main__':
    main()
