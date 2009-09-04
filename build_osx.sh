# set FILEBASE
eval $(python makevars.py)

BLDIR="installer_osx"
OUTDIR="dist"

python setup.py clean -a
rm -f $BLDIR/template.sparseimage
rm -f $OUTDIR/$FILEBASE.dmg

python setup.py py2app || exit

hdiutil eject /Volumes/Dtella
hdiutil eject /Volumes/$FILEBASE

hdiutil convert $BLDIR/template.dmg -format UDSP -o $BLDIR/template
hdiutil attach $BLDIR/template.sparseimage

cp -R dist/$FILENAME.app/ /Volumes/Dtella/$FILENAME.app
cp docs/readme.txt /Volumes/Dtella/
cp docs/changelog.txt /Volumes/Dtella/
cp docs/changelog_adc.txt /Volumes/Dtella/
cp docs/gpl.txt /Volumes/Dtella/

diskutil rename /Volumes/Dtella/ $FILEBASE
hdiutil eject /Volumes/$FILEBASE

hdiutil convert $BLDIR/template.sparseimage -format UDBZ -o $OUTDIR/$FILEBASE.dmg

rm $BLDIR/template.sparseimage
