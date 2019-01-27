from formats.structclasses import (structclass, union,
    readfrom, writeinto, bitfield, anonymous, ubyte, ushort)

from functools import wraps
from ctypes import sizeof
import unittest
import sys


class TestStructclasses(unittest.TestCase):
    def setUp(self):
        try:
            @structclass(byteorder='>')
            class struct:
                signature: ushort
                data:      ubyte * 5
        except:
            self.SkipTest('couldn\'t create structclass')

        self.__struct = struct

    def test_size(self):
        self.assertEqual(sizeof(self.__struct), 7)

    def test_structclass_attrs(self):
        sig, data = 1, (ubyte * 5)(2, 3, 4, 5, 6)
        s = self.__struct(sig, data)
        self.assertEqual(s.signature, sig)
        self.assertEqual(list(s.data), list(data))

    def test_readfrom(self):
        s = self.__struct()
        readfrom(s, b'\x00\x01\x02\x03\x04\x05\x06')

        sig, data = 1, (ubyte * 5)(2, 3, 4, 5, 6)
        self.assertEqual(s.signature, sig)
        self.assertEqual(list(s.data), list(data))

    def test_writeinto(self):
        sig, data = 1, (ubyte * 5)(2, 3, 4, 5, 6)
        s = self.__struct(sig, data)
        buf = bytearray(7)

        writeinto(s, buf)
        self.assertEqual(bytes(buf), b'\x00\x01\x02\x03\x04\x05\x06')


class TestUnion(unittest.TestCase):
    def setUp(self):
        try:
            @union
            class _u:
                b: ubyte
                s: ushort
        except:
            self.SkipTest('couldn\'t create union class')
        
        try:
            @structclass
            class struct:
                val: _u
        except:
            self.SkipTest('coulnd\'t create struct with union member')

        self.__struct = struct

    def test_size(self):
        self.assertEqual(sizeof(self.__struct), 2)

    def test_union(self):
        s = self.__struct()
        s.val.b = 5
        self.assertEqual(s.val.b, 5)

        s = self.__struct()
        s.val.s = 7
        self.assertEqual(s.val.s, 7)

    def test_readfrom(self):
        s = self.__struct()
        readfrom(s, b'\x01\x00')
        self.assertEqual(s.val.b, 1)

        if sys.byteorder == 'little':
            self.assertEqual(s.val.s, 1)
        else:
            self.assertEqual(s.val.s, 1 << 8)
    
    def test_writeinto(self):
        s = self.__struct()
        s.val.s = 3

        buf = bytearray(2)
        writeinto(s, buf)
        self.assertEqual(bytes(buf), (3).to_bytes(2, sys.byteorder))


class TestExtensions(unittest.TestCase):
    def test_anonymous(self):
        @union
        class _u:
            fst: ubyte
            snd: ubyte
        
        @structclass
        class struct:
            which: ubyte
            val: anonymous(_u)

        self.assertEqual(sizeof(struct), 2)
        s = struct()
        s.which = 0
        s.fst = 1

    def test_bitfield(self):
        @structclass(byteorder='>')
        class struct:
            flag_1: bitfield[ubyte:4]
            flag_2: bitfield[ubyte:4]

        self.assertEqual(sizeof(struct), 1)
        s = struct(1, 2)

        self.assertEqual(s.flag_1, 1)
        self.assertEqual(s.flag_2, 2)

        buf = bytearray(1)
        writeinto(s, buf)
        self.assertEqual(buf, b'\x12')

        readfrom(s, b'\x34')
        self.assertEqual(s.flag_1, 3)
        self.assertEqual(s.flag_2, 4)
