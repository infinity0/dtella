#!/usr/bin/env python
"""
Dtella - py2exe setup script
Copyright (C) 2007-2008  Dtella Labs (http://dtella.org/)
Copyright (C) 2007-2008  Paul Marks (http://pmarks.net/)
Copyright (C) 2007-2008  Jacob Feisley (http://feisley.com/)
Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
Copyright (C) 2009  Ximin Luo <xl269@cam.ac.uk>
Copyright (C) 2009- Andyhhp <andyhhp@hotmail.com>

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

from distutils.core import setup, Command
from distutils.dist import Distribution
import sys, os
import dtella.local_config as local

properties = {
    'name': 'dtella-cambridge',
    'version': '1.2.4.4',
    'description': 'Client for the Dtella network at Cambridge',
    'author': 'Dtella-Cambridge',
    'author_email': 'cabal@camdc.pcriot.com',
    'url': 'http://camdc.pcriot.com',
    'license': 'GPL v3',
    'platforms': ['posix', 'win32', 'darwin'],
}
## FIXME have this empty by default and set only if --format= is set
build_type = "tar.bz2"

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


# TODO find a better way of doing this...
def make_build_config(type):
    # Patch the local_config with the correct build_type
    lines = []
    properties['type'] = type
    for line in file("dtella/build_config.py.in").readlines():
        if line.find('BUILD_') >= 0:
            for k, v in properties.items():
                key = 'BUILD_' + k.upper()
                line = line.replace(key, str(v))
        lines.append(line)
    del properties['type']

    file("dtella/build_config.py", "w").writelines(lines)
    print "wrote build config to dtella/build_config.py"


def patch_nsi_template(suffix=''):
    # Generate NSI file from template, replacing name and version
    # with data from local_config.

    dt_name = local.hub_name
    dt_version = properties['version']
    dt_simplename = properties['name'] + '-' + properties['version']

    if suffix:
        suffix = '_' + suffix

    wfile = file("installer_win/dtella%s.nsi" % suffix, "w")

    for line in file("installer_win/dtella%s.template.nsi" % suffix):
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


def patch_camdc_nsi_template():
    # Generate NSI file from template, replacing name and version
    # with data from local_config.

    dt_name = local.hub_name
    dt_version = properties['version']
    dt_simplename = properties['name'] + '-' + properties['version']

    wfile = file("installer_win/camdc.nsh", "w")

    for line in file("installer_win/camdc.template.nsh"):
        if "PATCH_ME" in line:
            if "DTELLA_NAME" in line:
                line = line.replace("PATCH_ME", dt_name)
            elif "DTELLA_VERSION" in line:
                line = line.replace("PATCH_ME", dt_version)
            elif "DTELLA_SOURCENAME" in line:
                line = line.replace("PATCH_ME", dt_simplename)
            else:
                raise Error("Unpatchable NSI line: %s" % line)
        wfile.write(line)
    wfile.close()


class MyDist(Distribution):

    def __init__(self, attrs=None):
        Distribution.__init__(self, attrs)
        self.global_options.append(('bridge', 'b', "include the bridge modules in the build"))

    def run_commands(self):
        global build_type
        make_build_config(build_type)
        try:
            getattr(self, "bridge")
            self.packages.append('dtella.bridge')
        except AttributeError:
            pass
        Distribution.run_commands(self)


class bdist_shinst(Command):

    description = "Create a shell-installer for posix systems"

    user_options = [
        ('WGET=', None,
         "default custom URL retrieval program"),
        ('REPO=', None,
         "repository URL"),
        ('PROD=', None,
         "product name (no .ext)"),
        ('DEPS=', None,
         "dependency archive (w/ .ext)"),
        ('EXT=', None,
         "archive extension"),
        ('EXT-CMD=', None,
         "archive extract command"),
        ('EXT-VRB=', None,
         "archive extract command (verbose)"),
        ('SVNR=', None,
         "svn repository address"),
        ]

    def initialize_options(self):
        self.WGET = ''
        self.REPO = ''
        self.PROD = ''
        self.DEPS = ''
        self.EXT = ''
        self.EXT_CMD = ''
        self.EXT_VRB = ''
        self.SVNR = ''

    def finalize_options(self):
        pass

    def run(self):
        try:
            import dtella.bridge.bridge_config as bcfg
            self.REPO = bcfg.dconfig_fixed_entries['version'].split(' ')[2]
            i = self.REPO.find('#')
            if i >= 0:
                self.REPO = self.REPO[:i] + self.REPO[i+1:]
        except ImportError:
            sys.stderr.write("Could not find bridge config; abort.\n")
            return 1
        except ValueError:
            sys.stderr.write("Could not extract repository URL from bridge config; abort.\n")
            return 1

        import dtella.local_config as local
        try:
            self.PROD = properties['name'] + '-' + properties['version']
        except AttributeError:
            sys.stderr.write("Could not extract product name from local config; abort.\n")
            return 1

        if not self.DEPS:
            sys.stderr.write("DEPS not specified. (You can specify key=value pairs as arguments to this command.)\n")
            return 1

        from distutils.fancy_getopt import longopt_xlate
        import string
        lines = file("installer_posix/dtella.template.sh").readlines()
        for (k, _, _) in self.user_options:
            k = string.translate(k, longopt_xlate)
            if k[-1] == "=":
                k = k[:-1]
            v = getattr(self, k)

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

        f = "%s/%s.sh" % (outdir, self.PROD)
        wfile = file(f, "w")
        for line in lines:
            wfile.write(line)
        wfile.close()
        os.chmod(f, 0755)
        print "installer wrote to %s" %f


if __name__ == '__main__':

    if sys.platform == 'darwin':
        build_type = 'dmg'
        import py2app
        properties['app'] = ["dtella.py"]

    elif sys.platform == 'win32':
        build_type = 'exe'

        import py2exe
        if len(sys.argv) <= 2:
            patch_nsi_template()
        elif sys.argv[2] == 'updater':
            patch_nsi_template('updater')
            del sys.argv[2]
        elif sys.argv[2] == 'camdc':
            patch_camdc_nsi_template()
            del sys.argv[2]
        else:
            patch_nsi_template()

        properties['zipfile'] = None,
        properties['windows'] = [{
            "script": "dtella.py",
            "icon_resources": [(1, "icons/dtella.ico"), (10, "icons/kill.ico")],
        }]

    excludes = get_excludes()

    setup(
        distclass = MyDist,
        cmdclass = {'bdist_shinst': bdist_shinst},
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

        packages = ['dtella', 'dtella.client', 'dtella.common', 'dtella.modules'],
        scripts = ['bin/dtella'],

        **properties
    )
