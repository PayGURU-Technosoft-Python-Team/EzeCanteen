; EzeeCanteen Installer Script
; Created using NSIS

!define APP_NAME "EzeeCanteen"
!define COMP_NAME "PayGURU Technosoft Pvt. Ltd."
!define VERSION "1.0.0"
!define COPYRIGHT "PayGURU Technosoft Pvt. Ltd. © 2025"
!define DESCRIPTION "Canteen Management System"
!define INSTALLER_NAME "EzeeCanteenSetup.exe"
!define MAIN_APP_EXE "EzeeCanteen.exe"

SetCompressor lzma

Name "${APP_NAME}"
Caption "${APP_NAME} ${VERSION} Installer"
OutFile "${INSTALLER_NAME}"
InstallDir "$PROGRAMFILES\${APP_NAME}"
InstallDirRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation"

RequestExecutionLevel admin

!include "MUI2.nsh"

!define MUI_ABORTWARNING
!define MUI_ICON "fp.png"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    SetOverwrite try
    
    ; Main executable and resources
    File "dist\${MAIN_APP_EXE}"
    File "appSettings.json"
    File "*.xlsx"
    File "*.png"
    File "*.jpg"
    File "*.xml"
    
    ; Create directories
    CreateDirectory "$INSTDIR\Reports"
    CreateDirectory "$INSTDIR\logs"
    CreateDirectory "$INSTDIR\output"
    
    ; Create Start Menu shortcuts
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"
    
    ; Create desktop shortcut
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${MAIN_APP_EXE}"
    
    ; Write uninstall information to the registry
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$INSTDIR\uninstall.exe"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayIcon" "$INSTDIR\${MAIN_APP_EXE}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${COMP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${VERSION}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    ; Remove files and directories
    Delete "$INSTDIR\${MAIN_APP_EXE}"
    Delete "$INSTDIR\appSettings.json"
    Delete "$INSTDIR\*.xlsx"
    Delete "$INSTDIR\*.png"
    Delete "$INSTDIR\*.jpg"
    Delete "$INSTDIR\*.xml"
    Delete "$INSTDIR\uninstall.exe"
    
    RMDir "$INSTDIR\Reports"
    RMDir "$INSTDIR\logs"
    RMDir "$INSTDIR\output"
    RMDir "$INSTDIR"
    
    ; Remove shortcuts
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    
    ; Remove registry keys
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd 