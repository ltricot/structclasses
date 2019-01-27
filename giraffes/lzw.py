from bitstring import BitStream


def lzw_encode(it, minsize, maxsize):
    def codes():
        def _code(num, size):
            return '0b' + bin(num)[2:].rjust(size, '0')[::-1]
        init = lambda: {chr(i).encode(): i for i in range(1 << minsize)}

        cc, eoi = 1 << minsize, 1 << minsize + 1
        pref = bytearray()
        tab = init()
        maxx = 1 << minsize
        size = minsize

        for char in it:
            pref.append(char)
            bp = bytes(pref)
            if bp in tab:
                continue

            yield _code(tab[bp[:-1]], size)
            tab[bp] = maxx
            maxx += 1

            if maxx == 1 << size:
                size += 1

            if maxx == 1 << maxsize:
                yield _code(cc, size)  # reinitialize table
                size = minsize
                tab = init()

            pref.clear()
            pref.append(char)

        if pref:
            yield _code(tab[bytes(pref)], size)
        yield _code(eoi, size)

    bits = BitStream()
    for c in codes():
        print(c)
        bits.append(c)
        while len(bits) >= bits.pos + 8:
            yield bits.read('bytes:1')

def lzw_decode(it, minsize, maxsize):
    def codes(it):
        size = minsize
        bits = BitStream()
        for byte in it:
            bits.append(byte)
            while len(bits) > bits.pos + size:
                binn = bits.read(f'bits:{size}').bin[::-1]
                print(binn)
                size = yield int(binn, 2)

    init = lambda: {i: chr(i).encode() for i in range(1 << minsize)}
    cc, eoi = 1 << minsize, 1 << minsize + 1
    tab = init()
    size = minsize
    maxx = 1 << minsize + 2

    it = codes(it)
    code = old = next(it)
    yield tab[old]

    while code != eoi:
        if code == cc:
            tab = init()
            code = it.send(size)
            continue
        if code == 1 << minsize - 1:
            size += 1

        if code in tab: tab[maxx] = tab[old] + chr(tab[code][0]).encode()
        else: tab[code] = tab[maxx-1] + chr(tab[maxx-1][0]).encode()

        yield tab[code]
        old = code
        code = it.send(size)

inp = iter(bytes([0, 1, 2, 1, 2, 1, 2] * 4))
inr = lzw_encode(inp, 4, 16)
out = lzw_decode(inr, 4, 16)
print(list(out))
