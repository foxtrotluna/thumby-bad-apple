import struct
import time
import thumbyGraphics
import math
import framebuf
from array import array

def read_blockstream(f):
    while True:
        size = f.read(1)[0]
        if size == 0:
            break
        for i in range(size):
            yield f.read(1)[0]


class EndOfData(Exception):
    pass


class LZWDict:
    def __init__(self, code_size):
        self.code_size = code_size
        self.clear_code = 1 << code_size
        self.end_code = self.clear_code + 1
        self.final_code = 0x3b
        self.codes = []
        self.clear()

    def clear(self):
        self.last = b''
        self.code_len = self.code_size + 1
        self.codes[:] = []

    def decode(self, code):
        if code == self.clear_code:
            self.clear()
            return b''
        elif code == self.end_code:
            self.clear()
            raise EndOfData()
        elif code < self.clear_code:
            value = bytes([code])
        elif code <= len(self.codes) + self.end_code:
            value = self.codes[code - self.end_code - 1]
        else:
            value = self.last + self.last[0:1]
        if self.last:
            self.codes.append(self.last + value[0:1])
        if (len(self.codes) + self.end_code + 1 >= 1 << self.code_len and
            self.code_len < 12):
                self.code_len += 1
        self.last = value
        return value


def lzw_decode(data, code_size):
    dictionary = LZWDict(code_size)
    bit = 0
    byte = next(data)
    try:
        while True:
            code = 0
            for i in range(dictionary.code_len):
                code |= ((byte >> bit) & 0x01) << i
                bit += 1
                if bit >= 8:
                    bit = 0
                    byte = next(data)
            yield dictionary.decode(code)
    except StopIteration:
        #print('st')
        return
    except EndOfData:
        #print('end')
        #next(data)
        return
        #while True:
            #next(data)
            

class Extension:
    def __init__(self,f):
        b = f.read(1)
        self.extension_type = b[0]
        # 0x01 = label, 0xfe = comment
        self.data = bytes(read_blockstream(f))


class Frame:
    def __init__(self, f,buffer, colors):
        self.x, self.y, self.w, self.h, flags = (
            struct.unpack('<HHHHB', f.read(9)))
        self.palette_flag = (flags & 0x80) != 0
        self.interlace_flag = (flags & 0x40) != 0
        self.sort_flag = (flags & 0x20) != 0
        self.palette_size = 1 << ((flags & 0x07) + 1)
        if self.palette_flag:
            self.read_palette(f)
            colors = self.palette_size
        self.min_code_sz = f.read(1)[0]
        x = self.x
        y = self.y
        for decoded in lzw_decode(read_blockstream(f),self.min_code_sz):
            for byte in decoded:
                if byte == 0:
                    buffer.pixel(x,y,1)
                if byte == 1:
                    buffer.pixel(x,y,0)
                # if byte == 2:
                    # buffer.pixel(x,y,0)
                x += 1
                if (x >= self.w):
                    x = 0
                    y += 1
    def read_palette(self, f):
        self.palette = self.palette_class(self.palette_size)
        for i in range(self.palette_size):
            self.palette[i] = f.read(3)


class GIFImage:
    def __init__(self, f):
        self.read_header(f)
        print('Palette size: '+str(self.palette_size))
        f.read(self.palette_size*3)
        self.frames = []
        self.extensions = []
        offsetX = round((thumbyGraphics.display.width-self.w)/2)
        offsetY = round((thumbyGraphics.display.height-self.h)/2)
        self.buffer = framebuf.FrameBuffer(bytearray(self.w*self.h), self.w, self.h, framebuf.MONO_VLSB)
        framecount = 0
        delta = 0
        while True:
            block_type = f.read(1)[0]
            if block_type == 0x3b:
                break
            elif block_type == 0x00:
                continue
            elif block_type == 0x2c:
                thumbyGraphics.display.fill(0)
                thumbyGraphics.display.blit(self.buffer,offsetX,offsetY,self.w,self.h,0,0,0)
                Frame(f,self.buffer,self.palette_size)
                thumbyGraphics.display.update()
                #break
            elif block_type == 0x21:
                e = Extension(f)
                if e.extension_type == 0xf9:
                    delta += e.data[1]
            else:
                raise ValueError('Bad block {0:2x}'.format(block_type))

    def read_palette(self, f):
        self.palette = self.palette_class(self.palette_size)
        for i in range(self.palette_size):
            self.palette[i] = f.read(3)

    def read_header(self, f):
        header = f.read(6)
        if header not in {b'GIF87a', b'GIF89a'}:
            raise ValueError("Not GIF file")
        self.w, self.h, flags, self.background, self.aspect = (
            struct.unpack('<HHBBB', f.read(7)))
        self.palette_flag = (flags & 0x80) != 0
        self.sort_flag = (flags & 0x08) != 0
        self.color_bits = ((flags & 0x70) >> 4) + 1
        self.palette_size = 1 << ((flags & 0x07) + 1)
        
thumbyGraphics.display.setFPS(10)
with open("/Games/BadApple/badapple.gif", 'rb') as f:
    gif = GIFImage(f)
    




