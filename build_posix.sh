#!/bin/dash
eval $(python makevars.py)

export OUTDIR="dist"
export BLDDIR="build"

mkdir -p "$OUTDIR"
mkdir -p "$BLDDIR"

echo "collecting source code in $BLDDIR/$FILEBASE"
rm -rf "$BLDDIR/$FILEBASE"
mkdir -p "$BLDDIR/$FILEBASE"
cp --parents dtella.py \
             dtella/__init__.py \
             dtella/local_config.py \
             dtella/client/*.py \
             dtella/common/*.py \
             dtella/modules/*.py \
             docs/readme.txt \
             docs/changelog*.txt \
             docs/requirements.txt \
             docs/gpl.txt \
    "$BLDDIR/$FILEBASE"

cd "$BLDDIR"
tar cvjf "../$OUTDIR/$FILEBASE.tar.bz2" "$FILEBASE"
cd ..
echo "built tarball in $OUTDIR/$FILEBASE.tar.bz2"

python setup.py "EXT=tar.bz2" "EXT_CMD=tar xjf" "EXT_VRB=tar xvjf" \
	"SVNR=http://dtella-cambridge.googlecode.com/svn/branches/adc" \
	"DEPS=dtella_deps.tar.bz2"
