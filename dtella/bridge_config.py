"""
Dtella - Bridge Configuration
Copyright (C) 2007-2008  Dtella Labs (http://www.dtella.org/)
Copyright (C) 2007-2008  Paul Marks (http://www.pmarks.net/)
Copyright (C) 2007-2008  Jacob Feisley (http://www.feisley.com/)
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

import sys, os.path
from dtella.common.util import (load_cfg, get_user_path)

prefix = "bridge"

# Set defaults

myip_hint = ''
ip_cache = []

rdns_servers = []
irc_to_dc_bot = "*IRC"
dc_to_irc_bot = "DtellaBridge"
virtual_nicks = []
dc_to_irc_prefix = '|'
irc_to_dc_prefix = '~'
max_irc_nick_len = 30

dconfig_push_interval = 60*60

# Set fields from the config
cfgname = load_cfg(__name__, prefix)

# Verify required fields are all there

try:
    udp_port; private_key; service_ircd; service_args;
    dconfig_fixed_entries; dconfig_push_type; dconfig_push_options;
except NameError, e:
    raise ImportError("\n".join([
        "Bridge config: missing value (%s)" % e,
        "If you recently upgraded Dtella, you may also need to upgrade your bridge config file.",
        "Example bridge: %s" % os.path.join(os.path.dirname(__file__), prefix + ".cfg"),
        "Currently using: %s" % get_user_path(cfgname + ".cfg"),
    ]))

# Postprocess some fields to the correct types, etc, whatever

# Service config. Supported servers are "InspIRCd" and "UnrealIRCd"
service_classes = {
    "insp": "dtella.bridge.inspircd.InspIRCdConfig",
    "unreal": "dtella.bridge.inspircd.UnrealConfig",
}
try:
    service_ircd = service_ircd.lower()
    if service_ircd.endsWith("ircd"):
        service_ircd = service_ircd[:-4]
    service_class = service_classes[service_ircd]
except AttributeError, KeyError:
    raise ImportError("Bridge config: unsupported IRCd (%s) - need InspIRCd or UnrealIRCd" % service_ircd)

# dconfig pusher
import dtella.modules.push_textfile
import dtella.modules.push_gdata
import dtella.modules.push_dnsupdate
import dtella.modules.push_yi
dconfig_pushers = {
    'textfile': dtella.modules.push_textfile.TextFileUpdater,
    'gdata': dtella.modules.push_gdata.GDataUpdater,
    'dns': dtella.modules.push_dnsupdate.DynamicDNSUpdater,
    'yi': dtella.modules.push_yi.YiUpdater,
}
try:
    dconfig_push_func = dconfig_pushers[dconfig_push_type](dconfig_push_options).update
except NameError, e:
    raise ImportError("Bridge config: no options supplied to the dconfig pusher (%s)" % e)
except TypeError, e:
    raise ImportError("Bridge config: bad options supplied to the dconfig pusher (%s)" % e)
