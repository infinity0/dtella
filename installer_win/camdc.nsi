; Dtella-Cambridge - NSIS Installer Script
; Copyright (C) 2007-2008  Dtella Labs (http://dtella.org/)
; Copyright (C) 2007-2008  Paul Marks (http://pmarks.net/)
; Copyright (C) 2007-2008  Jacob Feisley (http://feisley.com/)
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

!verbose 4

;Includes
!include "camdc.nsh"
!include MUI2.nsh



;General Settings
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${PRODUCT_NAME}-${PRODUCT_VERSION}.exe"
InstallDir "$PROGRAMFILES\${PRODUCT_NAME}"
ShowInstDetails show
ShowUninstDetails show
SetCompressor lzma
CRCCheck on
XPStyle on
RequestExecutionLevel admin ;for vista UAC


;Start the MUI specific stuff
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install-colorful.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall-colorful.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_BITMAP "resources\topbanner-cam.bmp"
!define MUI_HEADERIMAGE_UNBITMAP "resources\topbanner-cam.bmp"
!define MUI_WELCOMEFINISHPAGE_BITMAP "resources\welcome-cam.bmp"
;!define MUI_UNWELCOMEFINISHPAGE_BITMAP "resources\welcome-cam.bmp"

;Installer
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
        !define MUI_COMPONENTSPAGE_SMALLDESC
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
        !define MUI_FINISHPAGE_RUN
        !define MUI_FINISHPAGE_RUN_TEXT "Start Dtella and StrongDC"
        !define MUI_FINISHPAGE_RUN_FUNCTION "LaunchBoth"
!insertmacro MUI_PAGE_FINISH

;Uninstaller


!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_COMPONENTS
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE English


Section "Dtella (Required)" INST_DTELLA ;Install the main dtella application
    Call Kill_Dtella

    ;Add normal files
    SetOutPath "$INSTDIR\${DTELLA_NAME}"
    File "dtella.exe"
    File "msvcr71.dll"
    File "readme.txt"
    File "changelog.txt"
    File "changelog_adc.txt"
    
    ;Add Start menu links
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}\Dtella (Run in Background).lnk" "$INSTDIR\${DTELLA_NAME}\dtella.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}\Kill Dtella.lnk" "$INSTDIR\${DTELLA_NAME}\dtella.exe" "--terminate" "$INSTDIR\${DTELLA_NAME}\dtella.exe" 1
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}\Readme.lnk" "$INSTDIR\${DTELLA_NAME}\readme.txt"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}\Changelog.lnk" "$INSTDIR\${DTELLA_NAME}\changelog.txt"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}\Changelog_Adc.lnk" "$INSTDIR\${DTELLA_NAME}\changelog_adc.txt"

    ;Create Reg Keys for uninstaller/updater to read
    WriteRegStr HKLM "${DTELLA_DIR_REGKEY}" "Version" "${DTELLA_VERSION}"
    WriteRegStr HKLM "${DTELLA_DIR_REGKEY}" "InstDir" "$INSTDIR\${DTELLA_NAME}\"
    WriteRegDWORD HKLM "${DTELLA_DIR_REGKEY}" "InstProgam" 1
    WriteRegDWORD HKLM "${DTELLA_DIR_REGKEY}" "InstSettings" 1
    
    ;Create Reg Keys to add the uninstaller to the control pannel
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "DisplayName" "${DTELLA_NAME}"
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${DTELLA_NAME}\dtella.exe"
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "DisplayVersion" "${DTELLA_VERSION}"
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "URLInfoAbout" "${DTELLA_WEB_SITE}"
    WriteRegStr HKLM "${DTELLA_UNINST_KEY}" "Publisher" "${DTELLA_PUBLISHER}"

SectionEnd

Section "StrongDC (Required)" INST_SDC ;Install the main StrongDC client
    Call Kill_SDC
    
    ;Add normal files
    SetOutPath "$INSTDIR\${SDC_NAME}"
    File "..\sdc222\StrongDC.exe"
    File "..\sdc222\unicows.dll"
    File "..\sdc222\EN.xml"
    File "..\sdc222\dcppboot.xml"
    File "..\sdc222\License.txt"
    File "..\sdc222\changelog-en.txt"
    SetOutPath "$INSTDIR\${SDC_NAME}\EmoPacks"
    File "..\sdc222\EmoPacks\Kolobok.xml"
    SetOutPath "$INSTDIR\${SDC_NAME}\EmoPacks\Kolobok"
    File "..\sdc222\EmoPacks\Kolobok\*.bmp"

    ;Create the settings folder in appdata and populate it
    SetShellVarContext current
    CreateDirectory "$APPDATA\${SDC_NAME}\Settings"
    SetOutPath "$APPDATA\${SDC_NAME}\Settings"
    File "..\sdc222\Settings\*.*"
    
    ;Create the default folders in current users documents, then patch the settings file
    
    CreateDirectory "$DOCUMENTS\${SDC_NAME}\Logs"
    CreateDirectory "$DOCUMENTS\${SDC_NAME}\Downloads"
    CreateDirectory "$DOCUMENTS\${SDC_NAME}\Unfinished"
    Call PatchSettings
    
    ;Create the start menu links
    SetShellVarContext all
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}"
    CreateDirectory "$SMPROGRAMS\${PRODUCT_NAME}\${SDC_NAME}"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${SDC_NAME}\StrongDC.lnk" "$INSTDIR\${SDC_NAME}\StrongDC.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${SDC_NAME}\License.lnk" "$INSTDIR\${SDC_NAME}\License.txt"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${SDC_NAME}\ChangeLog.lnk" "$INSTDIR\${SDC_NAME}\changelog-en.txt"
    
    ;Create Reg Keys for uninstaller/updater to read
    WriteRegStr HKLM "${SDC_DIR_REGKEY}" "Version" "${SDC_VERSION}"
    WriteRegStr HKLM "${SDC_DIR_REGKEY}" "InstDir" "$INSTDIR\${SDC_NAME}\"
    WriteRegDWORD HKLM "${SDC_DIR_REGKEY}" "InstProgam" 1
    WriteRegDWORD HKLM "${SDC_DIR_REGKEY}" "InstSettings" 1
    
    ;Create Reg Keys to add the uninstaller to the control pannel
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "DisplayName" "${SDC_NAME}"
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "DisplayIcon" "$INSTDIR\${SDC_NAME}\StrongDC.exe"
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "DisplayVersion" "${SDC_VERSION}"
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "URLInfoAbout" "${SDC_WEB_SITE}"
    WriteRegStr HKLM "${SDC_UNINST_KEY}" "Publisher" "${SDC_PUBLISHER}"
    
SectionEnd

Section "Run Dtella on Startup (Recommended)" INST_STARTUP ;Provide a link to run dtella at startup
    SetShellVarContext all
    CreateShortCut "$SMSTARTUP\Dtella.lnk" "$INSTDIR\${DTELLA_NAME}\dtella.exe"
SectionEnd

Section /o "Dtella Source Code" INST_DTELLA_SOURCE ;Give the users the dtella source if they wany
    SetOutPath "$INSTDIR\${DTELLA_NAME}"
    File "${DTELLA_SOURCENAME}.tar.bz2"
SectionEnd

Section -Post ;Finally, create the uninstaller
    SetOutPath "$INSTDIR"
    WriteUninstaller "$INSTDIR\uninst.exe"
    CreateShortCut "$SMPROGRAMS\${PRODUCT_NAME}\${UNINST_NAME}.lnk" "$INSTDIR\uninst.exe"
SectionEnd

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${INST_DTELLA} "The main Dtella program."
    !insertmacro MUI_DESCRIPTION_TEXT ${INST_SDC} "The StrongDC client"
    !insertmacro MUI_DESCRIPTION_TEXT ${INST_STARTUP} "This will automatically load Dtella for you when your computer starts."
    !insertmacro MUI_DESCRIPTION_TEXT ${INST_DTELLA_SOURCE} "If you don't know what this is for, then you don't need it."
!insertmacro MUI_FUNCTION_DESCRIPTION_END


Section "un.Dtella Program" UNINST_DTELLA_PROGRAM
    Call un.Kill_Dtella
    SetShellVarContext all
    RMDir /r /REBOOTOK "$INSTDIR\${DTELLA_NAME}"
    RMDir /r /REBOOTOK "$SMPROGRAMS\${PRODUCT_NAME}\${DTELLA_NAME}"
    Delete "$SMSTARTUP\Dtella.lnk"
    WriteRegDWORD HKLM "${DTELLA_DIR_REGKEY}" "InstProgam" 0
SectionEnd

Section "un.Dtella Settings" UNINST_DTELLA_SETTINGS
    RMDir /r /REBOOTOK "$PROFILE\.dtella"
    WriteRegDWORD HKLM "${DTELLA_DIR_REGKEY}" "InstSettings" 0
SectionEnd

Section "un.StrongDC Program" UNINST_SDC_PROGRAM
    Call un.Kill_SDC
    RMDir /r /REBOOTOK "$INSTDIR\${SDC_NAME}"
    RMDir /r /REBOOTOK "$SMPROGRAMS\${PRODUCT_NAME}\${SDC_NAME}"
    WriteRegDWORD HKLM "${SDC_DIR_REGKEY}" "InstProgam" 0
SectionEnd

Section "un.StrongDC Settings" UNINST_SDC_SETTINGS
    SetShellVarContext current
    RMDir /r /REBOOTOK "$APPDATA\${SDC_NAME}"
    WriteRegDWORD HKLM "${SDC_DIR_REGKEY}" "InstSettings" 0
SectionEnd

Section -un.Post
    ClearErrors

    ;Read and act on Dtella Keys
    ReadRegDWORD $0 HKLM "${DTELLA_DIR_REGKEY}" "InstProgam"
    IfErrors Dtella_Error
    ReadRegDWORD $1 HKLM "${DTELLA_DIR_REGKEY}" "InstSettings"
    IfErrors Dtella_Error

    IntOp $0 $0 | $1
    IntCmp $0 0 0 Dtella_Done Dtella_Done
    
    DeleteRegKey HKLM "${DTELLA_DIR_REGKEY}"
    DeleteRegKey HKLM "${DTELLA_UNINST_KEY}"
    Goto Dtella_Done
    
    Dtella_Error:
    IntOp $0 0 + 0     
    
    Dtella_Done:    
    
    ;Read and act on SDC keys
    ReadRegDWORD $2 HKLM "${SDC_DIR_REGKEY}" "InstProgam"
    IfErrors SDC_Error
    ReadRegDWORD $3 HKLM "${SDC_DIR_REGKEY}" "InstSettings"
    IfErrors SDC_Error

    IntOp $2 $2 | $3
    IntCmp $2 0 0 SDC_Done SDC_Done
    
    DeleteRegKey HKLM "${SDC_DIR_REGKEY}"
    DeleteRegKey HKLM "${SDC_UNINST_KEY}"
    Goto SDC_Done
    
    SDC_Error:
    IntOp $2 0 + 0
    
    SDC_Done:

    ;Consider deleting the uninstaller
    IntOp $0 $0 | $2
    IntCmp $0 0 0 UN_Done UN_Done
    
    SetShellVarContext all
    Delete /rebootok "$INSTDIR\uninst.exe"
    RMDir /rebootok "$INSTDIR"
    DeleteRegKey /ifempty HKLM "${PRODUCT_REG_BASE}" #importent here - by default, reg_base is 'Software\'
    RMDir /r  "$SMPROGRAMS\${PRODUCT_NAME}"
    UN_Done:

SectionEnd

!insertmacro MUI_UNFUNCTION_DESCRIPTION_BEGIN
    !insertmacro MUI_DESCRIPTION_TEXT ${UNINST_DTELLA_PROGRAM} "Uninstalls the Dtella program."
    !insertmacro MUI_DESCRIPTION_TEXT ${UNINST_DTELLA_SETTINGS} "Uninstalls your Dtella settings."
    !insertmacro MUI_DESCRIPTION_TEXT ${UNINST_SDC_PROGRAM} "Uninstalls the StrongDC client."
    !insertmacro MUI_DESCRIPTION_TEXT ${UNINST_SDC_SETTINGS} "Uninstalls your StrongDC settings."
!insertmacro MUI_UNFUNCTION_DESCRIPTION_END
