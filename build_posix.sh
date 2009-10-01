#!/bin/sh

# builds a source distribution of dtella plus a shell script that installs
# dtella dependencies and dtella from a remote source distribution

python setup.py sdist --formats=bztar

python setup.py bdist_shinst "--SVNR=http://dtella-cambridge.googlecode.com/svn/trunk" \
	"--EXT=tar.bz2" "--EXT-CMD=tar xjf" "--EXT-VRB=tar xvjf" "--EXT-LST=tar tjf" \
	"--DEPS=dtella_deps.tar.bz2"
