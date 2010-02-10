"""
Dtella - Utility Functions
Copyright (C) 2008  Dtella Labs (http://www.dtella.org)
Copyright (C) 2008  Paul Marks
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Andrew Cooper <amc96>, Ximin Luo <xl269> (@cam.ac.uk)

$Id$

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import struct
import random
import sys
import fpformat
import re
import array
import os
import os.path

from twisted.python.runtime import seconds
import twisted.python.log

# Import md5 for everyone, Python 2.4+
try:
    from hashlib import md5
except ImportError:
    from md5 import md5


def randbytes(n):
    return ''.join([chr(random.randint(0,255)) for i in range(n)])


def cmpify_version(ver):
    # Given a version string, turn it into something comparable.

    ver_re = re.compile("([0-9]*)(.*)$")

    ver_parts = []

    for part in ver.split('.'):
        m = ver_re.match(part)
        spart = m.group(2)
        try:
            ipart = int(m.group(1))
        except ValueError:
            ver_parts.append((spart,))
        else:
            ver_parts.append((ipart, spart))

    return tuple(ver_parts)


def hostnameMatch(hostname, regexes):
    # Convert a hostname into a human-readable location name.
    if hostname:
        for (r, vals) in regexes:
            s = re.compile(r).match(hostname)
            if s:
                try:
                    return vals[s.group(1)]
                except KeyError:
                    pass
    return "???"


def validateNick(nick):
    if len(nick) < 2:
        return "too short"

    if len(nick) > 30:
        return "too long"

    if not nick[0].isalpha():
        return "must start with a letter"

    chars = ("-0123456789"
             "ABCDEFGHIJKLMNOPQRSTUVWXYZ[]^_`"
             "abcdefghijklmnopqrstuvwxyz{}"
             "!\"#%&'()*+,./:;=?@\\~")

    for c in nick:
        if c not in chars:
            return "contains an invalid character: '%s'" % c

    return ''


# Lock2Key algorithm from the DC++ wiki
# by Benjamin Bruheim, optimized by Dody Suria Wijaya (25% faster)
def lock2key(lock):
    "Generates response to $Lock challenge from Direct Connect Servers"
    lock = array.array('B', lock)
    ll = len(lock)
    key = list('0'*ll)
    for n in xrange(1,ll):
        key[n] = lock[n]^lock[n-1]
    key[0] = lock[0] ^ lock[-1] ^ lock[-2] ^ 5
    for n in xrange(ll):
        key[n] = ((key[n] << 4) | (key[n] >> 4)) & 255
    result = ""
    for c in key:
        if c in (0, 5, 36, 96, 124, 126):
            result += "/%%DCN%.3i%%/" % c
        else:
            result += chr(c)
    return result


class RandSet(object):

    def __init__(self, init=()):
        self.map = {}
        self.set = set()
        for o in init:
            self.add(o)

    def __contains__(self, o):
        return (o in self.map)

    def __nonzero__(self):
        return bool(self.map)

    def __len__(self):
        return len(self.map)

    def add(self, o):
        # Add o to the set
        if o not in self.map:
            r = (random.random(), o)
            self.map[o] = r
            self.set.add(r)

    def discard(self, o):
        # Drop o from the set
        try:
            r = self.map.pop(o)
        except KeyError:
            return
        self.set.remove(r)

    def pop(self):
        # Get random element fron the set
        o = self.set.pop()[1]
        del self.map[o]
        return o

    def clear(self):
        self.map.clear()
        self.set.clear()

    def peek(self):
        o = self.pop()
        self.add(o)
        return o


def dcall_discard(obj, attr):
    # If a dcall exists, cancel it, and set it to None
    dcall = getattr(obj, attr)
    if dcall:
        dcall.cancel()
        setattr(obj, attr, None)


def dcall_timeleft(d):
    return max(0, d.getTime() - seconds())


def get_os():
    os_map = [('bsd','B'), ('cygwin','C'), ('linux','L'),
              ('darwin','M'), ('sun','S'), ('win','W')]

    p = sys.platform.lower()

    for key,value in os_map:
        if key in p:
            return value

    return '?'


def get_version_string():
    import dtella.build_config as build
    return "Dt:%s/%s" % (build.version, get_os())


def get_user_path(filename):
    path = os.path.expanduser("~/.dtella")
    if path[:1] == '~':
        # Can't get a user directory, just save to cwd.
        return filename
    else:
        try:
            if not os.path.exists(path):
                os.mkdir(path)
        except OSError:
            twisted.python.log.err()

        return os.path.join(path, filename)

def stdlines(text):
    return text.replace('\r\n', '\n').replace('\r','\n')

def dc_escape(text):
    return text.replace('|','&#124;').replace('$','&#36;')

def dc_unescape(text):
    return text.replace('&#124;','|').replace('&#36;','$')

def adc_escape(text):
    return text.replace('\\', '\\\\').replace('\n','\\n').replace(' ', '\\s')

def adc_unescape(text):
    return text.replace('\\\\', '\0').replace('\\n','\n').replace('\\s',' ').replace('\0','\\')

def adc_infostring(infdict):
    return ' '.join(["%s%s" % (i, adc_escape(d)) for (i,d) in infdict.iteritems()])

def adc_locdes(infdict):
    if 'LO' not in infdict:
        return infdict

    loc = infdict['LO']
    i = loc.find('|')
    if i >= 0:
        loc = loc[:i] + loc[i+1:]

    infd = dict(infdict)
    if 'DE' in infd:
        infd['DE'] = "[%s] %s" % (loc, infd['DE'])
    else:
        infd['DE'] = "[%s]" % (loc)

    return infd

def adc_infodict(infstring):
    inf = {}
    for i in infstring.split(' '):
        inf[i[:2]] = adc_unescape(i[2:])
    return inf

def split_info(info):
    # Split a MyINFO string
    # [0:'description<tag>', 1:' ', 2:'speed_', 3:'email', 4:'sharesize', 5:'']

    if info:
        info = info.split('$',6)
        if len(info) == 6:
            return info

    # Too many or too few parts
    raise ValueError


def parse_dtella_tag(info):

    # Break up info string
    try:
        info = split_info(info)

    except ValueError:
        # This could be an 'offline info'.
        if (info[:4], info[-1:]) == ('<Dt:','>'):
            return info[1:-1]

    else:
        # Properly formatted; extract tag
        desc, tag = split_tag(info[0])
        if tag:
            try:
                pos = tag.rindex("Dt:")
                return tag[pos:]
            except ValueError:
                pass

    # Couldn't find dtella tag
    return ""


def parse_incoming_info(info):
    # Pull the location and share size out of an info string
    # Returns dcinfo, location, shared

    info = info.replace('\r','').replace('\n','')

    # Break up info string
    try:
        info = split_info(info)
    except ValueError:
        return ("", "", 0)

    # Check if the location has a user-specified suffix
    try:
        location, suffix = info[2][:-1].split('|', 1)
        suffix = suffix[:8]
    except ValueError:
        # No separator, use entire connection field as location name
        location = info[2][:-1]
    else:
        # Keep location, and splice out the separator
        info[2] = location + suffix + info[2][-1:]

    # Get share size
    try:
        shared = int(info[4])
    except ValueError:
        shared = 0

    return ('$'.join(info), location, shared)


def split_tag(desc):
    # Break 'description<tag>' into ('description','tag')
    tag = ''
    if desc[-1:] == '>':
        try:
            pos = desc.rindex('<')
            tag = desc[pos+1:-1]
            desc = desc[:pos]
        except ValueError:
            pass
    return desc, tag


# Minimum Dtella needed to retain the SSL MyINFO flag.
SSLHACK_VERSION = cmpify_version("1.2.4")

def SSLHACK_filter_flags(info_str):
    # SSLHACK: The 'speed' field contains a flags byte, of which bit 0x10
    #          indicates SSL capability for some DC clients.  If this is an
    #          older Dtella node which doesn't understand SSL requests, we
    #          clear the bit, so our DC client won't try to initiate an
    #          SSL connection with it.

    # Ignore new-enough Dtella versions.
    dttag = parse_dtella_tag(info_str)
    if cmpify_version(dttag[3:]) >= SSLHACK_VERSION:
        return info_str

    try:
        info = split_info(info_str)
    except ValueError:
        return info_str

    try:
        flags, = struct.unpack('!B', info[2][-1:])
    except struct.error:
        return info_str

    if flags & 0x10:
        flags ^= 0x10
        info[2] = info[2][:-1] + struct.pack('!B', flags)
        return '$'.join(info)

    return info_str

def b32pad(n):
    _, leftover = divmod(len(n)-1, 8)
    n += (7-leftover)*'='
    return n

def format_bytes(n):
    # Convert an integer into a Bytes representation
    n = float(n)
    suffix = ('B','KiB','MiB','GiB','TiB','PiB')
    i = 0
    while n >= 1024 and i < 5:
        n /= 1024
        i+=1

    if i:
        return "%s %s" % (fpformat.fix(n, 2), suffix[i])
    else:
        return "%d %s" % (n, suffix[i])


def parse_bytes(s):
    # Might raise ValueError

    mult = 1
    if s:
        s = s.strip()
        if s[-2:].upper() == 'IB':
            s = s[:-2]
        elif s[-1:].upper() == 'B':
            s = s[:-1]

        i = 'KMGT'.find(s[-1].upper())
        if i > -1:
            s = s[:-1]
            mult = 1024 ** (i+1)

    return int(float(s) * mult)


def word_wrap(line, max_len=80):

    lines = []

    words = line.split(' ')
    i = 0

    while i < len(words):
        cur_line = None

        while i < len(words):
            word = words[i]

            if cur_line is None:
                cur_line = ''
            else:
                word = ' ' + word
                if len(cur_line) + len(word) > max_len:
                    break

            cur_line += word
            i += 1

        lines.append(cur_line)

    return lines


confignames = {}

def set_cfg(modname, cfg):
    if modname in sys.modules:
        # Can't think of a better exception, oh well
        raise ImportError("%s has already been imported; set_cfg() will have no effect." % modname)

    global confignames
    confignames[modname] = cfg


def load_cfg(modname, prefix):
    global confignames

    # These are python 2.6 modules; we can remove them from the dtella source tree
    # when python 2.5 is obsolete.
    from ast import literal_eval
    from pkgutil import get_data

    wrotenew = False

    if modname in confignames and confignames[modname]:
        cfgname = prefix + "_" +  confignames[modname]
        cfgfile = get_user_path(cfgname + ".cfg")

        if not os.path.exists(cfgfile):
            # copy default config if user doesn't have an override
            fp = open(cfgfile, 'w+')
            for i in get_data(modname, prefix + ".cfg"):
                fp.write(i)
            fp.close()
            wrotenew = True

        cfgfp = open(cfgfile)

    else:
        cfgname = prefix
        cfgfile = get_user_path(cfgname + ".cfg")
        if os.path.exists(cfgfile):
            print "--- Note: unused obsolete config in %s" % cfgfile
            print "--- You might want to remove it to reduce clutter."

        import StringIO
        cfgfp = StringIO.StringIO(get_data(modname, prefix + ".cfg"))

    #print "loading %s from %s" % (modname, cfgfile)
    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.readfp(cfgfp)
    for i in config.sections():
        for k, v in config.items(i):
            try:
                value = literal_eval(v)
            except (ValueError, SyntaxError):
                value = v
            #print "%s = %s %s" % (k, value.__class__, value)
            setattr(sys.modules[modname], k, value)

    # if we didn't explicity call set_cfg then don't save the config file.
    # this means that we can eg. check for the existence of bridge_config by
    # trying to import it, without any side effects. (reverse_dns does this)
    if modname not in confignames and wrotenew:
        os.remove(cfgfile)

    return cfgname


def CHECK(truth):
    if not truth:
        raise AssertionError("CHECK failed")
