from __future__ import annotations
from formats.structclasses import (structclass, ubyte, ushort, sizeof,
                                   bitfield)
from formats.blockclasses import (blockclass, readfrom, writeinto, optional,
                                  repeat, dispatch)


## BEGINNING OF FILE ##
@structclass(byteorder='<')
class GIFSignature:
    signature: ubyte * 3
    version:   ubyte * 3


@structclass(byteorder='<')
class LogicalScreenDescriptor:
    width:      ushort
    height:     ushort

    size:       bitfield[ubyte:3]
    sort:       bitfield[ubyte:1]
    resolution: bitfield[ubyte:3]
    GCTF:       bitfield[ubyte:1]

    background: ubyte
    aspect:     ubyte


@structclass(byteorder='<')
class ColorTableEntry:
    red:    ubyte
    green:  ubyte
    blue:   ubyte

## BLOCKs ##


@structclass(byteorder='<')
class SubBlockHeader:
    size: ubyte


@blockclass
class SubBlock:  # useful for many
    header: SubBlockHeader
    data:   ubyte * header.size

### Image ###


@structclass(byteorder='<')
class ImageDescriptor:
    # separator: ubyte  # match 0x2C # in Block
    left:      ushort
    top:       ushort
    width:     ushort
    height:    ushort

    size:      bitfield[ubyte:3]
    reserved:  bitfield[ubyte:2]
    sort:      bitfield[ubyte:1]
    interlace: bitfield[ubyte:1]
    LCTF:      bitfield[ubyte:1]


@structclass(byteorder='<')
class LZWMin:
    minimum_code_size: ubyte


@blockclass
class Image:
    header: ImageDescriptor
    LCT:    optional(
        on=header.LCTF,
        atype=ColorTableEntry * (1 << header.size + 1),
    )

    lzw:    LZWMin
    data:   repeat(SubBlock, until=lambda sub: sub.header.size == 0)


### Extension Blocks ###
@structclass(byteorder='<')
class GenericHeader:
    size: ubyte


@blockclass
class GenericBlock:
    header: GenericHeader
    data: ubyte * header.size


@structclass(byteorder='<')
class GraphicsControlExtension:
    # introducer: ubyte  # 0x21 # in Block
    # GCL:        ubyte  # 0xF9 # in ExtensionBlock
    size:         ubyte  # == 4

    transparency: bitfield[ubyte:1]
    input:        bitfield[ubyte:1]
    disposal:     bitfield[ubyte:3]
    reserved:     bitfield[ubyte:3]

    delay:        ushort
    TCI:          ubyte  # transparent color index
    terminator:   ubyte


@blockclass
class CommentExtensionBlock:
    comment: repeat(
        SubBlock,
        until=lambda sub: sub.header.size == 0,
    )


@structclass(byteorder='<')
class PlainTextExtensionHeader:
    size:   ubyte
    left:   ushort
    top:    ushort
    width:  ushort
    height: ushort

    chr_cell_width:         ubyte
    chr_cell_height:        ubyte
    foreground_color_ix:    ubyte
    background_color_ix:    ubyte


@blockclass
class PlainTextExtensionBlock:
    header: PlainTextExtensionHeader
    text:   repeat(
        SubBlock,
        until=lambda sub: sub.header.size == 0,
    )


@structclass(byteorder='<')
class ApplicationExtensionHeader:
    size: ubyte
    identifier: ubyte * 8
    auth: ubyte * 3


@blockclass
class ApplicationExtensionBlock:
    header: ApplicationExtensionHeader
    appdata: repeat(
        SubBlock,
        until=lambda sub: sub.header.size == 0,
    )

### General Block ###


@structclass(byteorder='<')
class Label:
    value: ubyte


@blockclass
class ExtensionBlock:
    label: Label
    block: dispatch(on=label.value, branches={
        0xF9: GraphicsControlExtension,
        0xFE: CommentExtensionBlock,
        0x01: PlainTextExtensionBlock,
        0xFF: ApplicationExtensionBlock,
    })


@structclass(byteorder='<')
class Trailer:
    pass


@structclass(byteorder='<')
class Introducer:
    value: ubyte


@blockclass
class Block:
    introducer: Introducer
    block: dispatch(on=introducer.value, branches={
        0x21: ExtensionBlock,  # is that it?
        0x2C: Image,
        0x3B: Trailer,
    })


@blockclass
class GIF:
    # must be here
    signature: GIFSignature
    LSD: LogicalScreenDescriptor
    GCT: optional(
        on=LSD.GCTF,
        atype=ColorTableEntry * (1 << LSD.size + 1)
    )

    # blocks
    blocks: repeat(
        Block,
        until=lambda b: b.introducer.value == 0x3B,
    )

    def __iter__(self):
        for block in (b.block for b in self.blocks):
            if isinstance(block, Image):
                data = b''.join(bytes(sub.data) for sub in block.data)
                yield data
