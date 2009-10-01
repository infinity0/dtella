; Dtella Updater - NSIS Installer Script
; Copyright (C) 2009-  Andyhhp
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

!define PRODUCT_NAME "PATCH_ME"
!define PRODUCT_VERSION "PATCH_ME"
!define PRODUCT_SIMPLENAME "PATCH_ME"

!define PRODUCT_REGKEY "Software\${PRODUCT_NAME}"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"

SetCompressor lzma

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "${PRODUCT_SIMPLENAME}.updater.exe"
SilentInstall silent
Icon "${NSISDIR}\Contrib\Graphics\Icons\modern-install-colorful.ico"
CRCCheck on
XPStyle on
RequestExecutionLevel admin ;for vista UAC

Section
    # Give dtella enough time to warn the user to reconnect
    Sleep "200"
    ClearErrors
    
    ;Check the registry
    ReadRegStr $0 HKLM "${PRODUCT_REGKEY}" "InstDir"
    IfErrors 0 Patch_Done
    
        ClearErrors
        ReadRegStr $0 HKLM "Software\ADtella@Cambridge" "InstDir"
        IfErrors Error_No_Key
        
        WriteRegStr HKLM "${PRODUCT_REGKEY}" "InstDir" $0
        
        ReadRegDWORD $0 HKLM "Software\ADtella@Cambridge" "InstProgram"
        WriteRegDWORD HKLM "${PRODUCT_REGKEY}" "InstProgram" $0
        
        ReadRegDWORD $0 HKLM "Software\ADtella@Cambridge" "InstSettings"
        WriteRegDWORD HKLM "${PRODUCT_REGKEY}" "InstSettings" $0
        
        DeleteRegKey HKLM "Software\ADtella@Cambridge"
        
        ReadRegStr $0 HKLM "${PRODUCT_REGKEY}" "InstDir"
    
    Patch_Done:
    
    ;Terminate the current dtella process
    SetShellVarContext all
    ExecWait '"$0\dtella.exe" --terminate'
    
    ;Write the new version
    SetOutPath $0
    File "dtella.exe"
    File "changelog.txt"
    File "changelog_adc.txt"

    ;Update the reg version strings - nothing else is changing
    WriteRegStr HKLM "${PRODUCT_REGKEY}" "Version" "${PRODUCT_VERSION}"
    WriteRegStr HKLM "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"

    ;See if the user has the previous source.  If so, give the new source as well
    IfFileExists "$0\${PRODUCT_NAME}*.tar.bz2" 0 No_Source
        File "${PRODUCT_SIMPLENAME}.tar.bz2"
    No_Source:
    
    ;Restart the dtella process
    Exec '"$0\dtella.exe"'
    
    ;Delete this file on next reboot
    Call GetExeName
    Pop $1
    Delete /rebootok "$1"

    Return
    
    ;If there is no reg key from a previous installer, something is wrong
    Error_No_Key:
    MessageBox MB_OK "Cant read installation regkey.  Please ensure you have installed CamDC.  If all else fails, ask for help in main chat"
    Return
SectionEnd

Function GetExeName
	Push $0
	Push $1
	Push $2
	System::Call /NOUNLOAD 'kernel32::GetModuleFileNameA(i 0, t .r0, i 1024)'
	System::Call 'kernel32::GetLongPathNameA(t r0, t .r1, i 1024)i .r2'
	StrCmp $2 error +2
	StrCpy $0 $1
	Pop $2
	Pop $1
	Exch $0
FunctionEnd