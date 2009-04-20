#!/bin/sh

# Dtella - Installer for posix (GNU, BSD) systems
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

SVNR=""                                     # svn repository address


###########################################################################
# The rest of this file should not need to be changed for a given release.
###########################################################################


EXTRACT=$EXT_CMD
INSTALL=install_prod

for i in "$@"; do
	case "$i" in
	-h | --help )
cat <<EOF
Usage: $0 <option>
Install $REPO

Options:
  -v, --verbose             Show files as they are being extracted.
  -s, --svn                 Install the latest develpment version from SVN.

EOF
		exit 0
		;;
	-s | --svn )
		if [ -z "$SVNR" ]; then echo "SVN install is not supported on this build."; exit 1; fi
		INSTALL=install_svn
		PROD="$PROD+SVN"
		;;
	-v | --verbose )
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

pytiger_compile_warn() {
	echo
	echo "Note: If pre-compiled pytiger binaries are not available for your system, the "
	echo "installer will automatically try to compile them. If the compiler complains "
	echo "about a missing Python.h, then first make sure you have the python-dev package "
	echo "installed, and try again. (You can uninstall this when the compile is done.)"
	echo "Press enter to continue, or Ctrl-C to abort..."
	read ENTER
}

NGOT=true
install_dep() {
	if $NGOT; then
		if [ ! -e "$DEPS" ]; then get_latest "$REPO/$DEPS";
		elif [ ! -f "$DEPS" ]; then echo "~/.dtella/$DEPS exists and is not a file; abort"; exit 5;
		else get_latest "$REPO/$DEPS"; fi
		NGOT=false
	fi
	$EXTRACT "$DEPS" "$1"
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
	if ! svn checkout "$SVNR" .
	then echo "could not complete svn checkout; abort."; exit 2;
	fi
}

if [ -n "$WGET" ]; then
	get_latest() { if ! $WGET "$@"; then echo "could not download $@; abort"; exit 2; fi }
elif which wget > /dev/null; then
	get_latest() { if ! wget -N "$@"; then echo "could not download $@; abort"; exit 2; fi }
elif which curl > /dev/null; then
	get_latest() { if ! curl -O "$@"; then echo "could not download $@; abort"; exit 2; fi }
else
	echo "could not find a suitable URL-retrieval program. try setting the WGET variable "
	echo "near the top of this file."
	exit 1
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
	if [ "$REPLY" = "$LONGMSG" ]; then
		if ! install_dep zope; then echo "could not extract zope; abort"; exit 3; fi
		if ! install_dep twisted; then echo "could not extract twisted; abort"; exit 3; fi
	else exit 1; fi
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
	if [ "$REPLY" = "$LONGMSG" ]; then
		if ! install_dep Crypto; then echo "could not extract pyCrypto; abort"; exit 3; fi
	else exit 1; fi
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
	if ! install_dep pytiger; then echo "could not extract pytiger"; exit 3; fi
	cd pytiger
	while [ true ]; do
		echo -n "install pytiger [S]ystem-wide (requires root), or for this [U]ser only? [S|U]: "
		read REPLY
		if [ "$REPLY" = "S" ]; then
			pytiger_compile_warn
			if su root -c "python setup.py --verbose install --prefix=/usr/local";
			then echo "pytiger installed";
			else echo "pytiger could not be installed; abort."; exit 4;
			fi
			break
		elif [ "$REPLY" = "U" ]; then
			pytiger_compile_warn
			if python setup.py --verbose install --install-lib=.;
			then echo "pytiger installed for this user";
			else echo "pytiger could not be installed for this user; abort."; exit 4;
			fi
			break
		fi
	done
	cd ..
fi

echo
echo "all dependencies satisfied; installing $PROD"
echo

$INSTALL
rm -f "$DEPS"
echo
echo "$PROD installed successfully into ~/.dtella/"

cd
if [ "$REPLY" = "U" ]; then
cat > dtella << 'EOF'
#!/bin/sh
export PYTHONPATH="$(echo ~/.dtella/pytiger)" # posix does not expand ~ on export
python -O ~/.dtella/dtella.py "$@" &
EOF
else
cat > dtella << 'EOF'
#!/bin/sh
python -O ~/.dtella/dtella.py "$@" &
EOF
fi

if [ $? -gt 0 ]; then
	echo "However, could not install ~/dtella run script."
else
	chmod +x dtella
	echo "You can run it with ~/dtella"
fi
exit 0
