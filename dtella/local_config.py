"""
Dtella - Local Site Configuration
Copyright (C) 2007-2008  Dtella Labs (http://www.dtella.org/)
Copyright (C) 2007-2008  Paul Marks (http://www.pmarks.net/)
Copyright (C) 2007-2008  Jacob Feisley (http://www.feisley.com/)
Copyright (C) 2008-2009  Dtella Cambridge (http://camdc.pcriot.com)

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

# These settings are specific to the Purdue network.  They should be
# customized for each new network you create.

# Use this prefix for filenames when building executables and installers.
# It will be concatenated with the version number below.
build_prefix = "dtella-cambridge-"

# Dtella version number.
version = "1.2.4.3"

# This is an arbitrary string which is used for encrypting packets.
# It essentially defines the uniqueness of a Dtella network, so every
# network should have its own unique key.
network_key = 'DC-Comics-Reloaded'

# This is the name of the "hub" which is seen by the user's DC client.
# "Dtella@____" is the de-facto standard, but nobody's stopping you
# from picking something else.
hub_name = "ADtella@Cambridge"

# Nodes can either emulate an ADC or NMDC hub. ADC is recommended.
# Clients will connect using adc:// or nmdc:// (default in most clients)
adc_mode = True

# Set this if you want Dtella to reject plaintext connection attempts.
# This only works when adc_mode is True. Recommended for fascist networks.
# TODO: not yet implemented
adc_fcrypto = True

# This enforces a maximum cap for the 'minshare' value which appears in DNS.
# It should be set to some sane value to prevent the person managing DNS from
# setting the minshare to 99999TiB, and effectively disabling the network.
minshare_cap = 1 * (1024**2)   # (=100MiB)

# This is a list of subnets (in CIDR notation) which will be permitted on
# the network.  Make sure you get this right initially, because you can't
# make changes once the program has been distributed.  In the unlikely event
# that you don't want any filtering, use ['0.0.0.0/0']
allowed_subnets = ['128.232.0.0/16', '129.169.0.0/16', '131.111.0.0/16', '193.60.80.0/20',
'172.16.0.0/13', '172.24.0.0/14', '172.28.0.0/15', '172.30.0.0/16']

# Here we configure an object which pulls 'Dynamic Config' from some source
# at a known fixed location on the Internet.  This config contains a small
# encrypted IP cache, version information, minimum share, and a hash of the
# IRC bridge's public key.

# -- Use DNS TXT Record --
import dtella.modules.pull_dns
dconfig_puller = dtella.modules.pull_dns.DnsTxtPuller(
    # Some public DNS servers to query through. (GTE and OpenDNS)
    servers = ['4.2.2.1','4.2.2.2','208.67.220.220','208.67.222.222'],
    # Hostname where the DNS TXT record resides.
    hostname = "cambridge.config.dtella.org"
    )

# -- Use Google Spreadsheet --
##import dtella.modules.pull_gdata
##dconfig_puller = dtella.modules.pull_gdata.GDataPuller(
##    sheet_key = "..."
##    )

#''' BEGIN NEWITEMS MOD #
# Limits for !newitems storage. Individual users can override the limits for
# display by using the commands !newitems daylim [days] | numlim [count]
# but data for items will always be stored up to the smallest of these limits.
newitems_daylim = 14
newitems_numlim = 64
# newitems_numlim should be <= 32, since UDP packets have a limited size
# END NEWITEMS MOD '''#

# Enable this if you can devise a meaningful mapping from a user's hostname
# to their location.  Locations are displayed in the "Connection / Speed"
# column of the DC client.
use_locations = True

###############################################################################

# if use_locations is True, then rdns_servers and hostnameToLocation will be
# used to perform the location translation.  If you set use_locations = False,
# then you may delete the rest of the lines in this file.

# DNS servers which will be used for doing IP->Hostname reverse lookups.
# These should be set to your school's local DNS servers, for efficiency.
rdns_servers = ['131.111.8.42','131.111.12.20']

# Customized data for our implementation of hostnameToLocation
import re
suffix_re = re.compile(r"(?:.*?\.)?([^.]+)(?:\.societies|\.private)?\.cam\.ac\.uk")
#prefix_re = re.compile(r"^([a-z]{1,6}).*\.cam\.ac\.uk")

#pre_table = {
#    }

suf_table = {
    'chu':'Churchill', 'christs':'Christ\'s', 'clare':'Clare', 'corpus':'Corpus Christi',
    'dar':'Darwin', 'dow':'Downing', 'emma':'Emmanuel', 'fitz':'Fitzwilliam',
    'girton':'Girton', 'cai':'Gonville and Caius', 'homerton':'Homerton', 'jesus':'Jesus',
    'kings':'King\'s', 'lucy-cav':'Lucy Cavendish', 'magd':'Magdalene', 'newn':'Newnham',
    'pem':'Pembroke', 'quns':'Queens\'', 'robinson':'Robinson', 'sel':'Selwyn',
    'sid':'Sidney Sussex', 'caths':'St Catharine\'s', 'st-edmunds':'St Edmund\'s', 'joh':'St John\'s',
    'trin':'Trinity', 'wolfson':'Wolfson', 'clarehall':'Clare Hall', 'hughes':'Hughes Hall',
    'newhall':'New Hall', 'trinhall':'Trinity Hall', 'srcf':'SRCF',
    }

def hostnameToLocation(hostname):
    # Convert a hostname into a human-readable location name.

    if hostname:

        suffix = suffix_re.match(hostname)
        if suffix:
            try:
                return suf_table[suffix.group(1)]
            except KeyError:
                pass

#        prefix = prefix_re.match(hostname)
#        if prefix:
#            try:
#                return pre_table[prefix.group(1)]
#            except KeyError:
#                pass

    return "Unknown Location"
