from __future__ import annotations
import unittest

from formats.structclasses import structclass, ubyte
from formats.blockclasses import blockclass, readfrom


class TestBlockclasses(unittest.TestCase):
    def test_blockclasses(self):
        @blockclass
        class block:
            size: ubyte
            data: ubyte * size

        # basic tests
        size, data = 5, (ubyte * 5)(1, 2, 3, 4, 5)
        b = block(size=size, data=data)

        self.assertEqual(b.size, size)
        self.assertEqual(b.data, data)

    def test_readfrom(self):
        @blockclass
        class block:
            size: ubyte
            data: ubyte * size

        b = block()
        readfrom(b, b'\x05\x01\x02\x03\x04\x05')
        self.assertEqual(b.size, 5)
        self.assertEqual(list(b.data), [1, 2, 3, 4, 5])

    def test_writeinto(self):
        @blockclass
        class block:
            size: ubyte
            data: ubyte * size

        # basic tests
        size, data = 5, (ubyte * 5)(1, 2, 3, 4, 5)
        b = block(size=size, data=data)

        buf = bytearray(6)
        writeinto(b, buf)
        self.assertEqual(bytes(buf), b'\x05\x01\x02\x03\x04\x05')
