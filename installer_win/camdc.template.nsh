; Dtella-Cambridge - NSIS Installer Script Common Header
; Copyright (c) 2009-      Andyhhp (http://camdc.pcriot.com)
;
; This program is free software; you can redistribute it and/or
; modify it under the terms of the GNU General Public License
; as published by the Free Software Foundation; either version 2
; of the License, or (at your option) any later version.
;
; This program is distributed in the hope that it will be useful,
; but WITHOUT ANY WARRANTY; without even the implied warranty of
; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
; GNU General Public License for more details.
;
; You should have received a copy of the GNU General Public License
; along with this program; if not, write to the Free Software
; Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


;Product defines
!define PRODUCT_NAME "CamDC"
!define PRODUCT_VERSION "2.7"
!define PRODUCT_PUBLISHER "infinity0 & Andyhhp"
!define PRODUCT_WEB_SITE "http://camdc.pcriot.com/"

!define UNINST_NAME "Uninstall ${PRODUCT_NAME}"
!define PRODUCT_REG_BASE "Software"

;Dtella defines
!define DTELLA_NAME "PATCH_ME"
!define DTELLA_VERSION "PATCH_ME"
!define DTELLA_WEB_SITE "http://camdc.pcriot.com/"
!define DTELLA_PUBLISHER "infinity0 & Andyhhp"
!define DTELLA_SOURCENAME "PATCH_ME"
!define DTELLA_DIR_REGKEY "${PRODUCT_REG_BASE}\${DTELLA_NAME}"
!define DTELLA_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${DTELLA_NAME}"

;StrongDC
!define SDC_NAME "StrongDC"
!define SDC_VERSION "2.22"
!define SDC_WEB_SITE "http://strongdc.sourceforge.net/index.php?lang=eng"
!define SDC_PUBLISHER "BigMuscle"
!define SDC_DIR_REGKEY "${PRODUCT_REG_BASE}\${SDC_NAME}"
!define SDC_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${SDC_NAME}"

Function Kill_Dtella
    SetShellVarContext all
    ExecWait '"$INSTDIR\${DTELLA_NAME}\dtella.exe" --terminate'
FunctionEnd

Function un.Kill_Dtella
    SetShellVarContext all
    ExecWait '"$INSTDIR\${DTELLA_NAME}\dtella.exe" --terminate'
FunctionEnd

Function Kill_SDC
    SetShellVarContext all
    ExecWait "taskkill /IM StrongDC.exe"
FunctionEnd

Function un.Kill_SDC
    SetShellVarContext all
    ExecWait "taskkill /IM StrongDC.exe"
FunctionEnd

Function LaunchBoth
    Exec '"$INSTDIR\${DTELLA_NAME}\dtella.exe"'
    Exec '"$INSTDIR\${SDC_NAME}\StrongDC.exe"'
FunctionEnd

Function PatchSettings

    Push "__PATCHME_DOWNLOADDIR__\"
    Push "$DOCUMENTS\${SDC_NAME}\Downloads\"
    Push all
    Push all
    Push "$APPDATA\${SDC_NAME}\Settings\DCPlusPlus.xml"
    Call AdvReplaceInFile

    Push "__PATCHME_TEMPDIR__\"
    Push "$DOCUMENTS\${SDC_NAME}\Unfinished\"
    Push all
    Push all
    Push "$APPDATA\${SDC_NAME}\Settings\DCPlusPlus.xml"
    Call AdvReplaceInFile

    Push "__PATCHME_LOGDIR__\"
    Push "$DOCUMENTS\${SDC_NAME}\Logs\"
    Push all
    Push all
    Push "$APPDATA\${SDC_NAME}\Settings\DCPlusPlus.xml"
    Call AdvReplaceInFile

FunctionEnd
;Push "C:\Program"             #-- text to be replaced  within the " "
;Push "C:/Program"             #-- replace with anything within the " "
;Push all                      #-- replace all occurrences 
;Push all                      #-- replace all occurrences 
;Push $INSTDIR\httpd.conf      #-- file to replace in 
;Call AdvReplaceInFile         #-- Call the Function
 
;>>>>>> Function Junction BEGIN
;Original Written by Afrow UK
; Rewrite to Replace on line within text by rainmanx
; This version works on R4 and R3 of Nullsoft Installer
; It replaces whatever is in the line throughout the entire text matching it.
Function AdvReplaceInFile
Exch $0 ;file to replace in
Exch
Exch $1 ;number to replace after
Exch
Exch 2
Exch $2 ;replace and onwards
Exch 2
Exch 3
Exch $3 ;replace with
Exch 3
Exch 4
Exch $4 ;to replace
Exch 4
Push $5 ;minus count
Push $6 ;universal
Push $7 ;end string
Push $8 ;left string
Push $9 ;right string
Push $R0 ;file1
Push $R1 ;file2
Push $R2 ;read
Push $R3 ;universal
Push $R4 ;count (onwards)
Push $R5 ;count (after)
Push $R6 ;temp file name
;-------------------------------
GetTempFileName $R6
FileOpen $R1 $0 r ;file to search in
FileOpen $R0 $R6 w ;temp file
StrLen $R3 $4
StrCpy $R4 -1
StrCpy $R5 -1
loop_read:
ClearErrors
FileRead $R1 $R2 ;read line
IfErrors exit
StrCpy $5 0
StrCpy $7 $R2
loop_filter:
IntOp $5 $5 - 1
StrCpy $6 $7 $R3 $5 ;search
StrCmp $6 "" file_write2
StrCmp $6 $4 0 loop_filter
StrCpy $8 $7 $5 ;left part
IntOp $6 $5 + $R3
StrCpy $9 $7 "" $6 ;right part
StrLen $6 $7
StrCpy $7 $8$3$9 ;re-join
StrCmp -$6 $5 0 loop_filter
IntOp $R4 $R4 + 1
StrCmp $2 all file_write1
StrCmp $R4 $2 0 file_write2
IntOp $R4 $R4 - 1
IntOp $R5 $R5 + 1
StrCmp $1 all file_write1
StrCmp $R5 $1 0 file_write1
IntOp $R5 $R5 - 1
Goto file_write2
file_write1:
FileWrite $R0 $7 ;write modified line
Goto loop_read
file_write2:
FileWrite $R0 $7 ;write modified line
Goto loop_read
exit:
FileClose $R0
FileClose $R1
SetDetailsPrint none
Delete $0
Rename $R6 $0
Delete $R6
SetDetailsPrint both
;-------------------------------
Pop $R6
Pop $R5
Pop $R4
Pop $R3
Pop $R2
Pop $R1
Pop $R0
Pop $9
Pop $8
Pop $7
Pop $6
Pop $5
Pop $4
Pop $3
Pop $2
Pop $1
Pop $0
FunctionEnd
