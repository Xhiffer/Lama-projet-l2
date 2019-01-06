#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""A library for reading and converting SVG.

This is a converter from SVG to RLG (ReportLab Graphics) drawings.
It converts mainly basic shapes, paths and simple text. The intended
usage is either as module within other projects:

    from svglib.svglib import svg2rlg
    drawing = svg2rlg("foo.svg")

or from the command-line where it is usable as an SVG to PDF converting
tool named sv2pdf (which should also handle SVG files compressed with
gzip and extension .svgz).
"""
from reportlab import xrange
import copy
import gzip
import itertools
import logging
import os, sys
import re
import base64
import tempfile
import subprocess
from collections import defaultdict, namedtuple
from functools import partial

from reportlab.pdfbase.pdfmetrics import registerFont, stringWidth
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.pdfgen.canvas import FILL_EVEN_ODD, FILL_NON_ZERO
from reportlab.pdfgen.pdfimages import PDFImage
from reportlab.graphics.shapes import (
    _CLOSEPATH, Circle, Drawing, Ellipse, Group, Image, Line, Path, PolyLine,
    Polygon, Rect, SolidShape, String,
)
from reportlab.lib import colors
from reportlab.lib.units import pica, toLength
try:
    from lxml import etree
except ImportError:
    import xml.dom.minidom 
    etree = None

from .utils import (
    bezier_arc_from_end_points, convert_quadratic_to_cubic_path,
    normalise_svg_path,
)

__version__ = '0.8.1'
__license__ = 'LGPL 3'
__author__ = 'Dinu Gherman'
__date__ = '2017-04-22'

XML_NS = 'http://www.w3.org/XML/1998/namespace'
STANDARD_FONT_NAMES = (
    'Times-Roman', 'Times-Italic', 'Times-Bold', 'Times-BoldItalic',
    'Helvetica', 'Helvetica-Oblique', 'Helvetica-Bold', 'Helvetica-BoldOblique',
    'Courier', 'Courier-Oblique', 'Courier-Bold', 'Courier-BoldOblique',
    'Symbol', 'ZapfDingbats',
)
DEFAULT_FONT_NAME = "Helvetica"
_registered_fonts = {}

logger = logging.getLogger(__name__)

Box = namedtuple('Box', ['x', 'y', 'width', 'height'])


def find_font(font_name, exact=False):
    """Return the font and a Boolean indicating if the match is exact."""
    if font_name in STANDARD_FONT_NAMES:
        return font_name, True
    elif font_name in _registered_fonts:
        return font_name, _registered_fonts[font_name]

    NOT_FOUND = (None, False)
    try:
        # Try first to register the font if it exists as ttf,
        # based on ReportLab font search.
        registerFont(TTFont(font_name, '%s.ttf' % font_name))
        _registered_fonts[font_name] = True
        return font_name, True
    except TTFError:
        # Try searching with Fontconfig
        try:
            pipe = subprocess.Popen(
                ['fc-match', '-s', '--format=%{file}\\n', font_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            output = pipe.communicate()[0].decode(sys.getfilesystemencoding())
            font_path = output.split('\n')[0]
        except OSError:
            return NOT_FOUND
        try:
            registerFont(TTFont(font_name, font_path))
        except TTFError:
            return NOT_FOUND
        # Fontconfig may return a default font totally unrelated with font_name
        exact = font_name.lower() in os.path.basename(font_path).lower()
        _registered_fonts[font_name] = exact
        return font_name, exact



class ClippingPath(Path):
    def __init__(self, *args, **kwargs):
        copy_from = kwargs.pop('copy_from', None)
        Path.__init__(self, *args, **kwargs)
        if copy_from:
            self.__dict__.update(copy.deepcopy(copy_from.__dict__))
        self.isClipPath = 1

    def getProperties(self, *args, **kwargs):
        props = Path.getProperties(self, *args, **kwargs)
        if 'fillColor' in props:
            props['fillColor'] = None
        return props

class DeferredClippingPath(ClippingPath):
    def __init__(self,ref=None):
        Path.__init__(self)
        self._ref = ref

# Attribute converters (from SVG to RLG)

class AttributeConverter:
    "An abstract class to locate and convert attributes in a DOM instance."

    def parseMultiAttributes(self, line):
        """Try parsing compound attribute string.

        Return a dictionary with single attributes in 'line'.
        """

        attrs = line.split(';')
        attrs = [a.strip() for a in attrs]
        attrs = filter(lambda a:len(a)>0, attrs)

        new_attrs = {}
        for a in attrs:
            k, v = a.split(':')
            k, v = [s.strip() for s in (k, v)]
            new_attrs[k] = v

        return new_attrs

    def findAttr(self, svgNode, name):
        """Search an attribute with some name in some node or above.

        First the node is searched, then its style attribute, then
        the search continues in the node's parent node. If no such
        attribute is found, '' is returned.
        """

        # This needs also to lookup values like "url(#SomeName)"...

        attr_value = svgNode.getAttribute(name).strip()

        if attr_value and attr_value != "inherit":
            return attr_value
        elif svgNode.getAttribute("style"):
            d = self.parseMultiAttributes(svgNode.getAttribute("style"))
            if name in d:
                return d[name]
        if svgNode.getparent() is not None:
            return self.findAttr(svgNode.getparent(), name)

        return ''

    def getAllAttributes(self, svgNode):
        "Return a dictionary of all attributes of svgNode or those inherited by it."

        d = {}

        parent = svgNode.getparent()
        if parent and parent.nodeName == 'g':
            d.update(self.getAllAttributes(svgNode.getparent()))

        style = svgNode.getAttribute("style")
        if style:
            d = self.parseMultiAttributes(style)
            d.update(d)

        for key, value in svgNode.attrib.items():
            if key != "style":
                d[key] = value

        return d

    def id(self, svgAttr):
        "Return attribute as is."
        return svgAttr

    def convertTransform(self, svgAttr):
        """Parse transform attribute string.

        E.g. "scale(2) translate(10,20)"
             -> [("scale", 2), ("translate", (10,20))]
        """

        line = svgAttr.strip()

        ops = line[:]
        brackets = []
        indices = []
        for i, lin in enumerate(line):
            if lin in "()":
                brackets.append(i)
        for i in range(0, len(brackets), 2):
            bi, bj = brackets[i], brackets[i+1]
            subline = line[bi+1:bj]
            subline = subline.strip()
            subline = subline.replace(',', ' ')
            subline = re.sub("[ ]+", ',', subline)
            if ',' in subline:
                indices.append(tuple(float(num) for num in subline.split(',')))
            else:
                indices.append(float(subline))
            ops = ops[:bi] + ' '*(bj-bi+1) + ops[bj+1:]
        ops = ops.replace(',', ' ').split()

        if len(ops) != len(indices):
            logger.warn("Unable to parse transform expression '%s'" % svgAttr)
            return []

        result = []
        for i, op in enumerate(ops):
            result.append((op, indices[i]))

        return result


class Svg2RlgAttributeConverter(AttributeConverter):
    "A concrete SVG to RLG attribute converter."

    def __init__(self,color_converter=None):
        self.color_converter = color_converter or self.identity_color_converter

    @staticmethod
    def identity_color_converter(c):
        return c

    def convertLength(self, svgAttr, percentOf=100, em_base=12):
        "Convert length to points."

        text = svgAttr
        if not text:
            return 0.0
        if ' ' in text.replace(',', ' ').strip():
            logger.debug("Only getting first value of %s" % text)
            text = text.replace(',', ' ').split()[0]

        if text.endswith('%'):
            logger.debug("Fiddling length unit: %")
            return float(text[:-1]) / 100 * percentOf
        elif text.endswith("pc"):
            return float(text[:-2]) * pica
        elif text.endswith("pt"):
            return float(text[:-2]) * 1.25
        elif text.endswith("em"):
            return float(text[:-2]) * em_base
        elif text.endswith("px"):
            return float(text[:-2])

        for unit in ("ex",):
            if unit in text:
                logger.warn("Ignoring unit: %s" % unit)
                text = text.replace(unit, '')

        text = text.strip()
        length = toLength(text)

        return length

    _re_spaces = re.compile(r'\s+')
    @classmethod
    def split_attr_list(cls,svgAttr):
        return cls._re_spaces.split(svgAttr.strip().replace(',', ' '))

    def convertLengthList(self, svgAttr):
        "Convert a list of lengths."
        return [self.convertLength(a) for a in self.split_attr_list(svgAttr)]

    def convertOpacity(self, svgAttr):
        return float(svgAttr)

    def convertFillRule(self, svgAttr):
        return {
            'nonzero': FILL_NON_ZERO,
            'evenodd': FILL_EVEN_ODD,
        }.get(svgAttr, '')

    def convertColor(self, svgAttr):
        "Convert string to a RL color object."

        # fix it: most likely all "web colors" are allowed
        predefined = "aqua black blue fuchsia gray green lime maroon navy "
        predefined = predefined + "olive orange purple red silver teal white yellow "
        predefined = predefined + "lawngreen indianred aquamarine lightgreen brown"

        # This needs also to lookup values like "url(#SomeName)"...

        text = svgAttr
        if not text or text == "none":
            return None

        if text in predefined.split():
            return self.color_converter(getattr(colors, text))
        elif text == "currentColor":
            return "currentColor"
        elif len(text) == 7 and text[0] == '#':
            return self.color_converter(colors.HexColor(text))
        elif len(text) == 4 and text[0] == '#':
            return self.color_converter(colors.HexColor('#' + 2*text[1] + 2*text[2] + 2*text[3]))
        elif text.startswith('rgb') and '%' not in text:
            t = text[3:].strip('()')
            tup = [h[2:] for h in [hex(int(num)) for num in t.split(',')]]
            tup = [(2 - len(h)) * '0' + h for h in tup]
            col = "#%s%s%s" % tuple(tup)
            return self.color_converter(colors.HexColor(col))
        elif text.startswith('rgb') and '%' in text:
            t = text[3:].replace('%', '').strip('()')
            tup = (int(val)/100.0 for val in t.split(','))
            return self.color_converter(colors.Color(*tup))

        logger.warn("Can't handle color: %s" % text)

        return None

    def convertLineJoin(self, svgAttr):
        return {"miter":0, "round":1, "bevel":2}[svgAttr]

    def convertLineCap(self, svgAttr):
        return {"butt":0, "round":1, "square":2}[svgAttr]

    def convertDashArray(self, svgAttr):
        strokeDashArray = self.convertLengthList(svgAttr)
        return strokeDashArray

    def convertDashOffset(self, svgAttr):
        strokeDashOffset = self.convertLength(svgAttr)
        return strokeDashOffset

    def convertFontFamily(self, svgAttr):
        # very hackish
        font_mapping = {
            "sans-serif": "Helvetica",
            "serif": "Times-Roman",
            "times": "Times-Roman",
            "monospace": "Courier",
            }

        font_names = [
            font_mapping.get(font_name.lower(), font_name)
            for font_name in self.split_attr_list(svgAttr)
        ]
        non_exact_matches = []
        for font_name in font_names:
            font_name, exact = find_font(font_name)
            if exact:
                return font_name
            elif font_name:
                non_exact_matches.append(font_name)
        if non_exact_matches:
            return non_exact_matches[0]
        else:
            logger.warn("Unable to find a suitable font for 'font-family:%s'" % svgAttr)
            return DEFAULT_FONT_NAME

        return font_name


class NodeCompat(object):
    """A wrapper to make minidom and lxml look alike"""

    def __init__(self, node):
        self.node = node

    if etree:
        def getAttribute(self, name):
            return self.node.attrib.get(name, '')

        def getAttributeNS(self, uri,name):
            return self.getAttribute("{%s}%s" % (uri,name))

        def getchildren(self,allNodes=False):
            return [NodeCompat(c) for c in self.node.getchildren()]

        @property
        def nodeName(self):
            """Return lxml node name without the namespace prefix."""
            try:
                return self.tag.split('}')[-1]
            except AttributeError:
                pass

        @property
        def is_element(self):
            return self.nodeName!='text'

        @property
        def is_text(self):
            return self.nodeName=='text'

        def getparent(self):
            p = self.node.getparent()
            if p is not None: return NodeCompat(p)

        def deepClone(self):
            return NodeCompat(copy.deepcopy(self.node))

        def appendChild(self,c):
            self.node.append(c.node)

    else:
        def getAttribute(self, name):
            # forward call to wrapped node
            return self.node.getAttribute(name) if self.node.nodeType==self.node.ELEMENT_NODE else ''

        @property
        def attrib(self):
            return self.node.attributes

        @property
        def is_text(self):
            return self.node.nodeType in (self.node.TEXT_NODE,self.node.CDATA_SECTION_NODE)

        @property
        def text(self):
            if self.node.nodeType in (self.node.TEXT_NODE,self.node.CDATA_SECTION_NODE):
                return self.data
            else:
                return ''.join(c.data for c in self.node.childNodes if c.nodeType in (self.node.TEXT_NODE,self.node.CDATA_SECTION_NODE))

        @property
        def is_element(self):
            return self.node.nodeType==self.node.ELEMENT_NODE

        def getparent(self):
            p = self.node.parentNode
            if p is not None: return NodeCompat(p)

        def getchildren(self,allNodes=False):
            return [NodeCompat(c) for c in self.node.childNodes if allNodes or c.nodeType==self.node.ELEMENT_NODE]

        def deepClone(self):
            return NodeCompat(self.node.cloneNode(True))

        def getAttributeNS(self,uri,name):
            return self.node.getAttributeNS(uri,name)

        def appendChild(self,c):
            self.node.appendChild(c.node)

        @property
        def attrib(self):
            return self.node.attributes

    def __getattr__(self, name):
        # forward attribute access to wrapped node
        return getattr(self.node, name)

class NodeTracker:
    """An object wrapper keeping track of arguments to certain method calls.

    Instances wrap an object and store all arguments to one special
    method, getAttribute(name), in a list of unique elements, usedAttrs.
    """
    def __init__(self, node):
        if not isinstance(node,NodeCompat):
            node = NodeCompat(node)
        self.node = node
        self.usedAttrs = []

    def getAttribute(self, name):
        # add argument to the history, if not already present
        if name not in self.usedAttrs:
            self.usedAttrs.append(name)
        # forward call to wrapped object
        return  self.node.getAttribute(name)

    if not etree:
        def getAttributeNS(self, uri, name):
            # add argument to the history, if not already present
            try:
                attr = self._attrsNS[(uri,name)]
            except KeyError:
                return  self.node.getAttributeNS(uri,name)
            name = attr.name
            if name not in self.usedAttrs:
                self.usedAttrs.append(name)
            return attr.value

    def __getattr__(self, name):
        # forward attribute access to wrapped object
        return getattr(self.node, name)

def get_shape_from_group(G):
    #for clip path handling
    for e in G.contents:
        if isinstance(e, Group):
            return get_shape_from_group(e)
        elif isinstance(e, SolidShape):
            return e

def copy_properties(src, dst):
    for p, v in src.getProperties().items():
        try:
            setattr(dst, p, v)
        except AttributeError:
            pass

def convert_shape_to_clipping_path(shape):
    if isinstance(shape, Path):
        return ClippingPath(copy_from=shape)
    elif isinstance(shape, Rect):
        # It is possible to use a rect as a clipping path in an svg, so we
        # need to convert it to a path for rlg.
        x1, y1, x2, y2 = shape.getBounds()
        p = ClippingPath()
        p.moveTo(x1, y1)
        p.lineTo(x2, y1)
        p.lineTo(x2, y2)
        p.lineTo(x1, y2)
        p.closePath()
        # Copy the styles from the rect to the clipping path.
        copy_properties(shape, p)
        return p
    elif shape:
        logging.error("Unsupported shape type %s for clipping" % shape.__class__.__name__)

### the main meat ###

class SvgRenderer:
    """Renderer that renders an SVG file on a ReportLab Drawing instance.

    This is the base class for walking over an SVG DOM document and
    transforming it into a ReportLab Drawing instance.
    """

    def __init__(self, path=None,color_converter=None):
        self.attrConverter = Svg2RlgAttributeConverter(color_converter=color_converter)
        self.shape_converter = Svg2RlgShapeConverter(path,self.attrConverter)
        self.handled_shapes = self.shape_converter.get_handled_shapes()
        self.definitions = {}
        self.waiting_use_nodes = defaultdict(list)
        self.wanted_clip_paths = defaultdict(list)
        self.box = Box(x=0, y=0, width=0, height=0)

    def render(self, svg_node):
        main_group = self.renderNode(svg_node)
        for xlink in self.waiting_use_nodes.keys():
            logger.debug("Ignoring unavailable object with ID '%s'." % xlink)

        main_group.scale(1, -1)
        main_group.translate(0 - self.box.x, -self.box.height - self.box.y)
        drawing = Drawing(self.box.width, self.box.height)
        drawing.add(main_group)
        return drawing

    def renderNode(self, node, parent=None):
        n = NodeTracker(node)
        nid = n.getAttribute("id")
        ignored = False
        item = None
        name = n.nodeName

        clipping = self.get_clippath(n)
        if name == "svg":
            if n.getAttributeNS(XML_NS,"space") == 'preserve':
                self.shape_converter.preserve_space = True
            item = self.renderSvg(n)
            return item
        elif name == "defs":
            item = self.renderG(n)
        elif name == 'a':
            item = self.renderA(n)
            parent.add(item)
        elif name == 'g':
            display = n.getAttribute("display")
            item = self.renderG(n, clipping=clipping)
            if display != "none":
                parent.add(item)
        elif name == "symbol":
            item = self.renderSymbol(n)
            parent.add(item)
        elif name == "use":
            item = self.renderUse(n, clipping=clipping)
            parent.add(item)
        elif name == "clipPath":
            item = self.renderG(n)
        elif name in self.handled_shapes:
            display = n.getAttribute("display")
            item = self.shape_converter.convertShape(name, n, clipping, self)
            if item and display != "none":
                parent.add(item)
        else:
            ignored = True
            logger.debug("Ignoring node: %s" % name)

        if not ignored:
            if nid and item:
                self.definitions[nid] = node
                if nid in self.wanted_clip_paths:
                    p = convert_shape_to_clipping_path(get_shape_from_group(item))
                    for g in self.wanted_clip_paths.pop(nid,[]):
                        #backfill the DeferredClippingPaths in group g
                        for i, c in enumerate(g.contents):
                            if getattr(c,'_ref',None)==nid:
                                g.contents[i] = ClippingPath(copy_from=p)
            if nid in self.waiting_use_nodes.keys():
                to_render = self.waiting_use_nodes.pop(nid)
                for use_node, group in to_render:
                    self.renderUse(use_node, group=group)
            if getattr(n,'_node_rendered',True):
                self.print_unused_attributes(node, n)

    def get_shape_from_node(self,node):
        for c in node.getchildren():
            if c.nodeName == 'path':
                g = self.shape_converter.convertShape('path', NodeTracker(c))
                return g.contents[-1]
            elif c.nodeName == 'use':
                g = self.renderUse(NodeTracker(c))
                return get_shape_from_group(g)
            elif  c.nodeName == 'rect':
                return self.shape_converter.convertRect(NodeTracker(c))
            else:
                return get_shape_from_node(c)

    def get_clippath(self, node):
        """
        Return the clipping Path object referenced by the node 'clip-path'
        attribute, if any.
        """
        clip_path = node.getAttribute('clip-path')
        if clip_path:
            m = re.match(r'url\(#([^\)]*)\)', clip_path)
            if m:
                ref = m.groups()[0]
                if ref in self.definitions:
                    return convert_shape_to_clipping_path(self.get_shape_from_node(self.definitions[ref]))
                else:
                    return DeferredClippingPath(ref=ref)

    def print_unused_attributes(self, node, n):
        if logger.level > logging.DEBUG:
            return
        all_attrs = self.attrConverter.getAllAttributes(node)
        unused_attrs = ['%s=%r' % (attr[0],attr[1]) for attr in all_attrs.items() if attr[0] not in n.usedAttrs]
        if unused_attrs:
            logger.debug("Unused attrs: %s %s" % (n.nodeName, unused_attrs))

    def renderTitle_(self, node):
        # Main SVG title attr. could be used in the PDF document info field.
        pass

    def renderDesc_(self, node):
        # Main SVG desc. attr. could be used in the PDF document info field.
        pass

    def renderSvg(self, node):
        getAttr = node.getAttribute
        width, height = map(getAttr, ("width", "height"))
        width, height = map(self.attrConverter.convertLength, (width, height))
        viewBox = getAttr("viewBox")
        if viewBox:
            viewBox = self.attrConverter.convertLengthList(viewBox)
            self.box = Box(*viewBox)
        else:
            self.box = Box(0, 0, width, height)
        group = Group()
        for child in node.getchildren():
            self.renderNode(child, group)
        return group

    def add_clipping_to_group(self,clipping,group):
        group.add(clipping)
        if isinstance(clipping,DeferredClippingPath):
            self.wanted_clip_paths[clipping._ref].append(group)

    def renderG(self, node, clipping=None, display=1):
        getAttr = node.getAttribute
        id, transform = map(getAttr, ("id", "transform"))
        gr = Group()
        if clipping:
            self.add_clipping_to_group(clipping, gr)
        for child in node.getchildren():
            item = self.renderNode(child, parent=gr)
            if item and display:
                gr.add(item)

        if transform:
            self.shape_converter.applyTransformOnGroup(transform, gr)

        return gr

    def renderSymbol(self, node):
        return self.renderG(node, display=0)

    def renderA(self, node):
        # currently nothing but a group...
        # there is no linking info stored in shapes, maybe a group should?
        return self.renderG(node)

    def renderUse(self, node, group=None, clipping=None):
        xlink_href = node.getAttributeNS('http://www.w3.org/1999/xlink','href')
        if not xlink_href:
            node._node_rendered = False
            return
        if group is None:
            group = Group()
        uid = xlink_href[1:]
        if uid not in self.definitions:
            # The missing definition should appear later in the file
            self.waiting_use_nodes[uid].append((node, group))
            node._node_rendered = False
            return group

        if clipping:
            self.add_clipping_to_group(clipping, group)
        if len(node.getchildren()) == 0:
            # Append a copy of the referenced node as the <use> child (if not already done)
            node.appendChild(self.definitions[uid].deepClone())
        self.renderNode(node.getchildren()[-1], parent=group)
        getAttr = node.getAttribute
        x, y, width, height, transform = [getAttr(a) for a in  ("x", "y", "width", "height", "transform")]
        if x or y:
            transform += " translate(%s, %s)" % (x or '0', y or '0')
        if transform:
            self.shape_converter.applyTransformOnGroup(transform, group)
        node._node_rendered = True
        return group


class SvgShapeConverter:
    """An abstract SVG shape converter.

    Implement subclasses with methods named 'renderX(node)', where
    'X' should be the capitalised name of an SVG node element for
    shapes, like 'Rect', 'Circle', 'Line', etc.

    Each of these methods should return a shape object appropriate
    for the target format.
    """
    def __init__(self, path, attrConverter=None):
        self.attrConverter = attrConverter or Svg2RlgAttributeConverter()
        self.svg_source_file = path
        self.preserve_space = False

    @classmethod
    def get_handled_shapes(cls):
        """Dynamically determine a list of handled shape elements based on
           convert<shape> method existence.
        """
        return [key[7:].lower() for key in dir(cls) if key.startswith('convert')]


class Svg2RlgShapeConverter(SvgShapeConverter):
    """Converter from SVG shapes to RLG (ReportLab Graphics) shapes."""
    embedded_image_magic_re = re.compile(r"data:image/(\w+?);base64")

    def convertShape(self, name, node, clipping=None, renderer=None):
        method_name = "convert%s" % name.capitalize()
        shape = getattr(self, method_name)(node)
        if not shape:
            return
        if name not in ('path', 'polyline', 'text'):
            # Only apply style where the convert method did not apply it.
            self.applyStyleOnShape(shape, node)
        transform = node.getAttribute("transform")
        if not (transform or clipping):
            return shape
        else:
            group = Group()
            if transform:
                self.applyTransformOnGroup(transform, group)
            if clipping:
                renderer.add_clipping_to_group(clipping, group)
            group.add(shape)
            return group

    def convertLine(self, node):
        getAttr = node.getAttribute
        x1, y1, x2, y2 = map(getAttr, ("x1", "y1", "x2", "y2"))
        x1, y1, x2, y2 = map(self.attrConverter.convertLength, (x1, y1, x2, y2))
        shape = Line(x1, y1, x2, y2)

        return shape

    def convertRect(self, node):
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        rx, ry = map(getAttr, ("rx", "ry"))
        rx, ry = map(self.attrConverter.convertLength, (rx, ry))
        shape = Rect(x, y, width, height, rx=rx, ry=ry)

        return shape

    def convertCircle(self, node):
        # not rendered if r == 0, error if r < 0.
        getAttr = node.getAttribute
        cx, cy, r = map(getAttr, ("cx", "cy", 'r'))
        cx, cy, r = map(self.attrConverter.convertLength, (cx, cy, r))
        shape = Circle(cx, cy, r)

        return shape

    def convertEllipse(self, node):
        getAttr = node.getAttribute
        cx, cy, rx, ry = map(getAttr, ("cx", "cy", "rx", "ry"))
        cx, cy, rx, ry = map(self.attrConverter.convertLength, (cx, cy, rx, ry))
        width, height = rx, ry
        shape = Ellipse(cx, cy, width, height)

        return shape

    def convertPolyline(self, node):
        getAttr = node.getAttribute
        points = getAttr("points")
        points = points.replace(',', ' ')
        points = points.split()
        points = list(map(self.attrConverter.convertLength, points))
        if len(points) % 2 != 0 or len(points) == 0:
            # Odd number of coordinates or no coordinates, invalid polyline
            return None

        polyline = PolyLine(points)
        self.applyStyleOnShape(polyline, node)
        has_fill = self.attrConverter.findAttr(node, 'fill') not in ('', 'none')

        if has_fill:
            # ReportLab doesn't fill polylines, so we are creating a polygon
            # polygon copy of the polyline, but without stroke.
            group = Group()
            polygon = Polygon(points)
            self.applyStyleOnShape(polygon, node)
            polygon.strokeColor = None
            group.add(polygon)
            group.add(polyline)
            return group

        return polyline

    def convertPolygon(self, node):
        getAttr = node.getAttribute
        points = getAttr("points")
        points = points.replace(',', ' ')
        points = points.split()
        points = list(map(self.attrConverter.convertLength, points))
        if len(points) % 2 != 0 or len(points) == 0:
            # Odd number of coordinates or no coordinates, invalid polygon
            return None
        shape = Polygon(points)

        return shape

    def clean_text(self, text, preserve_space):
        """Text cleaning as per https://www.w3.org/TR/SVG/text.html#WhiteSpace
        """
        if text is None:
            return
        if preserve_space:
            text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\t', ' ')
        else:
            text = text.replace('\r\n', '').replace('\n', '').replace('\t', ' ')
            text = text.strip()
            while ('  ' in text):
                text = text.replace('  ', ' ')
        return text

    def convertText(self, node):
        attrConv = self.attrConverter
        xml_space = node.getAttributeNS(XML_NS,"space")
        if xml_space:
            preserve_space = xml_space == 'preserve'
        else:
            preserve_space = self.preserve_space

        gr = Group()

        frag_lengths = []

        dx0, dy0 = 0, 0
        x1, y1 = 0, 0
        ff = attrConv.findAttr(node, "font-family") or DEFAULT_FONT_NAME
        ff = attrConv.convertFontFamily(ff)
        fs = attrConv.findAttr(node, "font-size") or "12"
        fs = attrConv.convertLength(fs)
        convertLength = partial(attrConv.convertLength, em_base=fs)
        x, y = map(node.getAttribute, ('x', 'y'))
        x, y = map(convertLength, (x, y))
        for c in itertools.chain([node], node.getchildren(allNodes=True)):
            has_x, has_y = False, False
            dx, dy = 0, 0
            baseLineShift = 0
            if c.is_text:
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
            elif c.nodeName == 'tspan':
                text = self.clean_text(c.text, preserve_space)
                if not text:
                    continue
                x1, y1, dx, dy = [c.getAttribute(name) for name in ("x", "y", "dx", "dy")]
                has_x, has_y = (x1 != '', y1 != '')
                x1, y1, dx, dy = map(convertLength, (x1, y1, dx, dy))
                dx0 += dx
                dy0 += dy
                baseLineShift = c.getAttribute("baseline-shift") or ''
                if baseLineShift in ("sub", "super", "baseline"):
                    baseLineShift = {"sub":-fs/2, "super":fs/2, "baseline":0}[baseLineShift]
                else:
                    baseLineShift = convertLength(baseLineShift, fs)
            else:
                continue

            frag_lengths.append(stringWidth(text, ff, fs))
            new_x = (x1 + dx) if has_x else (x + dx0 + sum(frag_lengths[:-1]))
            new_y = (y1 + dy) if has_y else (y + dy0)
            shape = String(new_x, -(new_y - baseLineShift), text)
            self.applyStyleOnShape(shape, node)
            if c.nodeName == 'tspan':
                self.applyStyleOnShape(shape, c)

            gr.add(shape)

        gr.scale(1, -1)

        return gr

    def convertPath(self, node):
        d = node.getAttribute('d')
        if not d:
            return None
        normPath = normalise_svg_path(d)
        path = Path(autoclose='svg')
        points = path.points
        # Track subpaths needing to be closed later
        subpath_start = []
        lastop = ''

        for i in xrange(0, len(normPath), 2):
            op, nums = normPath[i:i+2]

            # moveto absolute
            if op == 'M':
                path.moveTo(*nums)
                subpath_start = points[-2:]
            # lineto absolute
            elif op == 'L':
                path.lineTo(*nums)

            # moveto relative
            elif op == 'm':
                if len(points) >= 2:
                    if lastop in ('Z', 'z'):
                        starting_point = subpath_start
                    else:
                        starting_point = points[-2:]
                    xn, yn = starting_point[0] + nums[0], starting_point[1] + nums[1]
                    path.moveTo(xn, yn)
                else:
                    path.moveTo(*nums)
                subpath_start = points[-2:]
            # lineto relative
            elif op == 'l':
                xn, yn = points[-2] + nums[0], points[-1] + nums[1]
                path.lineTo(xn, yn)

            # horizontal/vertical line absolute
            elif op == 'H':
                path.lineTo(nums[0], points[-1])
            elif op == 'V':
                path.lineTo(points[-2], nums[0])

            # horizontal/vertical line relative
            elif op == 'h':
                path.lineTo(points[-2] + nums[0], points[-1])
            elif op == 'v':
                path.lineTo(points[-2], points[-1] + nums[0])

            # cubic bezier, absolute
            elif op == 'C':
                path.curveTo(*nums)
            elif op == 'S':
                x2, y2, xn, yn = nums
                if len(points) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x2, y2, xn, yn)

            # cubic bezier, relative
            elif op == 'c':
                xp, yp = points[-2:]
                x1, y1, x2, y2, xn, yn = nums
                path.curveTo(xp + x1, yp + y1, xp + x2, yp + y2, xp + xn, yp + yn)
            elif op == 's':
                x2, y2, xn, yn = nums
                if len(points) < 4 or lastop not in {'c', 'C', 's', 'S'}:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                path.curveTo(xi, yi, x0 + x2, y0 + y2, x0 + xn, y0 + yn)

            # quadratic bezier, absolute
            elif op == 'Q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (x1, y1), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 'T':
                if len(points) < 4:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                xn, yn = nums
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (xi, yi), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # quadratic bezier, relative
            elif op == 'q':
                x0, y0 = points[-2:]
                x1, y1, xn, yn = nums
                x1, y1, xn, yn = x0 + x1, y0 + y1, x0 + xn, y0 + yn
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (x1, y1), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)
            elif op == 't':
                if len(points) < 4:
                    xp, yp, x0, y0 = points[-2:] * 2
                else:
                    xp, yp, x0, y0 = points[-4:]
                x0, y0 = points[-2:]
                xn, yn = nums
                xn, yn = x0 + xn, y0 + yn
                xi, yi = x0 + (x0 - xp), y0 + (y0 - yp)
                (x0, y0), (x1, y1), (x2, y2), (xn, yn) = \
                    convert_quadratic_to_cubic_path((x0, y0), (xi, yi), (xn, yn))
                path.curveTo(x1, y1, x2, y2, xn, yn)

            # elliptical arc
            elif op in ('A', 'a'):
                rx, ry, phi, fA, fS, x2, y2 = nums
                x1, y1 = points[-2:]
                if op == 'a':
                    x2 += x1
                    y2 += y1
                if abs(rx) <= 1e-10 or abs(ry) <= 1e-10:
                    path.lineTo(x2, y2)
                else:
                    bp = bezier_arc_from_end_points(x1, y1, rx, ry, phi, fA, fS, x2, y2)
                    for _, _, x1, y1, x2, y2, xn, yn in bp:
                        path.curveTo(x1, y1, x2, y2, xn, yn)

            # close path
            elif op in ('Z', 'z'):
                path.closePath()

            else:
                logger.debug("Suspicious path operator: %s" % op)
            lastop = op

        gr = Group()
        self.applyStyleOnShape(path, node)

        gr.add(path)
        return gr

    def convertImage(self, node):
        getAttr = node.getAttribute
        x, y, width, height = map(getAttr, ('x', 'y', "width", "height"))
        x, y, width, height = map(self.attrConverter.convertLength, (x, y, width, height))
        xlink_href = node.getAttributeNS('http://www.w3.org/1999/xlink','href')

        embedded = self.embedded_image_magic_re.match(xlink_href)
        if embedded:
            ext = embedded.groups()[0]
            data = base64.decodestring(xlink_href[len(embedded.group(0)):].encode('ascii'))
            _, path = tempfile.mkstemp(suffix='.%s' % ext)
            with open(path, 'wb') as fh:
                fh.write(data)
            img = Image(int(x), int(y+height), int(width), int(-height), path)
            # this needs to be removed later, not here...
            # if exists(path): os.remove(path)
        else:
            xlink_href = os.path.join(os.path.dirname(self.svg_source_file), xlink_href)
            img = Image(int(x), int(y+height), int(width), int(-height), xlink_href)
            try:
                # this will catch invalid image
                PDFImage(xlink_href, 0, 0)
            except IOError:
                logger.error("Unable to read the image %s. Skipping..." % img.path)
                return None
        return img

    def applyTransformOnGroup(self, transform, group):
        """Apply an SVG transformation to a RL Group shape.

        The transformation is the value of an SVG transform attribute
        like transform="scale(1, -1) translate(10, 30)".

        rotate(<angle> [<cx> <cy>]) is equivalent to:
          translate(<cx> <cy>) rotate(<angle>) translate(-<cx> -<cy>)
        """

        tr = self.attrConverter.convertTransform(transform)
        for op, values in tr:
            if op == "scale":
                if not isinstance(values, tuple):
                    values = (values, values)
                group.scale(*values)
            elif op == "translate":
                if isinstance(values, (int, float)):
                    # From the SVG spec: If <ty> is not provided, it is assumed to be zero.
                    values = values, 0
                group.translate(*values)
            elif op == "rotate":
                if not isinstance(values, tuple) or len(values) == 1:
                    group.rotate(values)
                elif len(values) == 3:
                    angle, cx, cy = values
                    group.translate(cx, cy)
                    group.rotate(angle)
                    group.translate(-cx, -cy)
            elif op == "skewX":
                group.skew(values, 0)
            elif op == "skewY":
                group.skew(0, values)
            elif op == "matrix":
                group.transform = values
            else:
                logger.debug("Ignoring transform: %s %s" % (op, values))

    def applyStyleOnShape(self, shape, node, only_explicit=False):
        """
        Apply styles from an SVG element to an RLG shape.
        If only_explicit is True, only attributes really present are applied.
        """

        # RLG-specific: all RLG shapes
        "Apply style attributes of a sequence of nodes to an RL shape."

        # tuple format: (svgAttr, rlgAttr, converter, default)
        mappingN = (
            ("fill", "fillColor", "convertColor", "black"),
            ("fill-opacity", "fillOpacity", "convertOpacity", 1),
            ("fill-rule", "fillMode", "convertFillRule", "nonzero"),
            ("stroke", "strokeColor", "convertColor", "none"),
            ("stroke-width", "strokeWidth", "convertLength", "1"),
            ("stroke-opacity", "strokeOpacity", "convertOpacity", 1),
            ("stroke-linejoin", "strokeLineJoin", "convertLineJoin", "0"),
            ("stroke-linecap", "strokeLineCap", "convertLineCap", "0"),
            ("stroke-dasharray", "strokeDashArray", "convertDashArray", "none"),
        )
        mappingF = (
            ("font-family", "fontName", "convertFontFamily", DEFAULT_FONT_NAME),
            ("font-size", "fontSize", "convertLength", "12"),
            ("text-anchor", "textAnchor", "id", "start"),
        )

        if shape.__class__ == Group:
            # Recursively apply style on Group subelements
            for subshape in shape.contents:
                self.applyStyleOnShape(subshape, node, only_explicit=only_explicit)
            return

        ac = self.attrConverter
        for mapping in (mappingN, mappingF):
            if shape.__class__ != String and mapping == mappingF:
                continue
            for (svgAttrName, rlgAttr, func, default) in mapping:
                svgAttrValue = ac.findAttr(node, svgAttrName)
                if svgAttrValue == '':
                    if only_explicit:
                        continue
                    else:
                        svgAttrValue = default
                if svgAttrValue == "currentColor":
                    svgAttrValue = ac.findAttr(node.getparent(), "color") or default
                try:
                    meth = getattr(ac, func)
                    setattr(shape, rlgAttr, meth(svgAttrValue))
                except (AttributeError, KeyError, ValueError):
                    pass
        if getattr(shape, 'fillOpacity', None) is not None and shape.fillColor:
            shape.fillColor.alpha = shape.fillOpacity


def svg2rlg(path,**kwds):
    "Convert an SVG file to an RLG Drawing object."

    # unzip .svgz file into .svg
    unzipped = False
    if isinstance(path, str) and os.path.splitext(path)[1].lower() == ".svgz":
        data = gzip.GzipFile(path, "rb").read()
        open(path[:-1], 'w').write(data)
        path = path[:-1]
        unzipped = True

    # load SVG file
    if etree:
        parser = etree.XMLParser(remove_comments=True, recover=True)
        try:
            doc = etree.parse(path, parser=parser)
            svg = doc.getroot()
        except Exception as exc:
            logger.error("Failed to load input file, %r! (%s)" % (path,exc))
            return
    else:
        try:
            doc = xml.dom.minidom.parse(path)
            svg = doc.documentElement
        except Exception as exc:
            print("!!!!! Failed to load input file, %r! (%s)!" % (path,exc))
            return

    # convert to a RLG drawing
    svgRenderer = SvgRenderer(path,**kwds)
    drawing = svgRenderer.render(svg)

    # remove unzipped .svgz file (.svg)
    if unzipped:
        os.remove(path)

    return drawing


def main():
    import glob, traceback, sys
    from reportlab.lib.boxstuff import aspectRatioFix
    argv = sys.argv[1:]
    outDir = os.getcwd()
    formats = ['pdf']
    autoSize = False
    verbose = logging.CRITICAL
    handling = False
    for arg in argv:
        if arg.startswith('--outdir='):
            outDir = arg[9:]
            if not os.path.isabs(outDir):
                outDir = os.path.abspath(outDir)
            continue
        elif arg.startswith('--formats='):
            formats = [_.strip() for _ in arg[10:].split(',')]
            continue
        elif arg.startswith('--verbose='):
            verbose = max(int(arg[10:]),logging.CRITICAL)
            continue
        elif arg=='--verbose':
            verbose = logging.DEBUG
            continue
        elif arg=='--autoSize':
            autoSize = True
            continue
        elif arg.startswith('--'):
            raise ValueError('unknown option %r' % arg)
        if verbose!=None:
            if not handling:
                logger.addHandler(logging.StreamHandler(sys.stdout))
                handling = True
            logger.setLevel(verbose)
        for fn in glob.glob(arg):
            try:
                d = svg2rlg(fn)
                if d:
                    if autoSize:
                        preserveAspectRatio = False
                        anchor = 'sw'
                        width = float(d.width)
                        height = float(d.height)
                        x0,y0,x1,y1 = d.getBounds()
                        wo = x1 - x0
                        ho = y1 - y0
                        xn,yn,wn,hn,scaled = aspectRatioFix(preserveAspectRatio,anchor,0,0,width,height,wo,ho)
                        sx = wn/d.width
                        sy = hn/d.height
                        d.transform = [sx,0,0,sy,-sx*x0,-sy*y0]
                        d.width = wn
                        d.height = hn
                    fnRoot=os.path.splitext(os.path.basename(fn))[0]
                    d.save(formats=formats,verbose=verbose,fnRoot=fnRoot,outDir=outDir)
            except:
                traceback.print_exc()

if __name__=='__main__':
    main()
