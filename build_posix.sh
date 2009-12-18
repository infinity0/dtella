#!/bin/sh

eval $(python makevars.py)

BLDDIR="build"
OUTDIR="dist"

case $1 in
deb )
	if [ ! -f "dist/$FILEBASE.tar.gz" ]; then
		echo "Need to build source distribution first."
		exit 1
	fi

	# builds a debian package of dtella in deb_dist/
	# you need stdeb 0.4.1 or greater

	rm -rf "$BLDDIR/stdeb" && mkdir -p "$BLDDIR/stdeb"

	# if the version string has a non-alphanum character in it, the build will fail.
	# see http://github.com/astraw/stdeb/issues/#issue/15 for a workaround

	py2dsc --workaround-548392=false -d "$BLDDIR/stdeb" -x "setup.cfg" "dist/$FILEBASE.tar.gz"
	# bug #548392 does not affect us and the workaround restricts the python version, so don't use it

	cd "$BLDDIR/stdeb/$FILEBASE"
	dpkg-buildpackage -rfakeroot
	cd -
	for i in "$BLDDIR/stdeb"/*; do
		if [ -f "$i" ]; then cp -a "$i" "$OUTDIR"; fi
	done

	;;
* )
	# builds a source distribution of dtella
	python setup.py sdist
	python setup.py sdist --formats=bztar

	# builds a shell script that installs dtella and its dependencies
	# from a remote source distribution
	python setup.py bdist_shinst "--SVNR=http://dtella-cambridge.googlecode.com/svn/trunk" \
		"--EXT=tar.bz2" "--EXT-CMD=tar xjf" "--EXT-VRB=tar xvjf" "--EXT-LST=tar tjf" \
		"--DEPS=dtella_deps.tar.bz2"
	;;
esac
