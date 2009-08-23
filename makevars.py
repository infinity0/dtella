#!/usr/bin/env python
import sys
import setup

name = setup.properties['name']
version = setup.properties['version']

if sys.platform.startswith("win"):
    export = "set"
else:
    export = "export"

print '%s FILEBASE="%s"' % (export, name +'-'+ version)
