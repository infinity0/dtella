"""
Dtella - Local Site Configuration
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
import ConfigParser, re, ast, os.path, shutil, sys
from dtella.common.util import (parse_bytes, hostnameMatch, get_user_path)

config = ConfigParser.RawConfigParser()
cfgfile = get_user_path("network.cfg")
if not os.path.exists(cfgfile):
    # copy default network config if user doesn't have an override
    shutil.copy2(os.path.join(os.path.dirname(__file__), "network.cfg"), cfgfile)
config.read(cfgfile)

# Set the fields

local = sys.modules[__name__]
for i in config.sections():
    for k, v in config.items(i):
        try:
            value = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            value = v
        #print "%s = %s %s" % (k, value.__class__, value)
        setattr(local, k, value)

# Verify required fields are all there

try:
    network_key; hub_name; allowed_subnets; dconfig_type; use_locations;
except NameError, e:
    print "Broken network config file (%s); exiting" % e
    print "If you recently upgraded Dtella, you may also need to upgrade your network config file."
    print "Default network: %s" % os.path.join(os.path.dirname(__file__), "network.cfg")
    print "Currently using: %s" % cfgfile
    sys.exit(3)

# Postprocess some fields to the correct types, etc, whatever

try:
    adc_mode
except NameError:
    adc_mode = False

try:
    minshare_cap = parse_bytes(minshare_cap)
except NameError:
    minshare_cap = 1024 ** 4 # 1GiB

try:
    if dconfig_type == "dns":
        import dtella.modules.pull_dns
        dconfig_puller = dtella.modules.pull_dns.DnsTxtPuller(**dconfig_options)
    elif dconfig_type == "gdata":
        import dtella.modules.pull_gdata
        dconfig_puller = dtella.modules.pull_gdata.GDataPuller(**dconfig_options)
except NameError, e:
    print "No options supplied to the dconfig puller (%s); exiting" % e
    sys.exit(3)
except TypeError, e:
    print "Bad options supplied to the dconfig puller (%s); exiting" % e
    sys.exit(3)

if use_locations:
    if rdns_servers:
        def hostnameToLocation(hostname):
            # Convert a hostname into a human-readable location name.
            return hostnameMatch(hostname, host_regex)
    else:
        def hostnameToLocation(hostname):
            return "TODO implement IP locator"
