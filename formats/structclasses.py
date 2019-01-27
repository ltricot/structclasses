from dataclasses import make_dataclass, inspect
from typing import no_type_check_decorator
from ctypes import (BigEndianStructure, LittleEndianStructure, Structure,
                    Union, sizeof)
import ctypes
import sys


# _CData = ctypes.c_ubyte.__mro__[2]

# get_type_hints from the typing module raises when
# annotation is not a `type`
def _get_hints(cls, globalns=None, localns=None):
    if globalns is None:
        globalns = vars(sys.modules[cls.__module__])
    if localns is None:
        localns = vars(cls)

    annot = dict()
    if not hasattr(cls, '__annotations__'):
        return annot

    for name, tval in cls.__annotations__.items():
        if isinstance(tval, str):
            try:
                tval = eval(tval, globalns, localns)
                if not isinstance(tval, (_CData, bitfield, anonymous)):
                    raise TypeError((
                        f'{name}\'s type should be a ctype or one of'
                        f'{bitfield, anonymous} but is {type(tval)})'
                    ))
            except:  # is an actual string
                pass

        annot[name] = tval
    return annot


class bitfield:
    def __init__(self, type, width):
        self.type = type
        self.width = width

    # syntax convenience -- bitfield[ubyte:8]
    def __class_getitem__(cls, key):
        return cls(key.start, key.stop)


class anonymous:
    def __init__(self, type):
        self.type = type


def _structclass_inner(cls=None, byteorder=None, union=False):
    # copy some stuff
    dct = dict(cls.__dict__)
    bases = list(cls.__bases__)

    # manage byteorder & whether structure or union
    tp = 'Union' if union else 'Structure'
    order = 'BigEndian' if byteorder == '>' and not union else \
        'LittleEndian' if byteorder == '<' and not union else ''
    which = eval(order + tp)

    bases.insert(bases.index(object), which)
    qualname = getattr(cls, '__qualname__', None)

    # declare structure fields
    _fields = []
    _anonymous = []
    annot = _get_hints(cls)
    for attr, ctype in annot.items():
        field = (attr, ctype)
        if isinstance(ctype, bitfield):
            field = (attr, ctype.type, ctype.width)
        if isinstance(ctype, anonymous):
            field = (attr, ctype.type)
            _anonymous.append(attr)
        _fields.append(field)

    # set class attributes
    dct['_pack_'] = 1  # don't let ctypes align automatically
    dct['_anonymous_'] = _anonymous
    dct['_fields_'] = _fields
    dct['__annotations__'] = annot

    # necesarry so that dataclasses doesn't complain
    dct['__signature__'] = inspect.Signature()
    if qualname is not None:
        dct['__qualname__'] = qualname

    return make_dataclass(
        cls.__name__,
        list(annot.items()),
        bases=tuple(bases),
        namespace=dct,
        init=False,
    )


@no_type_check_decorator
def structclass(cls=None, *, byteorder=None):
    def decorator(cls):
        return _structclass_inner(cls, byteorder=byteorder)
    if cls is not None:
        return _structclass_inner(cls)
    return decorator


@no_type_check_decorator
def union(cls):
    return _structclass_inner(cls, union=True)


def readfrom(struct, buffer, offset=0):
    ret = sizeof(struct)
    smem = memoryview(struct).cast('B')

    try:
        smem[0:ret] = buffer[offset:offset+ret]
    except ValueError:
        msg = f'{type(struct)} size: {ret}, buffer section size: {len(buffer[offset:offset+ret])}'
        raise ValueError(msg)
    return ret


def writeinto(struct, buffer, offset=0):
    ret = sizeof(struct)
    smem = memoryview(struct).cast('B')
    buffer[offset:offset+ret] = smem
    return ret


char = ctypes.c_char
byte = ctypes.c_byte
ubyte = ctypes.c_ubyte
short = ctypes.c_short
ushort = ctypes.c_ushort
long = ctypes.c_long
ulong = ctypes.c_ulong
longlong = ctypes.c_ulonglong
ulonglong = ctypes.c_ulonglong
cfloat = ctypes.c_float
double = ctypes.c_double
longdouble = ctypes.c_longdouble
