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


from __future__ import division, print_function

import sys
import itertools
import collections
import os.path
import random
import struct
import shutil
import re
import xml.etree.ElementTree as xml
from xml.dom import minidom

import qt
qt.init()
from qt.core import *
from qt.gui import *
from qt.widgets import QApplication

import mersenne


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
    
    for attr_i in range(attr_count):
        attr = f.read(unpack(f, 'i')).decode('utf-8')
        value = f.read(unpack(f, 'i')).decode('utf-8')
        element.set(attr, value)
    
    for tag_i in range(tag_count):
        parse_ndd_xml(f, element)
    
    return element


def pretty_xml(element, **kwargs):
    s = xml.tostring(element)
    dom = minidom.parseString(s)
    return dom.toprettyxml(**kwargs)
def expand_html(s):
    return re.sub(r'<(div|a)(.*?)/>', r'<\1\2></\1>', s)

def content(*fn):
    return os.path.join('Content Dump', *fn)
def output(*fn):
    return os.path.join('output', *fn)

with open(content('SWG_Super Win the Game.vdd'), 'rb') as campaign_f:
    root = parse_ndd_xml(campaign_f)
#with open(output('SWG_Super Win the Game.vdd.xml'), 'w') as xml_f:
    #xml_f.write(pretty_xml(root, indent='  '))

campaign = root.find('./campaign')


pal_img = QImage(content('NPC_Palettes.bmp'))
npc_colors = [(pal_img.pixel(0, y), pal_img.pixel(1, y), pal_img.pixel(2, y)) for y in range(pal_img.height())]

def random_int(top):
    n = mersenne.extract_number()
    f = n/(2**32)
    return int(f*top)

def find_npc_values(entity_id):
    mersenne.initialize_generator(entity_id) # seed with entity_id
    sprite_index = random_int(8)
    color_index = random_int(8)
    return npc_colors[color_index], sprite_index



class Palette(object):
    pass
def palette(el):
    self = Palette()
    img = QPixmap(content(el.get('src')))
    mask = img.createMaskFromColor(el.get('chromakey'), qt.MaskInColor)
    img.setMask(mask)
    
    self.img = img.toImage()
    
    self.ani = []
    with open(content(el.get('animation')), 'rb') as f:
        f.read(2)
        tile_count = unpack(f, 'i')
        for tile_i in range(tile_count):
            tile_name = f.read(unpack(f, 'i')).decode('utf-8')
            frames = []
            frame_count = unpack(f, 'i')
            for frame_i in range(frame_count):
                x, y = unpack(f, 'i', 2)
                frames.append((x, y))
            if 'Snow' in tile_name:
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

all_palettes = {el.get('name'): palette(el) for el in campaign.find('./palettes')}


imgs = dict()
def get_img(fn):
    if fn not in imgs:
        img = QPixmap(content(fn))
        mask = img.createMaskFromColor(QColor(255, 0, 255), qt.MaskInColor)
        img.setMask(mask)
        imgs[fn] = img.toImage()
    return imgs[fn]


maps = campaign.find('./maps')

invis = QImage('invisible.png')


html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="robots" content="noindex"/>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
    <script type="text/javascript" src="http://code.jquery.com/jquery-1.11.1.min.js"></script>
    <script type="text/javascript" src="script.js"></script>
</head>
<body>

<div id="header" class="header">
    <div class="right">
        <h2><a href="http://superwinthegame.com/">Super Win the Game</a></h2> (game and visuals created by <a href="http://minorkeygames.com/">Minor Key Games</a>)
    </div>
    <div class="left">
        <h2>Map: {title}</h2> (made by <a href="http://steamcommunity.com/id/blaxpirit">BlaXpirit</a> with help of <a href="http://steamcommunity.com/id/morsk">Morsk</a>)
    </div>
</div>

{body}

</body>
</html>'''

try:
    for fn in ['script.js', 'style.css']:
        shutil.copyfile(fn, output(fn))
except Exception:
    pass

rw, rh = 256, 224
tw, th = 8, 8
rtw, rth = 16*2, 14*2

def slugify(s, sep='-'):
    s = s.casefold()
    s = re.sub(r'[^\w\s-]+', sep, s, flags=re.UNICODE)
    s = re.sub(r'[{}\s]+'.format(re.escape(sep)), sep, s)
    return s.strip(sep)
def rename_entity(s):
    s = s.replace("Mini MacGuffin", "Gem") # wat
    s = s.replace("Mega MacGuffin", "Heart") # wat
    return slugify(s)
def rename_map(s):
    return slugify(s)
def rename_map_title(s):
    return {
        "Entry Map": "Dreams",
        "Astronomer Tower": "Starlight Terrace",
        "Ice World": "Glacial Palace",
        "Skyworld": "Sky Pillars",
        "Subterranea": "Waterways",
        "Styx": "Underworld Entrance",
        "Styx Overworld": "Underworld Map",
        "Styx Caves": "Underworld Caves",
        "Fire Realm": "Hollow King's Lair",
    }.get(s, s)

def coord_id(x, y):
    return '-'.join(str(int(i)).replace('-', 'n') for i in (x, y))


for map in maps:
    edisplay = xml.Element('div', {'id': 'display'})
    e = xml.SubElement(edisplay, 'div', {'id': 'offset'})
    
    print()
    map_name = map.get('name')
    print(map_name)
    palettes = [all_palettes[palette.get('name')] for palette in map.iter('palette')]

    backcolor = QColor(map.get('backcolor'))

    map_f = open(content(map.get('src')), 'rb')
    map_f.read(18)
    
    grid = dict()
    
    room_count = unpack(map_f, 'i')

    for room_index in range(room_count):
        print(room_index, end='\r')
        sys.stdout.flush()
        coord_x, coord_y = unpack(map_f, 'i', 2)
        
        eroom = xml.SubElement(e, 'div', {'class': 'room'})
        eroom.set('id', 'room-'+coord_id(coord_x, coord_y))
        eroom.set('style', '''left: {}px; top: {}px; width: {}px; height: {}px'''.format(
            coord_x*rw, coord_y*rh, rw, rh
        ))
        
        ent_img = QImage(rw, rh, QImage.Format_ARGB32)
        ent_img.fill(qt.transparent)
        ent_p = QPainter(ent_img)

        entity_sprite_names = collections.defaultdict(list)

        entity_count = unpack(map_f, 'i')
        for entity_i in range(entity_count):
            unimportant = True
            
            for xml_i in range(3):
                map_f.read(unpack(map_f, 'i'))
            entity_id = unpack(map_f, 'i')
            entity_id_s = format(entity_id, '08x')
            entity_fn = 'SWG_EntInst_{}.ndd'.format(entity_id_s)
            with open(content(entity_fn), 'rb') as entity_f:
                root = parse_ndd_xml(entity_f)
            #with open(output(os.path.basename(entity_fn)+'.xml'), 'w') as xml_f:
                #xml_f.write(pretty_xml(root, indent='  '))
            
            pos = root.find('./space/position/vector[@x]')
            x, y = int(pos.get('x')), int(pos.get('y'))
            size = root.findall('./space/scale/vector[@x]')[-1]
            if size is not None:
                w, h = int(size.get('x')), int(size.get('y'))
            else:
                w = h = 0
            sprite = root.find('./sprite')
            if sprite is not None:
                sprite_name = sprite.get('name')
            else:
                sprite_name = None
            if sprite is not None and sprite.get('sheet'):
                unimportant = False
                s = get_img(sprite.get('sheet'))
                sx, sy = 0, 0
                if 'Ghost Block' in sprite_name:
                    sy = h*1 # Make ghost blocks fully visible
                elif 'NPC' in sprite_name:
                    npc = root.find('./npc[@face]')
                    if npc is not None:
                        if npc.get('face')=='right':
                            sx += s.width()//2
                    colors, row = find_npc_values(entity_id)
                    rgb = [QColor(c).rgb() for c in [qt.red, qt.green, qt.blue]]
                    colors = dict(zip(rgb, colors))
                    sy = h*row
                    s = s.copy()
                    for py in range(sy, sy+h):
                        for px in range(sx, sx+w):
                            try:
                                s.setPixel(px, py, colors[s.pixel(px, py)])
                            except KeyError:
                                pass
                elif 'Phase Block' in sprite_name:
                    if root.find('./script/onfullyloaded/action[@text="run self initoff"]') is not None:
                        #sx += w
                        ent_p.setOpacity(0.6)
                elif 'Fritzing Bolts' in sprite_name:
                    ent_p.setOpacity(0.4)
                elif 'Hollow King' in sprite_name:
                    if root.find('./script/onfullyloaded/action[@text="anim self play king"]') is not None:
                        sy = 96
                    elif root.find('./script/onfullyloaded/query/true/action[@text="anim self play heal"]') is not None:
                        sx, sy = 32, 64

                vector = root.find('./space/velocity/vector')
                mod = root.find('./anim/sequence[@startplaying="true"]/mod')
                if vector is not None and mod is not None:
                    if int(vector.get('x'))*int(mod.get('nx')) >= 0: # if signs match
                        sy = int(mod.get('oy'))
                ent_p.drawImage(x-w//2, y-h//2, s, sx, sy, w, h)
                ent_p.setOpacity(1)

            eentity = xml.SubElement(eroom, 'a', {'class': 'entity', 'name': entity_id_s})
            entity_name = root.find('./name')
            def add_class(s):
                eentity.set('class', '{} {}'.format(eentity.get('class'), s))
            if entity_name is not None:
                entity_name = entity_name.get('name')
            if not entity_name and sprite is not None:
                entity_name = sprite_name
                if entity_name:
                    entity_name = entity_name[entity_name.index('SWG_')+4:]
                    entity_sprite_names[entity_name].append((x/rw+y/rh, eentity))
            if entity_name:
                unimportant = False
                if rename_entity(entity_name) in ['gem', 'green-gem']:
                    add_class('gem')
                elif rename_entity(entity_name)=='heart':
                    add_class('heart')
            else:
                entity_name = entity_id_s
            if entity_name:
                entity_name = rename_entity(entity_name)
                eentity.set('id', 'ent-{}-{}'.format(coord_id(coord_x, coord_y), entity_name))
            eentity.set('style', '''left: {}px; top: {}px; width: {}px; height: {}px'''.format(
                x-w//2, y-h//2, w, h
            ))
            
            for tele in root.findall('./teleport[@mapx]'):
                unimportant = False
                filename = rename_map(tele.get('map'))+'.html' if tele.get('map')!=map_name else ''
                try:
                    eentity.set('href', '{}#ent-{}-{}'.format(
                        filename, coord_id(tele.get('mapx'), tele.get('mapy')), rename_entity(tele.get('entity'))
                    ))
                except (AttributeError, ValueError):
                    print("Error in teleporter entity {}".format(entity_id_s))

            if unimportant:
                add_class('unimportant')
            
            map_f.read(16)
        
        ent_p.end()
        for group in entity_sprite_names.values():
            if len(group)>1:
                for i, (order, eentity) in enumerate(sorted(group), 1):
                    eentity.set('id', '{}-{}'.format(eentity.get('id'), i))
        
        
        room_img = QImage(rw, rh, QImage.Format_ARGB32)
        room_img.fill(qt.transparent)
        room_p = QPainter(room_img)
        room_p.setPen(QPen(qt.green, 1))
        for x, y in itertools.product(range(rtw), range(rth)):
            bg_collision = None
            for fg in [False, True]:
                try:
                    if fg:
                        bg_collision = pal.collision[px, py] # look at bg's collision
                except AttributeError:
                    pass
                px, py, is_ani, pal = unpack(map_f, 'b', 4)
                if is_ani==2: # invisible block
                    bg_collision = invis
                    room_p.drawImage(x*tw, y*th, invis)
                    continue
                if px==py==-1:
                    continue
                pal = palettes[pal]
                if is_ani==1:
                    px, py = random.choice(pal.ani[px])
                
                if not fg:
                    bg_collision = pal.collision[px, py]
                
                # 0 nothing  1 full  2 spike  3 top  4 water  5 ice  6 toxic  7 ???
                pxt, pyt = px*tw, py*th
                if fg and bg_collision not in [1, 5, invis]:
                    s = sum(qAlpha(pal.img.pixel(pxt+sx, pyt+sy)) for sx in range(tw) for sy in range(th))
                    s /= (tw*th*256)
                    room_p.setOpacity(min(1.4-s, 1))
                room_p.drawImage(x*tw, y*th, pal.img, pxt, pyt, tw, th)
                room_p.setOpacity(1)
            if bg_collision==invis:
                room_p.drawImage(x*tw, y*th, invis)
        
        room_p.drawImage(0, 0, ent_img)
        #room_p.drawText(2, 14, '{},{}'.format(coord_x, coord_y))
        room_p.end()
        
        for edge in ['top', 'bottom', 'left', 'right']:
            code1, code2 = unpack(map_f, 2)
            assert code1 in [0, 1]
            scroll = bool(code1)
            assert code2%0b1000 in [
                0, # no teleport on leaving
                0b1, # teleport to location
                0b11, # teleport to map->location
                0b111, # teleport to map->location->entity
            ]
            if not code2:
                continue
            fn = ''
            hsh = ''
            if code2&0b001:
                to_x, to_y = unpack(map_f, 'i', 2)
                hsh = '#room-{}'.format(coord_id(to_x, to_y))
            if code2&0b010:
                to_map = map_f.read(unpack(map_f, 'i')).decode('utf-8')
                fn = rename_map(to_map)+'.html' if to_map!=map_name else ''
            if code2&0b100:
                to_entity = map_f.read(unpack(map_f, 'i')).decode('utf-8')
                hsh = '#ent-{}-{}'.format(coord_id(to_x, to_y), rename_entity(to_entity))
            eedge = xml.SubElement(eroom, 'a', {'class': 'edge {}'.format(edge)})
            eedge.set('id', 'edge-{}-{}'.format(coord_id(coord_x, coord_y), edge))
            eedge.set('href', fn+hsh)
        
        grid[coord_x, coord_y] = room_img
    

    dx = -min(x for x, y in grid)
    dy = -min(y for x, y in grid)
    
    mx = max(x for x, y in grid)+dx+1
    my = max(y for x, y in grid)+dy+1
    
    edisplay.set('style',
        '''width: {}px; height: {}px; background-color: {}; background-image: url('{}.png')'''
        .format(rw*mx, rh*my, backcolor.name(), rename_map(map_name))
    )
    e.set('style', '''left: {}px; top: {}px'''.format(rw*dx, rh*dy))
    
    full_img = QImage(rw*mx, rh*my, QImage.Format_ARGB32)
    full_img.fill(qt.transparent)
    full_p = QPainter(full_img)
    
    for x, y in grid:
        full_p.fillRect((x+dx)*rw, (y+dy)*rh, rw, rh, backcolor)

    remaining_rooms = set(grid)

    modifier_count = unpack(map_f, 'i')
    for modifier_i in range(modifier_count):
        x, y, w, h = unpack(map_f, 'i', 4)
        colored = unpack(map_f)
        cg, cb, cr, ca = unpack(map_f, 4)
        for i in range(x, x+w):
            for j in range(y, y+h):
                remaining_rooms.remove((i, j))
        if colored:
            color = QColor(cr, cb, cg, ca)
            full_p.fillRect(QRect((x+dx)*rw, (y+dy)*rh, w*rw, h*rh), color)
        eregion = xml.SubElement(e, 'div', {'class': 'region'})
        eregion.set('style', '''left: {}px; top: {}px; width: {}px; height: {}px'''.format(x*rw, y*rh, w*rw, h*rh))
        
        map_f.read(unpack(map_f, 'i'))
    
    for x, y in remaining_rooms:
        eregion = xml.SubElement(e, 'div', {'class': 'region'})
        eregion.set('style', '''left: {}px; top: {}px; width: {}px; height: {}px'''.format(x*rw, y*rh, rw, rh))

    
    for (x, y), v in grid.items():
        full_p.drawImage((x+dx)*rw, (y+dy)*rh, v)
    
    full_p.end()
    
    full_img.save(output('{}.png'.format(rename_map(map_name))))
    
    body = expand_html(pretty_xml(edisplay, indent='    ').split('\n', 1)[1].strip())
    result = html.format(title=rename_map_title(map_name), body=body)
    with open(output('{}.html'.format(rename_map(map_name))), 'w') as html_f:
        html_f.write(result)