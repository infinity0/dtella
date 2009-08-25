"""
Dtella - State File Management Module
Copyright (C) 2008  Dtella Labs (http://www.dtella.org)
Copyright (C) 2008  Paul Marks
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Ximin Luo <xl269@cam.ac.uk>

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
import shelve, random, time, socket, struct, heapq

from dtella.common.util import dcall_discard, get_user_path, CHECK
from dtella.common.ipv4 import Ad

class State():
    """
    Persistent state class. This class uses shelve to store data; see its
    documentation for details. In particular, note that mutating attributes
    *will not work*; you must read the attribute into a separate object, mutate
    that object, then re-assign that object to the attribute.

    To quote the documentation, "To append an item to d[key] in a way that will
    affect the persistent mapping, use:

        data = d[key]
        data.append(anitem)
        d[key] = data
    """
    def __init__(self, filename, defs={}, def_cb={}, **args):
        # __setattr__ takes precedence, can't use self.db = val
        self.__dict__["db"] = shelve.open(filename, **args)
        self.__dict__["defs"] = defs
        self.__dict__["def_cb"] = def_cb

    def __getattr__(self, name):
        if name in self.db:
            return self.db[name]
        elif name in self.defs:
            return self.defs[name]
        elif name in self.def_cb:
            # only call the function once, since it might generate different results
            value = self.def_cb[name]()
            self.__setattr__(name, value)
            return value
        else:
            return None

    def __setattr__(self, name, value):
        self.db[name] = value
        self.db.sync()

    def __delattr__(self, name):
        if name in self.db:
            del self.db[name]



class StateManager(State):

    def __init__(self, main, filename, **args):
        defaults = {
        'clientport': 7314,
        'killkey': '',
        'persistent': False,
        'localsearch': True,
        'ipcache': '',
        'suffix': '',
        'dns_ipcache': '\0\0\0\0',
        'dns_pkhashes': set(),
        }
        default_callbacks = {
        'udp_port': random_udp,
        }
        self.__dict__["main"] = main
        self.__dict__["peers"] = {}   # {ipp -> time}
        self.__dict__["exempt_ips"] = set()
        State.__init__(self, get_user_path(filename), defaults, default_callbacks, **args)


    def addExemptIP(self, ad):
        # If this is an offsite IP, add it to the exempt list.
        if not ad.auth('s', self.main):
            self.exempt_ips.add(ad.ip)


    def getYoungestPeers(self, n):
        # Return a list of (time, ipp) pairs for the N youngest peers
        peers = zip(self.peers.values(), self.peers.keys())
        return heapq.nlargest(n, peers)


    def refreshPeer(self, ad, age):
        # Call this to update the age of a cached peer

        if not ad.port:
            return

        if not ad.auth('sx', self.main):
            return

        ipp = ad.getRawIPPort()

        if age < 0:
            age = 0

        seen = time.time() - age

        try:
            old_seen = self.peers[ipp]
        except KeyError:
            self.peers[ipp] = seen
        else:
            if seen > old_seen:
                self.peers[ipp] = seen

        if self.main.icm:
            self.main.icm.newPeer(ipp, seen)

        # Truncate the peer cache if it grows too large
        target = 100

        if self.main.osm:
            target = max(target, len(self.main.osm.nodes))

        if len(self.peers) > target * 1.5:
            keep = set([ipp for when,ipp in self.getYoungestPeers(target)])

            for ipp in self.peers.keys():
                if ipp not in keep:
                    del self.peers[ipp]


    def setDNSIPCache(self, data):

        CHECK(len(data) % 6 == 4)

        when, = struct.unpack("!I", data[:4])
        ipps = [data[i:i+6] for i in range(4, len(data), 6)]

        self.dns_ipcache = when, ipps

        # If DNS contains a foreign IP, add it to the exemption
        # list, so that it can function as a bridge or cache node.

        self.exempt_ips.clear()

        for ipp in ipps:
            ad = Ad().setRawIPPort(ipp)
            self.addExemptIP(ad)

        return len(ipps)


def random_udp():
    for i in range(8):
        port = random.randint(1024, 65535)

        try:
            # See if the randomly-selected port is available
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(('', port))
            s.close()
            return port
        except socket.error:
            pass


##############################################################################
