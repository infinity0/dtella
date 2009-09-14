#!/bin/sh

# Dtella - Installer for POSIX (GNU, BSD) systems
# Copyright (C) 2009  Dtella Cambridge (http://camdc.pcriot.com/)
# Copyright (C) 2009  Ximin Luo <xl269@cam.ac.uk>
#
# $Id$
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#


WGET=""                                     # custom URL retrieval program

REPO=""                                     # repository URL
PROD=""                                     # product name (no .ext)
DEPS=""                                     # dependency archive (w/ .ext)

EXT=""                                      # archive extension
EXT_CMD=""                                  # archive extract command
EXT_VRB=""                                  # archive extract command (verbose)
EXT_LST=""                                  # archive list command

SVNR=""                                     # svn repository address


###########################################################################
# The rest of this file should not need to be changed for a given release.
###########################################################################

# Error codes:
# 1: user abort
# 2: error retrieving something from a remote location
# 3: error extracting an archive
# 4: error installing a component
# 5: couldn't create necessary installation files/directories
# 6: unavailable utility or feature

EXTRACT=$EXT_CMD
INSTALL=install_prod
VERBOSE=

for i in "$@"; do
	case "$i" in
	-h | --help )
		cat <<-EOF
		Usage: $0 <option>
		Install $REPO

		Options:
		  -v, --verbose             Show files as they are being extracted / installed.
		  -s, --svn                 Install the latest develpment version from SVN.

		EOF
		exit 0
		;;
	-s | --svn )
		if [ -z "$SVNR" ]; then echo "SVN install is not supported on this build."; exit 6; fi
		INSTALL=install_svn
		PROD="$PROD+SVN"
		;;
	-v | --verbose )
		VERBOSE=--verbose
		EXTRACT=$EXT_VRB
		;;
	esac
done

echo "This will install $PROD to your home directory."
echo "This script will overwrite ~/dtella and things in ~/.dtella/"
echo "Press enter to continue, or Ctrl-C at any time to abort..."

read ENTER

test -d ~/.dtella || mkdir ~/.dtella || { echo "Could not make ~/.dtella; abort" && exit 5; }
cd ~/.dtella

compile_warn() {
	echo
	echo "Note: If pre-compiled $1 binaries are not available for your system, the "
	echo "installer will automatically try to compile them. If the compiler complains "
	echo "about a missing Python.h, then first make sure you have the python-dev package "
	echo "installed, and try again. (You can uninstall this when the compile is done.)"
	echo "Press enter to continue, or Ctrl-C to abort..."
	read ENTER
}

NGOT=true
extract_dep() {
	if $NGOT; then
		if [ ! -e "$DEPS" ]; then get_latest "$REPO/$DEPS";
		elif [ ! -f "$DEPS" ]; then echo "~/.dtella/$DEPS exists and is not a file; abort"; exit 5;
		else get_latest "$REPO/$DEPS"; fi
		NGOT=false
	fi
	if ! $EXTRACT "$DEPS" "$1"; then echo "could not extract $2; abort"; exit 3; fi
}

install_dep() {
	cd "$1"
	compile_warn "$1"
	if ! python setup.py $VERBOSE install --install-lib=..;
	then echo "$2 could not be installed for this user; abort."; exit 4; fi
	python setup.py clean -a
	cd ..
	$EXT_LST "$DEPS" "$1" | sort -r | xargs rm -f 2>/dev/null
	$EXT_LST "$DEPS" "$1" | sort -r | xargs rmdir 2>/dev/null
	echo "$2 installed for this user";
}

install_prod() {
	get_latest "$REPO/$PROD.$EXT"
	if ! $EXTRACT "$PROD.$EXT"; then echo "could not extract $PROD.$EXT; abort"; exit 3; fi
	cd "$PROD"
	for i in *; do rm -rf "../$i"; done;
	mv -t .. *
	cd ..
	rmdir "$PROD"
}

install_svn() {
	# checkout from SVN and also force generation of build_config.py
	if ! { svn checkout "$SVNR" . && ./setup.py build && ./setup.py clean -a; }
	then echo "could not complete svn checkout; abort."; exit 2;
	fi
}

if [ -n "$WGET" ]; then
	get_latest() { if ! $WGET "$@"; then echo "could not download $@; abort"; exit 2; fi }
elif which wget > /dev/null; then
	get_latest() { if ! wget -N "$@"; then echo "could not download $@; abort"; exit 2; fi }
elif which curl > /dev/null; then
	get_latest() { if ! curl -O "$@"; then echo "could not download $@; abort"; exit 2; fi }
elif which fetch > /dev/null; then
	get_latest() { if ! fetch -m "$@"; then echo "could not download $@; abort"; exit 2; fi }
else
	echo "could not find a suitable URL-retrieval program. try setting the WGET variable "
	echo "near the top of this file."
	exit 6
fi

#python_has_mod() { false; }; # for testing
python_has_mod() { python -c "import $@" 2>/dev/null; }
LONGMSG="Yes, I know what I am doing."

if python_has_mod twisted;
then echo "Twisted found";
else
	echo "Twisted missing. Please install the python-twisted module. ONLY IF you are "
	echo "UNABLE to do this (eg. if you do not have root access), you may install it for "
	echo "this user only, by typing \"$LONGMSG\". Otherwise, "
	echo -n "hit ENTER to exit and install it normally: "
	read REPLY
	if [ ! "$REPLY" = "$LONGMSG" ]; then exit 1; fi
	extract_dep zope zope
	extract_dep twisted Twisted
	echo "Twisted installed for this user."
	echo
fi

if python_has_mod Crypto;
then echo "Crypto found";
else
	echo "pyCrypto missing. Please install the python-crypto module. ONLY IF you are"
	echo "UNABLE to do this (eg. if you do not have root access), you may install it for "
	echo "this user only, by typing \"$LONGMSG\". Otherwise, "
	echo -n "hit ENTER to exit and install it normally: "
	read REPLY
	if [ ! "$REPLY" = "$LONGMSG" ]; then exit 1; fi
	extract_dep pycrypto-2.0.1 pyCrypto
	install_dep pycrypto-2.0.1 pyCrypto
	echo "pyCrypto installed for this user."
	echo
fi


if python_has_mod tiger;
then
	echo "pytiger found"
	if [ -f "pytiger/pytiger.c" ]; then REPLY="U"; fi
else
	echo "pytiger missing"
	echo "pytiger is a custom package; downloading and extracting...";
	extract_dep pytiger pytiger
	while [ true ]; do
		echo -n "install pytiger [S]ystem-wide (requires root), or for this [U]ser only? [S|U]: "
		read REPLY
		if [ "$REPLY" = "S" ]; then
			cd pytiger
			compile_warn pytiger
			if ! python setup.py build;
			then echo "pytiger could not be installed; abort."; exit 4; fi
			echo "Please give the password for root:"
			if ! su root -c "python setup.py $VERBOSE install --prefix=/usr/local";
			then echo "pytiger could not be installed; abort."; exit 4; fi
			python setup.py clean -a
			echo "pytiger installed";
			cd ..
			break
		elif [ "$REPLY" = "U" ]; then
			install_dep pytiger pytiger
			break
		fi
	done
fi

echo
echo "all dependencies satisfied; installing $PROD"
echo

$INSTALL
rm -f "$DEPS"
echo
echo "$PROD installed successfully into ~/.dtella/"

cd
cat > dtella << 'EOF'
#!/bin/sh
python -O ~/.dtella/dtella.py "$@" &
EOF

if [ $? -gt 0 ]; then
	echo "However, could not install ~/dtella run script."
else
	chmod +x dtella
	echo "You can run it with ~/dtella"
fi
exit 0
