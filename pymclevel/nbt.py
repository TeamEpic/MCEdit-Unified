#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Named Binary Tag library. Serializes and deserializes TAG_* objects
to and from binary data. Load a Minecraft level by calling nbt.load().
Create your own TAG_* objects and set their values.
Save a TAG_* object to a file or StringIO object.

Read the test functions at the end of the file to get started.

This library requires Numpy.    Get it here:
http://new.scipy.org/download.html

Official NBT documentation is here:
http://www.minecraft.net/docs/NBT.txt


Copyright 2010 David Rio Vierra
"""
import collections
from contextlib import contextmanager
import gzip
import itertools
import logging
import string
import struct
import zlib
from cStringIO import StringIO

import numpy
from numpy import array, zeros, fromstring

#-----------------------------------------------------------------------------
# TRACKING PE ERRORS
#
# DEBUG_PE and dump_fName are overridden by leveldbpocket module
import sys
DEBUG_PE = False
dump_fName = 'dump_pe.txt'

log = logging.getLogger(__name__)


class JSONFormatError(RuntimeError):
    pass

class NBTFormatError(RuntimeError):
    pass


TAG_BYTE = 1
TAG_SHORT = 2
TAG_INT = 3
TAG_LONG = 4
TAG_FLOAT = 5
TAG_DOUBLE = 6
TAG_BYTE_ARRAY = 7
TAG_STRING = 8
TAG_LIST = 9
TAG_COMPOUND = 10
TAG_INT_ARRAY = 11
TAG_LONG_ARRAY = 12


class TAG_Value(object):
    """Simple values. Subclasses override fmt to change the type and size.
    Subclasses may set data_type instead of overriding setValue for automatic data type coercion"""
    __slots__ = ('_name', '_value')

    def __init__(self, value=0, name=""):
        self.value = value
        self.name = name

    fmt = struct.Struct("b")
    tagID = NotImplemented
    data_type = NotImplemented

    _name = None
    _value = None

    def __str__(self):
        return nested_string(self)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newVal):
        """Change the TAG's value. Data types are checked and coerced if needed."""
        self._value = self.data_type(newVal)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, newVal):
        """Change the TAG's name. Coerced to a unicode."""
        self._name = unicode(newVal)

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        # 'data' may be empty or not have the required length. Shall we bypass?
        value = None
        try:
            (value,) = cls.fmt.unpack_from(data)
        except Exception, e:
            if DEBUG_PE:
                fp = open(dump_fName)
                n_lines = len(fp.readlines()) + 1
                fp.close()
                msg = ("*** NBT support could not load data\n"
                    "{e}\n"
                    "----------\nctx.data (length: {lcd}):\n{cd}\n"
                    "..........\ndata (length: {lrd}):\n{rd}\n"
                    "''''''''''\nctx.offset:\n{co}\n"
                    "^^^^^^^^^^\ncls.fmt.format: {cf}\n***\n".format(e=e, cd=repr(ctx.data), rd=repr(data), co=ctx.offset, cf=cls.fmt.format,
                                                               lcd=len(ctx.data), lrd=len(data)
                                                              )
                )
                open(dump_fName, 'a').write(msg)
                added_n_lines = len(msg.splitlines())
                log.warning("Could not unpack NBT data: information written in {fn}, from line {b} to line {e}".format(fn=dump_fName, b=n_lines, e=(n_lines + added_n_lines - 1)))
            else:
                raise e
        if value == None:
            self = cls()
            self.name = 'Unknown'
        else:
            self = cls(value=value)
        ctx.offset += self.fmt.size
        return self

    def __repr__(self):
        return "<%s name=\"%s\" value=%r>" % (unicode(self.__class__.__name__), self.name, self.value)

    def write_tag(self, buf):
        buf.write(chr(self.tagID))

    def write_name(self, buf):
        if self.name is not None:
            write_string(self.name, buf)

    def write_value(self, buf):
        try:
            buf.write(self.fmt.pack(self.value))
        except:
            print "ERROR: could not save the following NBT tag:"
            print self.json()
            raise

    def isCompound(self):
        return False

    def eq(self,other):
        if type(other) in [
            TAG_Compound,
            TAG_List,
            TAG_Byte_Array,
            TAG_Long_Array,
            TAG_Int_Array
        ]:
            return False
        return self.value == other.value

    def ne(self,other):
        if type(other) in [
            TAG_Compound,
            TAG_List,
            TAG_Byte_Array,
            TAG_Long_Array,
            TAG_Int_Array
        ]:
            return True
        return self.value != other.value

    def issubset(self,other):
        return self.eq(other)

    def update(self,newTag):
        self.value = newTag.value


class TAG_Byte(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_BYTE
    fmt = struct.Struct(">b")
    data_type = int

    def json(self,sort=None):
        """ Convert TAG_Byte to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"
        return prefix + unicode(self.value) + u"b"


class TAG_Short(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_SHORT
    fmt = struct.Struct(">h")
    data_type = int

    def json(self,sort=None):
        """ Convert TAG_Short to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"
        return prefix + unicode(self.value) + u"s"


class TAG_Int(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_INT
    fmt = struct.Struct(">i")
    data_type = int

    def json(self,sort=None):
        """ Convert TAG_Int to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"
        return prefix + unicode(self.value)


class TAG_Long(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_LONG
    fmt = struct.Struct(">q")
    data_type = long

    def json(self,sort=None):
        """ Convert TAG_Long to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"
        return prefix + unicode(self.value) + u"l"


class TAG_Float(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_FLOAT
    fmt = struct.Struct(">f")
    data_type = float

    def json(self,sort=None):
        """ Convert TAG_Float to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"

        return prefix + unicode(self.value) + u"f"


class TAG_Double(TAG_Value):
    __slots__ = ('_name', '_value')
    tagID = TAG_DOUBLE
    fmt = struct.Struct(">d")
    data_type = float

    def json(self,sort=None):
        """ Convert TAG_Double to JSON string """
        prefix = u""
        if len(self.name) != 0:
            prefix = self.name + u":"

        return prefix + unicode(self.value) + u"d"


class TAG_Byte_Array(TAG_Value):
    """Like a string, but for binary data. Four length bytes instead of
    two. Value is a numpy array, and you can change its elements"""

    tagID = TAG_BYTE_ARRAY

    def __init__(self, value=None, name=""):
        if value is None:
            value = zeros(0, self.dtype)
        self.name = name
        self.value = value

    def __repr__(self):
        return "<%s name=%s length=%d>" % (self.__class__, self.name, len(self.value))

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        return array(value, self.dtype)

    dtype = numpy.dtype('uint8')

    @classmethod
    def load_from(cls, ctx):
        data = ctx.data[ctx.offset:]
        (string_len,) = TAG_Int.fmt.unpack_from(data)
        value = fromstring(data[4:string_len * cls.dtype.itemsize + 4], cls.dtype)
        self = cls(value)
        ctx.offset += string_len * cls.dtype.itemsize + 4
        return self

    def write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack(">I%ds" % (len(value_str),), self.value.size, value_str))

    def json(self,sort=None):
        """ Convert TAG_Byte_Array to JSON string """
        result = u"[B;"
        if len(self.name) != 0:
            result = self.name + u":[B;"
        # TODO parsing needs to be double checked
        for val in self.value:
            result += unicode(val) + u"b,"
        if result[-1] == u",":
            result = result[:-1]
        return result + u"]"

    def eq(self,other):
        if type(other) not in [
            TAG_Byte_Array,
            TAG_Long_Array,
            TAG_Int_Array
        ]:
            return False
        if len(self) != len(other):
            return False
        for i in range(len(self)):
            if self.value[i].ne(other.value[i]):
                return False
        return True

    def ne(self,other):
        if type(other) not in [
            TAG_Byte_Array,
            TAG_Long_Array,
            TAG_Int_Array
        ]:
            return True
        if len(self) != len(other):
            return True
        for i in range(len(self)):
            if self.value[i].ne(other.value[i]):
                return True
        return False


class TAG_Int_Array(TAG_Byte_Array):
    """An array of big-endian 32-bit integers"""
    tagID = TAG_INT_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u4')

    def json(self,sort=None):
        """ Convert TAG_Int_Array to JSON string """
        result = u"[I;"
        if len(self.name) != 0:
            result = self.name + u":[I;"
        # TODO parsing needs to be double checked
        for val in self.value:
            result += unicode(val) + u","
        if result[-1] == u",":
            result = result[:-1]
        return result + u"]"

class TAG_Long_Array(TAG_Int_Array):
    """An array of big-endian 64-bit integers. This is official - short arrays are not."""
    tagID = TAG_LONG_ARRAY
    __slots__ = ('_name', '_value')
    dtype = numpy.dtype('>u8')

    def json(self,sort=None):
        """ Convert TAG_Long_Array to JSON string """
        result = u"[L;"
        if len(self.name) != 0:
            result = self.name + u":[L;"
        # TODO parsing needs to be double checked
        for val in self.value:
            result += unicode(val) + u"l,"
        if result[-1] == ",":
            result = result[:-1]
        return result + u"]"


class TAG_String(TAG_Value):
    """String in UTF-8
    The value parameter must be a 'unicode' or a UTF-8 encoded 'str'
    """

    tagID = TAG_STRING

    def __init__(self, value="", name=""):
        if name:
            self.name = name
        self.value = value

    _decodeCache = {}

    __slots__ = ('_name', '_value')

    def data_type(self, value):
        if isinstance(value, unicode):
            return value
        else:
            decoded = self._decodeCache.get(value)
            if decoded is None:
                decoded = value.decode('utf-8')
                self._decodeCache[value] = decoded

            return decoded

    @classmethod
    def load_from(cls, ctx):
        value = load_string(ctx)
        return cls(value)

    def write_value(self, buf):
        try:
            write_string(self._value, buf)
        except:
            print "ERROR: could not save the following NBT tag:"
            print self.json()
            raise

    def decode(self, charset):
        self.value.decode(charset)

    def json(self,sort=None):
        """ Convert TAG_String to JSON string """
        try:
            ownName = self.name
            if ownName == "":
                prefix = u'"'
            else:
                prefix = self.name + u':"'
        except AttributeError:
            prefix = u'"'

        return prefix + self.value.replace(u'\\',u'\\\\').replace(u'\n',u'\\n"').replace(u'"',u'\\"') + u'"'

string_len_fmt = struct.Struct(">H")

def load_string(ctx):
    data = ctx.data[ctx.offset:]
    (string_len,) = string_len_fmt.unpack_from(data)

    value = data[2:string_len + 2].tostring()
    ctx.offset += string_len + 2
    return value


def write_string(string, buf):
    if (string is None):
        encoded = "".encode('utf-8')
    else:
        encoded = string.encode('utf-8')
    buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))


# noinspection PyMissingConstructor

class TAG_Compound(TAG_Value, collections.MutableMapping):
    """A heterogenous list of named tags. Names must be unique within
    the TAG_Compound. Add tags to the compound using the subscript
    operator [].    This will automatically name the tags."""

    tagID = TAG_COMPOUND

    ALLOW_DUPLICATE_KEYS = False

    __slots__ = ('_name', '_value')

    def __init__(self, value=None, name=""):
        self.value = value or []
        self.name = name

    def __repr__(self):
        return "<%s name='%s' keys=%r>" % (unicode(self.__class__.__name__), self.name, self.keys())

    def data_type(self, val):
        for i in val:
            self.check_value(i)
        return list(val)

    @staticmethod
    def check_value(val):
        if not isinstance(val, TAG_Value):
            raise TypeError("Invalid type for TAG_Compound element: %s" % val.__class__.__name__)
        if not val.name:
            raise ValueError("Tag needs a name to be inserted into TAG_Compound: %s" % val)

    @classmethod
    def load_from(cls, ctx):
        self = cls()
        while ctx.offset < len(ctx.data):
            tag_type = ctx.data[ctx.offset]
            ctx.offset += 1

            if tag_type == 0:
                break

            tag_name = load_string(ctx)
            tag = tag_classes[tag_type].load_from(ctx)
            tag.name = tag_name

            self._value.append(tag)

        return self

    def save(self, filename_or_buf=None, compressed=True):
        """
        Save the TAG_Compound element to a file. Since this element is the root tag, it can be named.

        Pass a filename to save the data to a file. Pass a file-like object (with a read() method)
        to write the data to that object. Pass nothing to return the data as a string.
        """
        if self.name is None:
            self.name = ""

        buf = StringIO()
        self.write_tag(buf)
        self.write_name(buf)
        self.write_value(buf)
        data = buf.getvalue()

        if compressed:
            gzio = StringIO()
            gz = gzip.GzipFile(fileobj=gzio, mode='wb')
            gz.write(data)
            gz.close()
            data = gzio.getvalue()

        if filename_or_buf is None:
            return data

        if isinstance(filename_or_buf, basestring):
            f = file(filename_or_buf, "wb")
            f.write(data)
        else:
            filename_or_buf.write(data)

    def write_value(self, buf):
        for tag in self.value:
            tag.write_tag(buf)
            tag.write_name(buf)
            tag.write_value(buf)

        buf.write("\x00")

    # --- collection functions ---

    def __getitem__(self, key):
        # hits=filter(lambda x: x.name==key, self.value)
        # if(len(hits)): return hits[0]
        for tag in self.value:
            if tag.name == key:
                return tag
        raise KeyError("Key {0} not found".format(key))

    def __iter__(self):
        return itertools.imap(lambda x: x.name, self.value)

    def __contains__(self, key):
        return key in map(lambda x: x.name, self.value)

    def __len__(self):
        return self.value.__len__()

    def __setitem__(self, key, item):
        """Automatically wraps lists and tuples in a TAG_List, and wraps strings
        and unicodes in a TAG_String."""
        if isinstance(item, (list, tuple)):
            item = TAG_List(item)
        elif isinstance(item, basestring):
            item = TAG_String(item)

        item.name = key
        self.check_value(item)

        # remove any items already named "key".
        if not self.ALLOW_DUPLICATE_KEYS:
            self._value = filter(lambda x: x.name != key, self._value)

        self._value.append(item)

    def __delitem__(self, key):
        self.value.__delitem__(self.value.index(self[key]))

    def add(self, value):
        if value.name is None:
            raise ValueError("Tag %r must have a name." % value)

        self[value.name] = value

    def get_all(self, key):
        return [v for v in self._value if v.name == key]

    def isCompound(self):
        return True


    def json(self,sort=None):
        """ Convert TAG_Compound to JSON string """
        if self.name == "":
            result = u"{"
        else:
            result = self.name + u":{"
        if sort==None:
            for key in self.keys():
                result += self[key].json(sort) + u","
        elif (
            (type(sort) == list) or
            (type(sort) == tuple)
        ):
            for sortKey in sort:
                if sortKey in self.keys():
                    result += self[sortKey].json(sort) + u","
            for key in sorted(self.keys()):
                if key not in sort:
                    result += self[key].json(sort) + u","
        else:
            for key in sorted(self.keys()):
                result += self[key].json(sort) + u","
        if result[-1] == u",":
            result = result[:-1]
        return result + u"}"

    def eq(self,other):
        if type(other) != TAG_Compound:
            return False
        if len(self) != len(other):
            return False
        try:
            for aKey in self.keys():
                if self[aKey].ne(other[aKey]):
                    return False
        except:
            return False
        return True

    def ne(self,other):
        if type(other) != TAG_Compound:
            return True
        if len(self) != len(other):
            return True
        try:
            for aKey in self.keys():
                if self[aKey].ne(other[aKey]):
                    return True
        except:
            return True
        return False

    def issubset(self,other):
        if type(other) != TAG_Compound:
            return False
        try:
            for aKey in self.keys():
                if not self[aKey].issubset(other[aKey]):
                    return False
        except:
            return False
        return True

    def update(self,newTag):
        for aKey in newTag.keys():
            if aKey not in self:
                json = newTag[aKey].json()
                newSubTag = json_to_tag(json)
                if newSubTag.name != aKey:
                    newSubTag = newSubTag[aKey]
                self[aKey] = newSubTag
            else:
                self[aKey].update(newTag[aKey])

class TAG_List(TAG_Value, collections.MutableSequence):
    """A homogenous list of unnamed data of a single TAG_* type.
    Once created, the type can only be changed by emptying the list
    and adding an element of the new type. If created with no arguments,
    returns a list of TAG_Compound

    Empty lists in the wild have been seen with type TAG_Byte"""

    tagID = 9

    def __init__(self, value=None, name="", list_type=TAG_BYTE):
        # can be created from a list of tags in value, with an optional
        # name, or created from raw tag data, or created with list_type
        # taken from a TAG class or instance
        self.name = name
        self.list_type = list_type
        self.value = value or []

    __slots__ = ('_name', '_value')

    def __repr__(self):
        return "<%s name='%s' list_type=%r length=%d>" % (self.__class__.__name__, self.name,
                                                          tag_classes[self.list_type],
                                                          len(self))

    def data_type(self, val):
        if val:
            self.list_type = val[0].tagID
        assert all([x.tagID == self.list_type for x in val])
        return list(val)

    @classmethod
    def load_from(cls, ctx):
        self = cls()
        self.list_type = ctx.data[ctx.offset]
        ctx.offset += 1

        (list_length,) = TAG_Int.fmt.unpack_from(ctx.data, ctx.offset)
        ctx.offset += TAG_Int.fmt.size

        for i in xrange(list_length):
            tag = tag_classes[self.list_type].load_from(ctx)
            self.append(tag)

        return self

    def write_value(self, buf):
        buf.write(chr(self.list_type))
        buf.write(TAG_Int.fmt.pack(len(self.value)))
        for i in self.value:
            i.write_value(buf)

    def check_tag(self, value):
        if value.tagID != self.list_type:
            raise TypeError("Invalid type %s for TAG_List(%s)" % (value.__class__, tag_classes[self.list_type]))

    # --- collection methods ---

    def __iter__(self):
        return iter(self.value)

    def __contains__(self, tag):
        return tag in self.value

    def __getitem__(self, index):
        return self.value[index]

    def __len__(self):
        return len(self.value)

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            for tag in value:
                self.check_tag(tag)
        else:
            self.check_tag(value)

        self.value[index] = value

    def __delitem__(self, index):
        del self.value[index]

    def insert(self, index, value):
        if len(self) == 0:
            self.list_type = value.tagID
        else:
            self.check_tag(value)

        value.name = ""
        self.value.insert(index, value)

    def json(self,sort=None):
        """ Convert TAG_List to JSON string """
        if self.name == "":
            result = u"["
        else:
            result = self.name + u":["
        # TODO parsing needs to be double checked
        for i in self.value:
            result += i.json(sort) + u","
        if result[-1] == u",":
            result = result[:-1]
        return result + u"]"

    def eq(self,other):
        if type(other) != TAG_List:
            return False
        if len(self.value) != len(other.value):
            return False
        for i in range(len(self.value)):
            if self[i].ne(other[i]):
                return False
        return True

    def ne(self,other):
        if type(other) != TAG_List:
            return True
        if len(self.value) != len(other.value):
            return True
        for i in range(len(self.value)):
            if self[i].ne(other[i]):
                return True
        return False

    def issubset(self,other):
        if type(other) != TAG_List:
            return False
        for i in range(len(self.value)):
            # Order insensitive
            # Read this as:
            # if this list element is a subset of none of other's elements:
            #   then this list is not a subset of the other list
            if not any(self[i].issubset(other[j]) for j in range(len(other.value))):
                return False
        return True

tag_classes = {}

for c in (
TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String, TAG_Byte_Array, TAG_List, TAG_Compound,
TAG_Int_Array, TAG_Long_Array):
    tag_classes[c.tagID] = c


def gunzip(data):
    return gzip.GzipFile(fileobj=StringIO(data)).read()


def try_gunzip(data):
    try:
        data = gunzip(data)
    except IOError, zlib.error:
        pass
    return data


def load(filename="", buf=None):
    """
    Unserialize data from an NBT file and return the root TAG_Compound object. If filename is passed,
    reads from the file, otherwise uses data from buf. Buf can be a buffer object with a read() method or a string
    containing NBT data.
    """
    if filename:
        buf = file(filename, "rb")

    if hasattr(buf, "read"):
        buf = buf.read()

    return _load_buffer(try_gunzip(buf))


class load_ctx(object):
    pass


def _load_buffer(buf):
    if isinstance(buf, str):
        buf = fromstring(buf, 'uint8')
    data = buf

    if not len(data):
        raise NBTFormatError("Asked to load root tag of zero length")

    tag_type = data[0]
    if tag_type != 10:
        magic = data[:4]
        raise NBTFormatError('Not an NBT file with a root TAG_Compound '
                             '(file starts with "%s" (0x%08x)' % (magic.tostring(), magic.view(dtype='uint32')))

    ctx = load_ctx()
    ctx.offset = 1
    ctx.data = data

    tag_name = load_string(ctx)
    tag = TAG_Compound.load_from(ctx)
    # For PE debug
    try:
        tag.name = tag_name
    except:
        pass

    return tag


__all__ = [a.__name__ for a in tag_classes.itervalues()] + ["load", "gunzip"]


@contextmanager
def littleEndianNBT():
    """
    Pocket edition NBT files are encoded in little endian, instead of big endian.
    This sets all the required paramaters to read little endian NBT, and makes sure they get set back after usage.
    :return: None
    """

    # We need to override the function to access the hard-coded endianness.
    def override_write_string(string, buf):
        encoded = string.encode('utf-8')
        buf.write(struct.pack("<h%ds" % (len(encoded),), len(encoded), encoded))

    def reset_write_string(string, buf):
        encoded = string.encode('utf-8')
        buf.write(struct.pack(">h%ds" % (len(encoded),), len(encoded), encoded))

    def override_byte_array_write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack("<I%ds" % (len(value_str),), self.value.size, value_str))

    def reset_byte_array_write_value(self, buf):
        value_str = self.value.tostring()
        buf.write(struct.pack(">I%ds" % (len(value_str),), self.value.size, value_str))

    global string_len_fmt
    string_len_fmt = struct.Struct("<H")
    TAG_Byte.fmt = struct.Struct("<b")
    TAG_Short.fmt = struct.Struct("<h")
    TAG_Int.fmt = struct.Struct("<i")
    TAG_Long.fmt = struct.Struct("<q")
    TAG_Float.fmt = struct.Struct("<f")
    TAG_Double.fmt = struct.Struct("<d")
    TAG_Int_Array.dtype = numpy.dtype("<u4")
    TAG_Long_Array.dtype = numpy.dtype("<u8")
    global write_string
    write_string = override_write_string
    TAG_Byte_Array.write_value = override_byte_array_write_value
    yield
    string_len_fmt = struct.Struct(">H")
    TAG_Byte.fmt = struct.Struct(">b")
    TAG_Short.fmt = struct.Struct(">h")
    TAG_Int.fmt = struct.Struct(">i")
    TAG_Long.fmt = struct.Struct(">q")
    TAG_Float.fmt = struct.Struct(">f")
    TAG_Double.fmt = struct.Struct(">d")
    TAG_Int_Array.dtype = numpy.dtype(">u4")
    TAG_Long_Array.dtype = numpy.dtype(">u8")
    write_string = reset_write_string
    TAG_Byte_Array.write_value = reset_byte_array_write_value


def nested_string(tag, indent_string="  ", indent=0):
    result = ""

    if tag.tagID == TAG_COMPOUND:
        result += 'TAG_Compound({\n'
        indent += 1
        for key, value in tag.iteritems():
            result += indent_string * indent + '"%s": %s,\n' % (key, nested_string(value, indent_string, indent))
        indent -= 1
        result += indent_string * indent + '})'

    elif tag.tagID == TAG_LIST:
        result += 'TAG_List([\n'
        indent += 1
        for index, value in enumerate(tag):
            result += indent_string * indent + nested_string(value, indent_string, indent) + ",\n"
        indent -= 1
        result += indent_string * indent + '])'

    else:
        result += "%s(%r)" % (tag.__class__.__name__, tag.value)

    return result


try:
    # noinspection PyUnresolvedReferences
    # Inhibit the _nbt import if we're debugging the PE support errors, because we need to get information concerning NBT malformed data...
#     if DEBUG_PE or '--debug-pe' in sys.argv:
#         log.warning("PE support debug mode is activated. Using full Python NBT support!")
#     else:
        from _nbt import (load, TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double, TAG_String,
                          TAG_Byte_Array, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Long_Array, NBTFormatError,
                          littleEndianNBT, nested_string, gunzip, hexdump)
except ImportError as err:
    log.error("Failed to import Cythonized nbt file. Running on (very slow) pure-python nbt fallback.")
    log.error("(Did you forget to run 'setup.py build_ext --inplace'?)")
    log.error("%s"%err)


################################################################################
# BEGIN JSON TO TAG PARSER

"""
Oh dear, this is one big mess of code. It used to be much worse. It works for
strict json to nbt parsing, but doesn't handle some of the more leniant uses
that Minecraft allows; for instance, raw json text starting like:

["",{...}]

This isn't read right, as NBT only allows list elements to be the same type.
In this case, the starting quotes should be ignored, but aren't atm.

Anyways, good enough for my needs for now.
"""

def _jsonParser_resetCurState(state):
    state["name"] = ''
    state["native"] = None
    state["tag"] = None

def _jsonParser_storeValue(state):
    # Ensure we have a value to store
    if state["native"] is None:
        return

    # Determine how to index where the new value goes,
    # and put it there.
    thisTagType = type(state["tag"])
    isContainer = (
        thisTagType is TAG_Compound or
        thisTagType is TAG_List or
        thisTagType is TAG_Byte_Array or
        thisTagType is TAG_Int_Array or
        thisTagType is TAG_Long_Array
    )

    if not isContainer:
        # type and value must be determined
        state["tag"] = _jsonParser_jsonToTag(state["native"])
    state["tag"].name = state["name"]

    # Determine and use the correct function
    # to store the new tag in its container
    parentTagType = type(state["stackTag"][-1])
    parentIsArray = (
        parentTagType is TAG_Byte_Array or
        parentTagType is TAG_Int_Array or
        parentTagType is TAG_Long_Array
    )

    if parentTagType is TAG_Compound:
        state["stackTag"][-1].add(state["tag"])
    elif parentTagType is TAG_List:
        state["stackTag"][-1].append(state["tag"])
    elif parentIsArray:
        array = state["stackTag"][-1].value
        value = state["tag"].value
        array = numpy.insert(array,len(array),value)
        state["stackTag"][-1].value = array
    else:
        raise JSONFormatError("Invalid tag container type.")

    # If the new value is a container, go inside it.
    if isContainer:
        state["stackTag"].append(state["tag"])

    # Reset the current state.
    _jsonParser_resetCurState(state)

def _jsonParser_exitNestLevel(state):
    _jsonParser_storeValue(state)
    state["stackTag"].pop()

def _jsonParser_jsonToTag(json):
    """
    Converts a command-ready json string into an NBT tag.
    The NBT tag returned may contain other NBT tags.
    Default type assumptions taken from:
    https://minecraft.gamepedia.com/Commands#Data_tags
    """
    # Handle the special case of booleans, which are really bytes
    if json.lower() == "true":
        json = "1b"
    if json.lower() == "false":
        json = "0b"

    # Grab the last character
    tailChar = json[-1]
    sansTail = json[:-1]
    sansQuotes = json
    if (
    ( json[0] == '"' )
    and ( json[-1] == '"' )
    ):
        sansQuotes = json[1:-1]

    # Split these by type
    if tailChar.lower() == "b":
        try:
            return TAG_Byte(sansTail)
        except:
            return TAG_String(sansQuotes)
    elif tailChar.lower() == "s":
        try:
            return TAG_Short(sansTail)
        except:
            return TAG_String(sansQuotes)
    elif tailChar.lower() == "l":
        try:
            return TAG_Long(sansTail)
        except:
            return TAG_String(sansQuotes)
    elif tailChar.lower() == "f":
        try:
            return TAG_Float(sansTail)
        except:
            return TAG_String(sansQuotes)
    elif tailChar.lower() == "d":
        try:
            return TAG_Double(sansTail)
        except:
            return TAG_String(sansQuotes)
    elif tailChar == '"':
        return TAG_String(sansQuotes.replace(u'\\"',u'"').replace(u'\\n',u'\n"').replace(u'\\\\',u'\\'))
    #elif determine from context
    #    ie, if we know that "Pos" is a list of doubles,
    #    but they have no decimal point or d suffix
    elif '.' in json:
        try:
            return TAG_Double(json)
        except:
            return TAG_String(sansQuotes)
    else:
        try:
            return TAG_Int(json)
        except:
            return TAG_String(sansQuotes)

def json_to_tag(json):
    startQuote = None
    backslashFound = False

    listTypeCharsLeft = 0

    state = {}

    state["name"]  = ''
    state["native"] = None
    state["tag"] = None

    result = TAG_Compound()
    debug = ''

    # This stack points to a container tag
    state["stackTag"] = [result]

    # Begin parse
    for i,c in enumerate(json):
        # TODO Debug for testing the whitespace handler
        #print c,
        # i is the index of character c in json
        if listTypeCharsLeft > 0:
            debug += c
            listTypeCharsLeft -= 1
            continue
        elif backslashFound:
            # Previous character was \, ignore this character
            debug += '?'
            backslashFound = False
            continue
        elif c == '\\':
            # This charcter is a \, ignore next character
            debug += '\\'
            backslashFound = True
            continue
        elif c == '"':
            # Quote found, is it start or end?
            if startQuote is not None:
                # It is an end quote, accept the value
                # Include the quote marks to identify type

                # Note that this might in fact be the tag NAME,
                # not the tag VALUE. This will be updated when a
                # colon signifies the value starts next, or when
                # it is clear the end of the tag has arrived.
                debug += '"'
                stringValue = json[startQuote: i + 1]
                state["native"] = stringValue
                startQuote = None
                continue
            else:
                # It is a start quote, record the location
                debug += "'"
                startQuote = i
                continue
        elif startQuote is not None:
            # We're inside quotes; other cases should be ignored.
            debug += '~'
            continue
        elif c == '{':
            # New compound tag
            if i == 0:
                # This is the starting tag, and accounted for.
                continue
            else:
                # This tag is not accounted for.
                debug += '{'
                state["native"] = {}
                state["tag"] = TAG_Compound()
                _jsonParser_storeValue(state)
                continue
        elif c == '[':
            # New list tag
            debug += '['
            state["native"] = []
            typeId = json[i+1:i+3]
            if typeId == u'B;':
                state["tag"] = TAG_Byte_Array()
                listTypeCharsLeft = 2
            elif typeId == u'I;':
                state["tag"] = TAG_Int_Array()
                listTypeCharsLeft = 2
            elif typeId == u'L;':
                state["tag"] = TAG_Long_Array()
                listTypeCharsLeft = 2
            else:
                state["tag"] = TAG_List()
            _jsonParser_storeValue(state)
            continue
        elif c == ']':
            # End of list tag
            debug += ']'
            _jsonParser_exitNestLevel(state)
            continue
        elif c == '}':
            # End of compound tag
            debug += '}'
            _jsonParser_exitNestLevel(state)
            continue
        elif c == ':':
            # LHS is name, RHS is value.
            # If missing, name is not present.
            debug += ':'
            if state["name"] == '':
                state["name"] = state["native"]
            else:
                state["name"] += ":" + state["native"]
            state["native"] = None
            continue
        elif c == ',':
            # Tag separator for lists and compounds
            debug += ','
            _jsonParser_storeValue(state)
            continue
        else:
            # Non-string non-container tag
            debug += '-'
            if state["native"] is None:
                # TODO test this; should allow for json files with whitespace
                #if c in string.whitespace:
                #    continue
                state["native"] = ""
            state["native"] += c
    if state["native"] is not None:
        _jsonParser_storeValue(state)

    return result


