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
import collections
import functools
import io
import os.path
import random
import struct
import shutil
import typing
import re
import xml.etree.ElementTree as xml
from xml.dom import minidom
import configparser

import universal_qt

import qt
from qt.core import *
from qt.gui import *
from qt.widgets import QApplication

import mersenne


app = QApplication([])


def unpack(f, fmt, n=None):
    if n is not None:
        fmt *= n
    fmt = "<" + fmt
    size = struct.calcsize(fmt)
    result = struct.unpack(fmt, f.read(size))
    if n is None:
        [result] = result
    return result


def parse_ndd_xml(f, parent=None):
    if parent is None:
        header = f.read(8)
        assert header[1:4] == b"ndd"

    tag = f.read(unpack(f, "i")).decode()

    if parent is None:
        element = xml.Element(tag)
    else:
        element = xml.SubElement(parent, tag)

    attr_count = unpack(f, "i")
    tag_count = unpack(f, "i")

    for attr_i in range(attr_count):
        attr = f.read(unpack(f, "i")).decode()
        value = f.read(unpack(f, "i")).decode()
        element.set(attr, value)

    for tag_i in range(tag_count):
        parse_ndd_xml(f, element)

    return element


def pretty_xml(element, **kwargs):
    s = xml.tostring(element)
    dom = minidom.parseString(s)
    return dom.toprettyxml(**kwargs)


def expand_html(s):
    s = s.replace("[NEWLINE]", "&#10;")
    return re.sub(r"<(div|a)(.*?)/>", r"<\1\2></\1>", s)


def content(*fn):
    return os.path.join("Content Dump", *fn)


def output(*fn):
    return os.path.join("output", *fn)


@functools.lru_cache(None)
def get_img(fn, chromakey="fuchsia"):
    img = QPixmap(content(fn))
    mask = img.createMaskFromColor(QColor(chromakey), qt.MaskInColor)
    img.setMask(mask)
    return img.toImage()


@functools.lru_cache(None)
def _get_file(fn):
    with open(content(fn), "rb") as f:
        return f.read()


def get_file(fn):
    return io.BytesIO(_get_file(fn))


with get_file("SWG_Super Win the Game.vdd") as campaign_f:
    root = parse_ndd_xml(campaign_f)
campaign = root.find("./campaign")

strings = configparser.ConfigParser()
with open(content("SWG_Strings.txt"), encoding="utf-8-sig") as strings_f:
    strings.read_file(strings_f)
strings = dict(strings.items())


if os.path.isdir(output("ndd")):
    for fn in os.listdir(content()):
        if fn.endswith((".ndd", ".vdd")):
            with get_file(fn) as f:
                f_root = parse_ndd_xml(f)
            with open(output("ndd", fn + ".xml"), "w") as xml_f:
                xml_f.write(pretty_xml(f_root, indent="  "))


pal_img = QImage(content("NPC_Palettes.bmp"))
npc_colors = [
    (pal_img.pixel(0, y), pal_img.pixel(1, y), pal_img.pixel(2, y))
    for y in range(pal_img.height())
]


def random_int(top):
    n = mersenne.extract_number()
    f = n / (2 ** 32)
    return int(f * top)


def find_npc_values(entity_id):
    mersenne.initialize_generator(entity_id)  # seed with entity_id
    sprite_index = random_int(8)
    color_index = random_int(8)
    return npc_colors[color_index], sprite_index


class Animation(typing.NamedTuple):
    name: str
    frames: list
    random: bool


class Palette(object):
    def __init__(self, el):
        self.img = get_img(el.get("src"), el.get("chromakey"))

        self.animations = []
        with get_file(el.get("animation")) as f:
            f.read(2)
            tile_count = unpack(f, "i")
            for tile_i in range(tile_count):
                tile_name = f.read(unpack(f, "i")).decode()
                frames = []
                frame_count = unpack(f, "i")
                for frame_i in range(frame_count):
                    x, y = unpack(f, "i", 2)
                    frames.append((x, y))
                unpack(f, "i")
                random = unpack(f, "B")
                self.animations.append(Animation(tile_name, frames, random))

        self.collision = dict()
        with get_file(el.get("collision")) as f:
            f.read(2)
            w, h = unpack(f, "i", 2)
            for x in range(w):
                for y in range(h):
                    self.collision[x, y] = unpack(f, "B")


all_palettes = {el.get("name"): Palette(el) for el in campaign.find("./palettes")}


maps = campaign.find("./maps")

invis = QImage("invisible.png")


html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8"/>
    <meta name="robots" content="noindex"/>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>

<div id="header" class="header">
    <div class="right">
        <h2><a href="https://superwinthegame.com/">Super Win the Game</a></h2> (game and visuals created by <a href="https://minorkeygames.com/">Minor Key Games</a>)
    </div>
    <div class="left">
        <h2><a href="." title="Maps Index">Map</a>: {title}</h2> (made by <a href="https://steamcommunity.com/id/blaxpirit">BlaXpirit</a> with help of <a href="https://steamcommunity.com/id/morsk">Morsk</a>)
    </div>
</div>

{body}

    <script type="text/javascript" src="https://code.jquery.com/jquery-3.5.1.min.js"></script>
    <script type="text/javascript" src="script.js?1"></script>
</body>
</html>"""

try:
    for fn in ["script.js", "style.css", "index.html"]:
        shutil.copyfile(fn, output(fn))
except Exception:
    pass

rw, rh = 256, 224
tw, th = 8, 8
rtw, rth = 16 * 2, 14 * 2
anim_frames = 16


def slugify(s, sep="-"):
    s = s.casefold()
    s = re.sub(r"[^\w\s-]+", sep, s, flags=re.UNICODE)
    s = re.sub(r"[{}\s]+".format(re.escape(sep)), sep, s)
    return s.strip(sep)


def rename_entity(s):
    s = s.replace("Mini MacGuffin", "Gem")  # wat
    s = s.replace("Mega MacGuffin", "Heart")  # wat
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
    return "-".join(str(int(i)).replace("-", "n") for i in (x, y))


def set_style(el, d):
    style = "; ".join(
        f"{k}: {v}" + ("px" if isinstance(v, int) else "") for k, v in d.items()
    )
    el.set("style", style)


def produce_map(map, anim_phase):
    edisplay = xml.Element("div", {"id": "display"})
    e = xml.SubElement(edisplay, "div", {"id": "offset"})

    map_name = map.get("name")
    palettes = [all_palettes[palette.get("name")] for palette in map.iter("palette")]

    backcolor = QColor(map.get("backcolor"))

    map_f = get_file(map.get("src"))
    map_f.read(18)

    grid = dict()

    room_count = unpack(map_f, "i")

    anim_rand = random.Random()
    anim_rand.seed(0, version=2)

    for room_index in range(room_count):
        coord_x, coord_y = unpack(map_f, "i", 2)

        eroom = xml.SubElement(e, "div", {"class": "room"})
        eroom.set("id", "room-" + coord_id(coord_x, coord_y))
        set_style(
            eroom,
            {"left": coord_x * rw, "top": coord_y * rh, "width": rw, "height": rh},
        )

        ent_img = QImage(rw, rh, QImage.Format_ARGB32)
        ent_img.fill(qt.transparent)
        ent_p = QPainter(ent_img)

        entity_sprite_names = collections.defaultdict(list)

        entity_count = unpack(map_f, "i")
        for entity_i in range(entity_count):
            important = False

            for xml_i in range(3):
                map_f.read(unpack(map_f, "i"))
            entity_id = unpack(map_f, "i")
            entity_id_s = format(entity_id, "08x")
            entity_fn = "SWG_EntInst_{}.ndd".format(entity_id_s)
            with get_file(entity_fn) as entity_f:
                root = parse_ndd_xml(entity_f)

            pos = root.find("./space/position/vector[@x]")
            x, y = int(pos.get("x")), int(pos.get("y"))
            size = root.findall("./space/scale/vector[@x]")[-1]
            w, h = int(size.get("x")), int(size.get("y"))
            sprite = root.find("./sprite")
            if sprite is not None:
                sprite_name = sprite.get("name")
            else:
                sprite_name = None
            if sprite is not None and sprite.get("sheet"):
                important = True
                s = get_img(sprite.get("sheet"))
                sx, sy = 0, 0
                find_sequence = [
                    root.find('./anim/sequence[@name="on"]'),
                    root.find('./anim/sequence[@name="out"]'),
                    root.find('./anim/sequence[@startplaying="true"]'),
                ]
                sequence = next((el for el in find_sequence if el is not None), None)
                if sequence is not None:
                    frame = sequence.find("./frame")
                    try:
                        multiplier = round(0.7 / float(sequence.get("duration")))
                    except ZeroDivisionError:
                        multiplier = 0
                    offset = anim_rand.random()
                    dx = int(frame.get("dx"))
                    dy = int(frame.get("dy"))
                    total_frames = dx * dy
                    current_frame = (
                        int(
                            (offset + anim_phase / anim_frames * multiplier)
                            * total_frames
                        )
                        % total_frames
                    )
                    sx = int(frame.get("x")) + w * current_frame * (dx // total_frames)
                    sy = int(frame.get("y")) + h * current_frame * (dy // total_frames)
                if "Ghost Block" in sprite_name:
                    sy = h * 1  # Make ghost blocks fully visible
                elif "NPC" in sprite_name:
                    npc = root.find("./npc[@face]")
                    if npc is not None:
                        if npc.get("face") == "right":
                            sx += s.width() // 2
                    colors, row = find_npc_values(entity_id)
                    rgb = [QColor(c).rgb() for c in [qt.red, qt.green, qt.blue]]
                    colors = dict(zip(rgb, colors))
                    sy = h * row
                    s = s.copy()
                    for py in range(sy, sy + h):
                        for px in range(sx, sx + w):
                            try:
                                s.setPixel(px, py, colors[s.pixel(px, py)])
                            except KeyError:
                                pass
                elif "Phase Block" in sprite_name or "Retractable" in sprite_name:
                    initoff = root.find(
                        './script/onfullyloaded/action[@text="run self initoff"]'
                    )
                    if initoff is not None:
                        # sx += w
                        ent_p.setOpacity(0.6)
                elif "Fritzing Bolts" in sprite_name:
                    ent_p.setOpacity(0.4)
                elif "Hollow King" in sprite_name:
                    bad = root.find(
                        './script/onfullyloaded/action[@text="anim self play king"]'
                    )
                    good = root.find(
                        './script/onfullyloaded/query/true/action[@text="anim self play heal"]'
                    )
                    if bad is not None:
                        sy = 96
                    elif good is not None:
                        sy = 64

                vector = root.find("./space/velocity/vector")
                mod = root.find('./anim/sequence[@startplaying="true"]/mod')
                if vector is not None and mod is not None:
                    if int(vector.get("x")) * int(mod.get("nx")) >= 0:  # if signs match
                        sy = int(mod.get("oy"))
                ent_p.drawImage(x - w // 2, y - h // 2, s, sx, sy, w, h)
                ent_p.setOpacity(1)

            eentity = xml.SubElement(
                eroom, "a", {"class": "entity", "name": entity_id_s}
            )
            entity_name = root.find("./name")

            def add_class(s):
                eentity.set("class", "{} {}".format(eentity.get("class"), s))

            if entity_name is not None:
                entity_name = entity_name.get("name")
            if not entity_name and sprite is not None:
                entity_name = sprite_name
                if entity_name:
                    entity_name = entity_name[entity_name.index("SWG_") + 4 :]
                    entity_sprite_names[entity_name].append((x / rw + y / rh, eentity))
            text = list(strings.get(entity_id_s, {}).values())
            if entity_name:
                important = True
                if rename_entity(entity_name) in ["gem", "green-gem"]:
                    add_class("gem")
                elif rename_entity(entity_name) == "heart":
                    add_class("heart")
                text.extend(strings.get(entity_name, {}).values())
            else:
                entity_name = entity_id_s

            if text:
                text = "[NEWLINE]".join(
                    "\N{BULLET} "
                    + re.sub(
                        r"\{([a-zA-Z]+:)*([a-zA-Z]+)\}",
                        r"[\2]",
                        v.replace(r"\n", "[NEWLINE]\N{EN SPACE}"),
                    )
                    for v in text
                    if not ((v.startswith("[") and v.endswith("]")))
                )
                eentity.set("title", text)
            if entity_name:
                eentity.set(
                    "id",
                    f"ent-{coord_id(coord_x, coord_y)}-{rename_entity(entity_name)}",
                )
            set_style(
                eentity,
                {"left": x - w // 2, "top": y - h // 2, "width": w, "height": h},
            )

            for tele in root.findall("./teleport[@mapx]"):
                important = True
                filename = (
                    rename_map(tele.get("map")) + ".html"
                    if tele.get("map") != map_name
                    else ""
                )
                if eentity.get("href") and tele.get("map") == map_name:
                    continue
                if tele.get("entity"):
                    eentity.set(
                        "href",
                        "{}#ent-{}-{}".format(
                            filename,
                            coord_id(tele.get("mapx"), tele.get("mapy")),
                            rename_entity(tele.get("entity")),
                        ),
                    )
                else:
                    eentity.set(
                        "href",
                        "{}#room-{}".format(
                            filename, coord_id(tele.get("mapx"), tele.get("mapy"))
                        ),
                    )

            if not important:
                add_class("unimportant")

            map_f.read(16)

        ent_p.end()
        for group in entity_sprite_names.values():
            if len(group) > 1:
                for i, (order, eentity) in enumerate(sorted(group), 1):
                    eentity.set("id", "{}-{}".format(eentity.get("id"), i))

        room_img = QImage(rw, rh, QImage.Format_ARGB32)
        room_img.fill(qt.transparent)
        room_p = QPainter(room_img)
        room_p.setPen(QPen(qt.green, 1))
        for x, y in itertools.product(range(rtw), range(rth)):
            bg_collision = None
            for fg in [False, True]:
                try:
                    if fg:
                        bg_collision = pal.collision[px, py]  # look at bg's collision
                except AttributeError:
                    pass
                px, py, is_ani, pal = unpack(map_f, "b", 4)
                if is_ani == 2:  # invisible block
                    bg_collision = invis
                    room_p.drawImage(x * tw, y * th, invis)
                    continue
                if px == py == -1:
                    continue
                pal = palettes[pal]
                snow = False
                if is_ani == 1:
                    anim = pal.animations[px]
                    offset = anim_rand.random() if anim.random else 0
                    idx = int((offset + anim_phase / anim_frames) * len(anim.frames))
                    px, py = anim.frames[idx % len(anim.frames)]
                    snow = "Snow" in anim.name

                if not fg:
                    bg_collision = pal.collision[px, py]

                # 0 nothing  1 full  2 spike  3 top  4 water  5 ice  6 toxic  7 ???
                pxt, pyt = px * tw, py * th
                if fg and bg_collision not in [1, 5, invis]:
                    s = sum(
                        qAlpha(pal.img.pixel(pxt + sx, pyt + sy))
                        for sx in range(tw)
                        for sy in range(th)
                    )
                    s /= tw * th * 256
                    room_p.setOpacity(min(1.4 - s, 1))
                if fg and snow:
                    room_p.setOpacity(0.7)
                room_p.drawImage(x * tw, y * th, pal.img, pxt, pyt, tw, th)
                room_p.setOpacity(1)
            if bg_collision == invis:
                room_p.drawImage(x * tw, y * th, invis)

        room_p.drawImage(0, 0, ent_img)
        # room_p.drawText(2, 14, '{},{}'.format(coord_x, coord_y))
        room_p.end()

        for edge in ["top", "bottom", "left", "right"]:
            code1, code2 = unpack(map_f, "B", 2)
            assert code1 in [0, 1]
            scroll = bool(code1)
            assert code2 % 0b1000 in [
                0,  # no teleport on leaving
                0b1,  # teleport to location
                0b11,  # teleport to map->location
                0b111,  # teleport to map->location->entity
            ]
            if not code2:
                continue
            fn = ""
            hsh = ""
            if code2 & 0b001:
                to_x, to_y = unpack(map_f, "i", 2)
                hsh = "#room-{}".format(coord_id(to_x, to_y))
            if code2 & 0b010:
                to_map = map_f.read(unpack(map_f, "i")).decode()
                fn = rename_map(to_map) + ".html" if to_map != map_name else ""
            if code2 & 0b100:
                to_entity = map_f.read(unpack(map_f, "i")).decode()
                hsh = "#ent-{}-{}".format(
                    coord_id(to_x, to_y), rename_entity(to_entity)
                )
            eedge = xml.SubElement(eroom, "a", {"class": "edge {}".format(edge)})
            eedge.set("id", "edge-{}-{}".format(coord_id(coord_x, coord_y), edge))
            eedge.set("href", fn + hsh)

        grid[coord_x, coord_y] = room_img

    dx = -min(x for x, y in grid)
    dy = -min(y for x, y in grid)

    mx = max(x for x, y in grid) + dx + 1
    my = max(y for x, y in grid) + dy + 1

    set_style(
        edisplay,
        {
            "width": rw * mx,
            "height": rh * my,
            "background-color": backcolor.name(),
            "background-image": f"url('{rename_map(map_name)}.png')",
        },
    )
    set_style(e, {"left": rw * dx, "top": rh * dy})

    full_img = QImage(rw * mx, rh * my, QImage.Format_ARGB32)
    full_img.fill(qt.transparent)
    full_p = QPainter(full_img)

    for x, y in grid:
        full_p.fillRect((x + dx) * rw, (y + dy) * rh, rw, rh, backcolor)

    remaining_rooms = dict.fromkeys(grid)

    modifier_count = unpack(map_f, "i")
    for modifier_i in range(modifier_count):
        x, y, w, h = unpack(map_f, "i", 4)
        colored = unpack(map_f, "B")
        cg, cb, cr, ca = unpack(map_f, "B", 4)
        for i in range(x, x + w):
            for j in range(y, y + h):
                del remaining_rooms[i, j]
        if colored:
            color = QColor(cr, cb, cg, ca)
            full_p.fillRect(QRect((x + dx) * rw, (y + dy) * rh, w * rw, h * rh), color)
        eregion = xml.SubElement(e, "div", {"class": "region"})
        set_style(
            eregion, {"left": x * rw, "top": y * rh, "width": w * rw, "height": h * rh}
        )

        map_f.read(unpack(map_f, "i"))

    for x, y in remaining_rooms:
        eregion = xml.SubElement(e, "div", {"class": "region"})
        set_style(eregion, {"left": x * rw, "top": y * rh, "width": rw, "height": rh})

    for (x, y), v in grid.items():
        full_p.drawImage((x + dx) * rw, (y + dy) * rh, v)

    full_p.end()

    full_img.save(output("{}-{:02d}.png".format(rename_map(map_name), anim_phase + 1)))

    body = expand_html(pretty_xml(edisplay, indent="    ").split("\n", 1)[1].strip())
    result = html.format(title=rename_map_title(map_name), body=body)
    with open(output("{}.html".format(rename_map(map_name))), "w") as html_f:
        html_f.write(result)


for map in maps:
    print(map.get("name"))
    for anim_phase in range(anim_frames):
        produce_map(map, anim_phase)
        print(anim_phase + 1, end="\r")
        sys.stdout.flush()
