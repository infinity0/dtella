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
import re, os.path, sys
from dtella.common.util import (parse_bytes, hostnameMatch, get_user_path,
                                load_cfg)

prefix = "network"

# Set defaults
adc_mode = False
adc_fcrypto = False
minshare_cap = str(1024 ** 3) # 1GiB

# Set fields from the config
cfgname = load_cfg(__name__, prefix)

# Verify required fields are all there

try:
    network_key; hub_name; allowed_subnets; dconfig_type; use_locations;
except NameError, e:
    print "Network config: missing value (%s); exiting" % e
    print "If you recently upgraded Dtella, you may also need to upgrade your network config file."
    print "Default network: %s" % os.path.join(os.path.dirname(__file__), prefix + ".cfg")
    print "Currently using: %s" % get_user_path(cfgfile)
    sys.exit(3)

# Postprocess some fields to the correct types, etc, whatever

try:
    minshare_cap = parse_bytes(minshare_cap)
except ValueError, e:
    print "Network config: bad value for minshare_cap (%s); exiting" % e
    sys.exit(3)

try:
    if dconfig_type == "dns":
        import dtella.modules.pull_dns
        dconfig_puller = dtella.modules.pull_dns.DnsTxtPuller(**dconfig_options)
    elif dconfig_type == "gdata":
        import dtella.modules.pull_gdata
        dconfig_puller = dtella.modules.pull_gdata.GDataPuller(**dconfig_options)
except NameError, e:
    print "Network config: no options supplied to the dconfig puller (%s); exiting" % e
    sys.exit(3)
except TypeError, e:
    print "Network config: bad options supplied to the dconfig puller (%s); exiting" % e
    sys.exit(3)

from dtella.common.ipv4 import SubnetMatcher, CidrStringToIPMask, rfc1918_matcher

# Create a subnet matcher for locally-configured IPs.
ip_matcher = SubnetMatcher(allowed_subnets)

# If any explicitly-allowed subnets are subsets of RFC1918 space,
# then IPs in those subnets should NOT be classified as private.
not_private_matcher = SubnetMatcher()
for r in allowed_subnets:
    ipmask = CidrStringToIPMask(r)
    if rfc1918_matcher.containsRange(ipmask):
        not_private_matcher.addRange(ipmask)

if use_locations:
    if rdns_servers:
        def hostnameToLocation(hostname):
            # Convert a hostname into a human-readable location name.
            return hostnameMatch(hostname, host_regex)
    else:
        def hostnameToLocation(hostname):
            return "TODO implement IP locator"
