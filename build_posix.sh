#!/bin/dash

python setup.py sdist --formats=bztar

python setup.py bdist_shinst "--EXT=tar.bz2" "--EXT-CMD=tar xjf" "--EXT-VRB=tar xvjf" \
	"--SVNR=http://dtella-cambridge.googlecode.com/svn/trunk" \
	"--DEPS=dtella_deps.tar.bz2"
