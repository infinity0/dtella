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

import sys, os

properties = {
    'name': 'dtella-cambridge',
    'version': '1.2.4.5',
    'description': 'Client for the Dtella network at Cambridge',
    'author': 'Dtella-Cambridge',
    'author_email': 'cabal@camdc.pcriot.com',
    'url': 'http://camdc.pcriot.com',
    'license': 'GPL v3',
    'platforms': ['posix', 'win32', 'darwin'],
    'options': {},
}
## FIXME have this empty by default and set only if --format= is set
build_type = "tar.bz2"
bugs_email = "cabal@camdc.pcriot.com"


class Error(Exception):
    pass


def get_excludes():
    ex = []

    # No client should need this
    ex.append("OpenSSL")

    # Skip over any bridge components.
    ex.append("dtella.bridge_config")
    ex.append("dtella.bridge")

    return ex


def get_includes():
    inc = []

    # this is required for py2exe/py2app to work with shelve
    for db in ['dbhash', 'gdbm', 'dbm', 'dumbdbm']:
        try:
            __import__(db)
            inc.append(db)
        except ImportError:
            pass

    if not inc:
        raise Error("Could not find a suitable dbm. Check your python installation.")

    return inc


# TODO find a better way of doing this...
def make_build_config(type, bugs_email, data_dir=None):
    # Patch the build_config with the correct variables
    global properties
    props = properties.copy()
    props.update({
        'type': type,
        'bugs_email': bugs_email,
        'data_dir': data_dir,
    })

    lines = []
    for line in file("dtella/build_config.py.in").readlines():
        i = line.find(' = ')
        if i >= 0:
            key = line[:i]
            if key in props:
                line = line.replace('PATCH_ME', str(props[key]))
        lines.append(line)

    file("dtella/build_config.py", "w").writelines(lines)
    print "wrote build config to dtella/build_config.py"


def patch_nsi_template(suffix=''):
    # Generate NSI file from template

    dt_name = properties['name']
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

    dt_name = properties['name']
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


if __name__ == '__main__':

    from distutils.core import setup
    from distutils.command.bdist import bdist

    my_commands = {}

    if 'py2app' in sys.argv:
        build_type = 'dmg'
        import py2app

        properties['app'] = ["dtella.py"]
        properties['options']['py2app'] = {
            "optimize": 2,
            "argv_emulation": True,
            "iconfile": "icons/dtella.icns",
            "plist": {'LSBackgroundOnly':True},
            "excludes": get_excludes(),
            "includes": get_includes(),
        }

    elif 'py2exe' in sys.argv:
        build_type = 'exe'
        import py2exe

        if len(sys.argv) <= 2:
            patch_nsi_template()
        elif sys.argv[2] == 'camdc':
            patch_camdc_nsi_template()
            del sys.argv[2]
        elif sys.argv[2] == 'updater':
            patch_nsi_template('updater')
            del sys.argv[2]
        else:
            patch_nsi_template()

        properties['zipfile'] = None
        properties['windows'] = [{
            "script": "dtella.py",
            "icon_resources": [(1, "icons/dtella.ico"), (10, "icons/kill.ico")],
        }]
        properties['options']['py2exe'] = {
            "optimize": 2,
            "bundle_files": 1,
            "ascii": True,
            "dll_excludes": ["libeay32.dll"],
            "excludes": get_excludes(),
            "includes": get_includes(),
        }

        # py2exe is shit and ignores package_data so we need to hack this up ourselves
        from py2exe.build_exe import py2exe as build_exe
        class py2exe_pkg(build_exe):

            def copy_extensions(self, extensions):
                build_exe.copy_extensions(self, extensions)

                for pkg, data in self.distribution.package_data.iteritems():
                    for file in data:
                        path = os.path.join(pkg, file)
                        full = os.path.join(self.collect_dir, path)

                        if os.path.isdir(path):
                            raise Error("Not implemented yet")
                        else:
                            self.copy_file(path, full)
                            self.compiled_files.append(path)

        my_commands['py2exe'] = py2exe_pkg

    else:
        del properties['options']


    # "from distutils.core import Distribution" will get the unpatched version
    # of it; py2app and py2exe both patch it and we need to extend that
    import distutils.core
    _Distribution = distutils.core.Distribution
    class MyDist(_Distribution):

        def __init__(self, attrs=None):
            _Distribution.__init__(self, attrs)
            self.global_options.append(('bridge', 'b', "include the bridge modules in the build"))

        def run_commands(self):
            global build_type, bugs_email
            make_build_config(build_type, bugs_email)
            try:
                getattr(self, "bridge")
                self.packages.append('dtella.bridge')
            except AttributeError:
                pass
            _Distribution.run_commands(self)


    class bdist_shinst(bdist):

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
            ('EXT-LST=', None,
             "archive list command"),
            ('SVNR=', None,
             "svn repository address"),
            ]

        def initialize_options(self):
            bdist.initialize_options(self)
            self.WGET = ''
            self.REPO = ''
            self.PROD = ''
            self.DEPS = ''
            self.EXT = ''
            self.EXT_CMD = ''
            self.EXT_VRB = ''
            self.EXT_LST = ''
            self.SVNR = ''

        def finalize_options(self):
            bdist.finalize_options(self)

        def run(self):
            try:
                import dtella.bridge_config as bcfg
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

            self.PROD = properties['name'] + '-' + properties['version']

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

            f = "%s/%s.sh" % (self.dist_dir, self.PROD)
            wfile = file(f, "w")
            for line in lines:
                wfile.write(line)
            wfile.close()
            os.chmod(f, 0755)
            print "installer wrote to %s" %f

    my_commands['bdist_shinst'] = bdist_shinst

    setup(
        distclass = MyDist,
        cmdclass = my_commands,
        packages = ['dtella', 'dtella.client', 'dtella.common', 'dtella.modules'],
        # FIXME put bridge_config into dtella.bridge so we can exclude it
        package_data = {'dtella': ['network.cfg', 'bridge.cfg']},
        scripts = ['bin/dtella'],
        **properties
    )
