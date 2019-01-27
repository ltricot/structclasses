from __future__ import annotations
import ctypes
import sys
import abc

from . import structclasses as stc

_CData = ctypes.c_ubyte.__mro__[2]


def blockclass(cls):
    # pre-compile type annotation code
    annot = getattr(cls, '__annotations__', {})
    for attr, code in annot.items():
        bytecode = compile(
            code,
            filename=sys.modules[cls.__module__].__file__,
            mode='eval')
        annot[attr] = bytecode

    def __str__(self):
        def _get_str(cval):
            if hasattr(cval, '__iter__'):
                return list(str(val) for val in cval)
            return cval
        attrs = ', '.join(f"{attr}={_get_str(getattr(self, attr))}"
                          for attr in self.__annotations__)
        return f'{cls.__name__}({attrs})'
    cls.__str__ = __str__
    return cls


class _BlockBase(abc.ABC):
    @abc.abstractmethod
    def _frombuffer(self, buf, offset=0):
        raise NotImplementedError()
    
    @abc.abstractmethod
    def _tobuffer(self, buf, offset=0):
        raise NotImplementedError()


def optional(on, atype):
    empty = type('empty', (ctypes.Structure,), dict())
    return atype if on else empty


def dispatch(on, branches, default=None):
    if on not in branches and default is not None:
        return default
    return branches[on]


def repeat(atype, until):
    class repeat(list, _BlockBase):
        _type = staticmethod(atype)
        _until = staticmethod(until)

        def _frombuffer(self, buf, offset=0):
            off = offset
            block = self._type()
            off += readfrom(block, buf, offset=off)
            self.append(block)

            while not self._until(self[-1]):
                self.append(self._type())
                off += readfrom(self[-1], buf, offset=off)
            return off - offset
        
        def _tobuffer(self, buf, offset=0):
            off = offset
            for block in self:
                off += writeinto(block, buf, offset=off)
            return off - offset
    return repeat


def readfrom(bcls, buf, offset=0):
    def _get_types(bcls):
        globalns = sys.modules[bcls.__module__].__dict__
        localns = bcls.__dict__

        for attr, code in bcls.__annotations__.items():
            type = eval(code, globalns, localns)
            val = yield attr, type
            setattr(bcls, attr, val)

    # recursion leaf
    if isinstance(bcls, _CData):
        return stc.readfrom(bcls, buf, offset)

    if isinstance(bcls, _BlockBase):
        return bcls._frombuffer(buf, offset=offset)

    off = offset
    types = _get_types(bcls)
    val = None

    # recurse on attributes
    while True:
        try:
            attr, type = types.send(val)
        except StopIteration:
            break

        val = type()
        off += readfrom(val, buf, offset=off)
    return off - offset


def writeinto(bcls, buf, offset=0):
    off = offset
    if isinstance(bcls, _CData):
        return stc.writeinto(bcls, buf, off)
    
    if isinstance(bcls, _BlockBase):
        return bcls._tobuffer(buf, off)

    for attr in bcls.__annotations__:
        off += writeinto(getattr(bcls, attr), buf, off)
    return off - offset
