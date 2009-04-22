#!/usr/bin/env python
"""
Dtella - py2exe setup script
Copyright (C) 2007-2008  Dtella Labs (http://dtella.org/)
Copyright (C) 2007-2008  Paul Marks (http://pmarks.net/)
Copyright (C) 2007-2008  Jacob Feisley (http://feisley.com/)
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

from distutils.core import setup
import sys, os
import dtella.local_config as local

class Error(Exception):
    pass

def get_excludes():
    ex = []

    # Ignore XML and SSL, unless the puller needs them.
    def check_attr(o, a):
        try:
            return getattr(o, a)
        except AttributeError:
            return False

    if not check_attr(local.dconfig_puller, 'needs_xml'):
        ex.append("xml")

    if not check_attr(local.dconfig_puller, 'needs_ssl'):
        ex.append("_ssl")

    # No client should need this
    ex.append("OpenSSL")

    # Skip over any bridge components.
    ex.append("dtella.bridge_config")
    ex.append("dtella.bridge")

    return ex


def patch_build_type(type="tar.bz2"):
    # Patch the local_config with the correct build_type
    lines = []
    for line in file("dtella/local_config.py").readlines():
        if line.find('build_type = "') == 0:
            line = 'build_type = "%s"\n' % type
        lines.append(line)

    file("dtella/local_config.py", "w").writelines(lines)


def patch_nsi_template():
    # Generate NSI file from template, replacing name and version
    # with data from local_config.

    dt_name = local.hub_name
    dt_version = local.version
    dt_simplename = local.build_prefix + local.version

    wfile = file("installer_win/dtella_updater.nsi", "w")

    for line in file("installer_win/dtella_updater.template.nsi"):
        if "PATCH_ME" in line:
            if "PRODUCT_NAME" in line:
                line = line.replace("PATCH_ME", dt_name)
            elif "PRODUCT_VERSION" in line:
                line = line.replace("PATCH_ME", dt_version)
            elif "PRODUCT_SIMPLENAME" in line:
                line = line.replace("PATCH_ME", dt_simplename)
            else:
                raise Error("Unpatchable NSI line: %s" % line)
        wfile.write(line)
    wfile.close()


def build_posix_installer():
    # Patch the dtella_install with the correct variables
    vars = { }
    
    try:
        import dtella.bridge.bridge_config as bcfg
        vars['REPO'] = bcfg.dconfig_fixed_entries['version'].split(' ')[2]
        i = vars['REPO'].find('#')
        if i >= 0:
            vars['REPO'] = vars['REPO'][:i] + vars['REPO'][i+1:]
    except ImportError:
        sys.stderr.write("Could not find bridge config; abort.\n")
        return 1
    except ValueError:
        sys.stderr.write("Could not extract repository URL from bridge config; abort.\n")
        return 1

    import dtella.local_config as local
    try:
        vars['PROD'] = local.build_prefix + local.version
    except AttributeError:
        sys.stderr.write("Could not extract product name from local config; abort.\n")
        return 1

    argv = sys.argv[1:]
    for i in argv:
        try:
            k, v = i.split('=', 1)
            vars[k] = v
        except ValueError:
            sys.stderr.write("Ignoring malformed k=v pair: %s\n" % i)
            pass

    if 'DEPS' not in vars:
        sys.stderr.write("DEPS not specified. (You can specify key=value pairs as arguments to this command.)\n")
        return 1

    lines = file("installer_posix/dtella.template.sh").readlines()
    for k, v in vars.iteritems():
        for i, line in enumerate(lines):

            if line[:len(k)+3] != k + '=""':
                continue

            kl, vl = len(k), len(v)
            e = line.find('#')
            
            if e < 0:
                lines[i] = '%s="%s"' % (k, v)
            elif kl+3+vl < e:
                lines[i] = '%s="%s"' % (k, v) + line[kl+3+vl:]
            else:
                lines[i] = '%s="%s"\n%s%s' % (k, v, ' '*e, line[e:])

    outdir = "dist"
    if 'OUTDIR' in os.environ:
        outdir = os.environ["OUTDIR"]

    f = "%s/%s.sh" % (outdir, vars['PROD'])
    wfile = file(f, "w")
    for line in lines:
        wfile.write(line)
    wfile.close()
    os.chmod(f, 0755)
    print "installer wrote to %s" %f


if sys.platform == 'darwin':
    patch_build_type('dmg')
    import py2app
elif sys.platform == 'win32':
    patch_build_type('exe')
    import py2exe
    patch_nsi_template()
elif os.name == 'posix':
    patch_build_type()
    sys.exit(build_posix_installer())
else:
    sys.stderr.write("Unsupported build platform: %s\n" % sys.platform)
    sys.exit(-1)

excludes = get_excludes()

setup(
    name = 'Dtella',
    version = local.version,
    description = 'Dtella Client',
    author = 'Dtella Labs',
    url = 'http://dtella.org',
    options = {
        "py2exe": {
            "optimize": 2,
            "bundle_files": 1,
            "ascii": True,
            "dll_excludes": ["libeay32.dll"],
            "excludes": excludes,
        },

        "py2app": {
            "optimize": 2,
            "argv_emulation": True,
            "iconfile": "icons/dtella.icns",
            "plist": {'LSBackgroundOnly':True},
            "excludes": excludes,
        }
    },

    app = ["dtella.py"],

    zipfile = None,
    windows = [{
        "script": "dtella.py",
        "icon_resources": [(1, "icons/dtella.ico"), (10, "icons/kill.ico")],
    }]
)

patch_build_type()
