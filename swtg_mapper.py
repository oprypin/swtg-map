#!/usr/bin/env python3

# Copyright (C) 2014 Oleh Prypin <blaxpirit@gmail.com>
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import sys
import itertools
import os.path
import random
import struct
import xml.etree.ElementTree as xml


import qt
qt.init()
from qt.core import *
from qt.gui import *
from qt.widgets import QApplication

app = QApplication([])



def unpack(f, fmt='B', n=None):
    if isinstance(fmt, int) and n is None:
        fmt, n = 'B', fmt
    if n is not None:
        fmt *= n
    if not fmt.startswith('<'):
        fmt = '<'+fmt
    sz = struct.calcsize(fmt)
    r = struct.unpack(fmt, f.read(sz))
    if n is None:
        (r,) = r
    return r

def parse_ndd_xml(f, parent=None):
    if parent is None:
        header = f.read(8)
        assert header[1:4]==b'ndd'
    
    tag = f.read(unpack(f, 'i')).decode('utf-8')

    if parent is None:
        element = xml.Element(tag)
    else:
        element = xml.SubElement(parent, tag)
    
    attr_count = unpack(f, 'i')
    tag_count = unpack(f, 'i')
    
    for _ in range(attr_count):
        attr = f.read(unpack(f, 'i')).decode('utf-8')
        value = f.read(unpack(f, 'i')).decode('utf-8')
        element.set(attr, value)
    
    for _ in range(tag_count):
        parse_ndd_xml(f, element)
    
    return element


def pretty_xml(element):
    from xml.dom import minidom
    s = xml.tostring(element)
    dom = minidom.parseString(s)
    return dom.toprettyxml(indent='  ')

def content(*fn):
    return os.path.join('Content Dump', *fn)
def output(*fn):
    return os.path.join('output', *fn)

with open(content('SWG_Super Win the Game.vdd'), 'rb') as f:
    root = parse_ndd_xml(f)
#with open(output('SWG_Super Win the Game.vdd.xml'), 'w') as f:
    #f.write(pretty_xml(root))


campaign = root.find('campaign')


class Palette(object):
    pass
def palette(el):
    self = Palette()
    img = QPixmap(content(el.get('src')))
    mask = img.createMaskFromColor(el.get('chromakey'), qt.MaskInColor)
    img.setMask(mask)
    
    self.img = img.toImage()
    #self.img.save(output('Palette_{}.png'.format(el.get('name'))))
    
    self.ani = []
    with open(content(el.get('animation')), 'rb') as f:
        f.read(2)
        tile_count = unpack(f, 'i')
        for tile_i in range(tile_count):
            tile_name = f.read(unpack(f, 'i'))
            frames = []
            frame_count = unpack(f, 'i')
            for frame_i in range(frame_count):
                x, y = unpack(f, 'i', 2)
                frames.append((x, y))
            if b'Snow' in tile_name:
                frames = [(15, 15)] # Remove snow
            self.ani.append(frames)
            f.read(5)
    
    self.collision = dict()
    with open(content(el.get('collision')), 'rb') as f:
        f.read(2)
        w, h = unpack(f, 'i', 2)
        for x in range(w):
            for y in range(h):
                self.collision[x, y] = unpack(f)
    return self

all_palettes = {el.get('name'): palette(el) for el in campaign.find('palettes')}

imgs = dict()
def get_img(fn):
    if fn not in imgs:
        img = QPixmap(content(fn))
        mask = img.createMaskFromColor(QColor(255, 0, 255), qt.MaskInColor)
        img.setMask(mask)
        imgs[fn] = img.toImage()
    return imgs[fn]


maps = campaign.find('maps')

invis = QImage('invisible.png')

for map in maps:
    print()
    print(map.get('name'))
    palettes = [all_palettes[palette.get('name')] for palette in map.iter('palette')]

    backcolor = QColor(map.get('backcolor'))

    f = open(content(map.get('src')), 'rb')
    f.read(18)
    
    grid = dict()
    
    room_count = unpack(f, 'i')

    for room_index in range(room_count):
        print(room_index, end='\r')
        sys.stdout.flush()
        coord_x, coord_y = unpack(f, 'i', 2)
        
        ent_img = QImage(256, 224, QImage.Format_ARGB32)
        ent_img.fill(qt.transparent)
        g = QPainter(ent_img)

        entity_count = unpack(f, 'i')
        for entity_index in range(entity_count):
            for _ in range(3):
                f.read(unpack(f, 'i'))
            entity_id = unpack(f, 'i')
            entity_id = format(entity_id, '08x')
            fn = 'SWG_EntInst_{}.ndd'.format(entity_id)
            with open(content(fn), 'rb') as f2:
                root = parse_ndd_xml(f2)
            #with open(output(os.path.basename(fn)+'.xml'), 'w') as f2:
                #f2.write(pretty_xml(root))
            
            sprite = root.find('sprite')
            if sprite is not None and sprite.get('sheet'):
                s = get_img(sprite.get('sheet'))
                pos = root.find('./space/position/vector[@x]')
                x, y = int(pos.get('x')), int(pos.get('y'))
                size = root.findall('./space/scale/vector[@x]')[-1]
                w, h = int(size.get('x')), int(size.get('y'))
                sx, sy = 0, 0
                if 'Ghost Block' in sprite.get('name'):
                    sy = 16 # Make ghost blocks fully visible
                
                g.drawImage(x-w//2, y-h//2, s, sx, sy, w, h)

            f.read(16)
        
        g.end()
        
        img = QImage(256, 224, QImage.Format_ARGB32)
        img.fill(qt.transparent)
        g = QPainter(img)
        g.setPen(QPen(qt.green, 1))
        for x, y in itertools.product(range(16*2), range(14*2)):
            bg_collision = None
            for fg in [False, True]:
                try:
                    if fg:
                        bg_collision = pal.collision[px, py] # look at bg's collision
                except AttributeError:
                    pass
                px, py, is_ani, pal = unpack(f, 4)
                if is_ani==2: # invisible block
                    bg_collision = invis
                    g.drawImage(x*8, y*8, invis)
                    continue
                if px==py==0xff:
                    continue
                pal = palettes[pal]
                if is_ani==1:
                    px, py = random.choice(pal.ani[px])
                
                if not fg:
                    bg_collision = pal.collision[px, py]
                
                # 0 nothing  1 full  2 spike  3 top  4 water  5 ice  6 toxic  7 ???
                px8, py8 = px*8, py*8
                if fg and bg_collision not in [1, 5, invis]:
                    s = sum(qAlpha(pal.img.pixel(px8+sx, py8+sy)) for sx in range(8) for sy in range(8))
                    s /= (8*8*256.0)
                    g.setOpacity(min(1.4-s, 1))
                g.drawImage(x*8, y*8, pal.img, px8, py8, 8, 8)
                g.setOpacity(1)
            if bg_collision==invis:
                g.drawImage(x*8, y*8, invis)
        
        g.drawImage(0, 0, ent_img)
        g.drawText(2, 14, '{},{}'.format(coord_x, coord_y))
        g.end()
        #img.save(output('Room_{}_{}.png'.format(map.get('name'), room_index)))
        grid[coord_x, coord_y] = img
            
        
        # read what i used to think was just "01 00 01 00 01 00 01 00"
        # it's actually a series of 4 reads, and some can have internal data.
        for _ in range(4):
            code1, code2 = unpack(f, 2)
            # print('{:2} {:02x} {:02x}  {:x}'.format(room_index, code1, code2, index))
            assert code1 in [0, 1] # make sure, since i don't think it can be anything else
            assert code2 in [0, 0b1, 0b11, 0b111, 0b110111]
            if code2 & 0b0001: # skip 2 int32s
                f.read(8)
            if code2 & 0b0010: # skip a length-prefixed string
                f.read(unpack(f, 'i'))
            if code2 & 0b0100: # skip a length-prefixed string
                f.read(unpack(f, 'i'))
        
    
    dx = -min(x for x, y in grid)
    dy = -min(y for x, y in grid)
    
    mx = max(x for x, y in grid)+dx+1
    my = max(y for x, y in grid)+dy+1
    
    img = QImage(256*mx, 224*my, QImage.Format_ARGB32)
    img.fill(qt.transparent)
    g = QPainter(img)
    
    for x, y in grid:
        g.fillRect((x+dx)*256, (y+dy)*224, 256, 224, backcolor)

    rects = []

    modifier_count = unpack(f, 'i')
    for _ in range(modifier_count):
        x, y, w, h = unpack(f, 'i', 4)
        colored = unpack(f)
        cg, cb, cr, ca = unpack(f, 4)
        r = QRect((x+dx)*256, (y+dy)*224, w*256, h*224)
        rects.append(r)
        if colored:
            color = QColor(cr, cb, cg, ca)
            g.fillRect(r, color)
        
        f.read(unpack(f, 'i'))
    
    for (x, y), v in grid.items():
        g.drawImage((x+dx)*256, (y+dy)*224, v)
    
    for r in rects:
        g.setBrush(qt.transparent)
        g.setPen(QPen(qt.green, 1, qt.DashLine))
        g.drawRect(r.adjusted(1, 1, -2, -2))
    
    g.end()
    
    img.save(output('Zone_{}.png'.format(map.get('name'))))