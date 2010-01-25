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
ACTION="install"

DIR_BASE="$HOME/.local/share/dtella"
DIR_CFG="$HOME/.dtella"
DIR_BIN="$HOME/bin"

PDIR_BASE="~/.local/share/dtella"
PDIR_CFG="~/.dtella"
PDIR_BIN="~/bin"

for i in "$@"; do
	case "$i" in
	-s | --svn )
		if [ -z "$SVNR" ]; then echo "SVN install is not supported on this build."; exit 6; fi
		INSTALL=install_svn
		PROD="$PROD+SVN"
		;;
	-v | --verbose )
		VERBOSE=--verbose
		EXTRACT=$EXT_VRB
		;;
	-u | --uninstall )
		ACTION="uninstall"
		;;
	-o | --uninstall-old )
		ACTION="uninstall-old"
		;;
	-h | --help | * )
		cat <<-EOF
		Usage: $0 [OPTIONS]
		Install or uninstall $PROD

		Options:
		  -v, --verbose             Show files as they are being extracted / installed.
		  -s, --svn                 Install the latest develpment version from SVN.
		  -u, --uninstall           Uninstall dtella
		  -o, --uninstall-old       Uninstall dtella (old structure, in $PDIR_CFG)

		Files:
		  Base program files        $PDIR_BASE/
		  Run script                $PDIR_BIN/dtella
		  User (data) files         $PDIR_CFG/

		EOF
		exit 0
		;;
	esac
done

echo ">>> $PROD: \033[1m$ACTION\033[0m (see --help for options)"

uninstall_end() {
	if $1; then echo "$PROD \033[1msuccessfully uninstalled\033[0m."; X=0;
	else echo "$PROD \033[1mpartially uninstalled\033[0m; see output for details."; X=5; fi
	echo "There may still be user files in $PDIR_CFG; you may remove these yourself."
	exit $X
}

case $ACTION in
uninstall )
	echo "This will remove $PDIR_BIN/dtella, and $PDIR_BASE and its contents. "
	echo "Press enter to continue, or Ctrl-C to abort..."
	read ENTER
	rm -rf $VERBOSE "$DIR_BIN/dtella" "$DIR_BASE" || SUC=false
	rmdir -p $VERBOSE "$DIR_BIN" $(dirname "$DIR_BASE")
	uninstall_end $SUC
	;;
uninstall-old )
	echo "This will remove ~/dtella, and the contents of $PDIR_CFG. User files will be "
	echo "spared (*.db, *.log, *.cfg files in the top-level directory)."
	echo "Press enter to continue, or Ctrl-C to abort..."
	read ENTER
	EXC='^[^/]*\.\(db\|log\|cfg\)$'
	cd "$DIR_CFG"
	find * ! -type d | grep -v $EXC | sort -r | xargs rm -f $VERBOSE || SUC=false
	rm -f $VERBOSE setup.cfg ~/dtella || SUC=false
	find *           | grep -v $EXC | sort -r | xargs rmdir $VERBOSE || SUC=false
	uninstall_end $SUC
	;;
esac

echo "This will overwrite $PDIR_BIN/dtella and completely replace $PDIR_BASE "
echo "Press enter to continue, or Ctrl-C at any time to abort..."
read ENTER

test -d "$DIR_BASE" || mkdir -p "$DIR_BASE" || { echo "Could not make $PDIR_BASE; abort" && exit 5; }
cd "$DIR_BASE"

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
	if ! svn checkout "$SVNR" . ; then echo "could not complete svn checkout; abort."; exit 2; fi
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
./setup.py --upgrade-type=tar clean -a > /dev/null # enables the !UPGRADE command
rm -f "$DEPS"
echo
echo "$PROD \033[1msuccessfully installed\033[0m into $PDIR_BASE"

cd
mkdir -p "$DIR_BIN" && cat > "$DIR_BIN/dtella" << EOF
#!/bin/sh
exec python -O $PDIR_BASE/dtella.py "\$@"
EOF

if [ $? -gt 0 ]; then
	echo "However, could not install $PDIR_BIN/dtella run script."
else
	chmod +x "$DIR_BIN/dtella"
	echo "You can run it with $PDIR_BIN/dtella"
fi
exit 0
