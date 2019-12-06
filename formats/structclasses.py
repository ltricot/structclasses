from dataclasses import make_dataclass, inspect
from typing import no_type_check_decorator
from ctypes import (BigEndianStructure, LittleEndianStructure, Structure,
                    Union, sizeof)
import ctypes
import sys


# _CData = ctypes.c_ubyte.__mro__[2]

# get_type_hints from the typing module raises when
# annotation is not a type
def _get_hints(cls, globalns=None, localns=None):
    '''evaluate type hints for a class

    evaluate type hints for a class in the class's module's
    context. the context is more complete than at class creation
    time: when `_get_hints` is called the whole module has been
    evaluated.

    every type annotation must be one of `_CData`, `bitfield` or
    `anonymous`. they are the types used to create the binary
    parsing code.

    less restrictive than the standard library get_hints as it
    does not force annotations to be subclasses of `type`.

    .. doctest::

        >>> class array:
        ...     length: int
        ...     data: bytearray
        ...
        >>> _get_hints(array)
        {'length': <class 'int'>, 'data': <class 'bytearray'>}
        >>>
        >>> # type annotations can be arbitrary expressions
        >>> class array:
        ...     length: 5 + 3
        ...     data: bytearray
        ...
        >>> _get_hints(array)
        {'length': 8, 'data': <class 'bytearray'>}

    :param globalns: global context dictionary
    :param localns: local (inside the class) context dictionary
    :returns: a dictionary of evaluated hints
    '''

    if globalns is None:
        globalns = vars(sys.modules[cls.__module__])
    if localns is None:
        localns = vars(cls)

    annot = dict()
    if not hasattr(cls, '__annotations__'):
        return annot

    for name, tval in cls.__annotations__.items():
        if isinstance(tval, str):
            # this try/except is stupid: 2 types of errors can
            # happen:
            #    - inside eval: arbitrary user code error
            #    - raise TypeError: internal error
            # the reaction does not depend on what happens: pass
            # we should separate both errors and react appropriately
            # for each, i.e. not simply silence it
            try:
                tval = eval(tval, globalns, localns)
                if not isinstance(tval, (_CData, bitfield, anonymous)):
                    raise TypeError((
                        f'{name}\'s type should be a ctype or one of'
                        f'{bitfield, anonymous} but is {type(tval)})'
                    ))
            except:
                pass

        annot[name] = tval
    return annot


class bitfield:
    '''a way to express types smaller than sizeof(char)

    the idea of bitfields is to divide a larger value (for
    example, a ubyte value) into smaller values which occupy
    fractions of the larger one. this is useful for flags

    the following example should make it clear:

    ..doctest ::

        >>> @structclass(byteorder='>')
        ... class phaddr32:
        ...     tag:    bitfield[uint:23]
        ...     index:  bitfield[uint:4]
        ...     offset: bitfield[uint:5]
        ... 
        >>> 
        >>> addr = phaddr32(tag=1, index=1, offset=1)
        >>> bytes(addr)  # 0x00000221
        b'\\x00\\x00\\x02!'
        >>> addr.tag
        1

    bit ordering for bit fields in structs is implementation
    defined (i.e. it depends on the compiler), so this is
    unsafe to use.
    '''

    # maybe we should implement this in terms of masks
    # instead of C bitfields: i hear that bit ordering is
    # implementation defined which is a real issue

    def __init__(self, atype, width):
        self.type = atype
        self.width = width

    # syntactic sugar omnomnom -- bitfield[ubyte:8]
    def __class_getitem__(cls, key):
        return cls(key.start, key.stop)


class anonymous:
    '''make a struct member anonymous.
    
    make an attribute's submembers directly accessible through
    the parent's attributes.

    a terrible example:

    .. doctest::

        >>> @structclass(byteorder='>')
        ... class point1d:
        ...     x: uint
        ...
        >>> @structclass(byteorder='>')
        ... class point2d:
        ...     _1d: anonymous(point1d)
        ...     y: uint
        ...
        >>> @structclass(byteorder='>')
        ... class point3d:
        ...     _2d: anonymous(point2d)
        ...     z: uint
        ...
        >>> p = point3d()
        >>> p.x, p.y, p.z = 1, 2, 3
        >>> bytes(p)
        b'\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x02\\x00\\x00\\x00\\x03'
        >>> p
        point3d(_2d=point2d(_1d=point1d(x=1), y=2), z=3)
    '''

    # none of the implementation of ``anonymous`` is here
    # it cannot implement its functionality itself and so
    # acts only as a flag so that ``_structclass_inner``
    # can do the work

    def __init__(self, type):
        self.type = type


def _structclass_inner(cls=None, byteorder=None, union=False, pack=True):
    '''create a :func:`dataclass make_dataclass`
    :class:`structure ctypes.Structure` from a user class.

    this is a very small overlay over the functionality of
    :class:`ctypes.Structure`.

    :param cls: the class to be made into a structure
    :param byteorder: a string specifying the byte order
    '''

    # copy the guts of the user class
    dct = dict(cls.__dict__)
    bases = list(cls.__bases__)

    # manage byteorder & whether structure or union
    # truly a nightmare -- i still don't know if this
    # works for bitfields
    tp = 'Union' if union else 'Structure'
    order = 'BigEndian' if byteorder == '>' and not union else \
        'LittleEndian' if byteorder == '<' and not union else ''
    which = eval(order + tp)  # unconscionable

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
    # the first one is equivalent to __attribute__((packed)) in C
	# or #pragma pack(1)
    dct['_pack_'] = 1 if pack else 0
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


# the people who created `no_type_check_decorator`
# are really smart. i appreciate them
@no_type_check_decorator
def structclass(cls=None, *, byteorder=None, pack=True):
    def decorator(cls):
        return _structclass_inner(cls, byteorder=byteorder, pack=pack)
    if cls is not None:
        return _structclass_inner(cls)
    return decorator


@no_type_check_decorator
def union(cls):
	# is there any sense in the `pack` argument here ?
	# i don't think so
    return _structclass_inner(cls, union=True)


def readfrom(struct, buffer, offset=0):
    # you just know you're on another level when you
    # use memoryviews. as a python coder you're not even
    # supposed to know memory exists :)
    ret = sizeof(struct)
    smem = memoryview(struct).cast('B')

    try:
        smem[0:ret] = buffer[offset:offset+ret]
    except ValueError:
        msg = (f'{type(struct)} size: {ret}, buffer '
               f'section size: {len(buffer[offset:offset+ret])}')
        raise ValueError(msg)
    return ret


def writeinto(struct, buffer, offset=0):
    ret = sizeof(struct)
    smem = memoryview(struct).cast('B')
    buffer[offset:offset+ret] = smem
    return ret


# what kind of shit interface does ctypes provide. for the
# love of god this is supposed to be python
char = ctypes.c_char
byte = ctypes.c_byte
ubyte = ctypes.c_ubyte
short = ctypes.c_short
ushort = ctypes.c_ushort
cint = ctypes.c_int
uint = ctypes.c_uint
long = ctypes.c_long
ulong = ctypes.c_ulong
longlong = ctypes.c_longlong
ulonglong = ctypes.c_ulonglong
cfloat = ctypes.c_float
double = ctypes.c_double
longdouble = ctypes.c_longdouble
