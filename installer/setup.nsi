; -*- coding: utf-8 -*-
; 包装设计器 Packaging Designer — NSIS 安装脚本（amd64 · 免管理员 · 用户级安装）
; 编译： "C:\Program Files (x86)\NSIS\makensis.exe" setup.nsi
; 产出： installer\包装设计器-1.0.0-setup.exe

Unicode true
SetCompressor /SOLID lzma
SetCompressorDictSize 64

!define APP_NAME       "包装设计器"
!define APP_NAME_EN    "Packaging Designer"
!define APP_VERSION    "1.0.6"
!define APP_PUBLISHER  "周豪（hawchou1995）"
!define APP_URL        "https://github.com/hawchou1995/packaging-designer"
!define APP_EXE        "PackagingDesigner.exe"
!define SRC_DIR        "..\dist106\PackagingDesigner"

Name "${APP_NAME} ${APP_VERSION}"
BrandingText "${APP_NAME} ${APP_VERSION} · ${APP_URL}"
OutFile "包装设计器-${APP_VERSION}-setup.exe"
RequestExecutionLevel user
InstallDir "$LOCALAPPDATA\Programs\PackagingDesigner"
InstallDirRegKey HKCU "Software\PackagingDesigner" "InstallDir"
ShowInstDetails show
ShowUninstDetails show

VIProductVersion "1.0.6.0"
VIAddVersionKey /LANG=2052 "ProductName"     "${APP_NAME} ${APP_NAME_EN}"
VIAddVersionKey /LANG=2052 "CompanyName"     "${APP_PUBLISHER}"
VIAddVersionKey /LANG=2052 "FileDescription" "${APP_NAME} 安装程序"
VIAddVersionKey /LANG=2052 "FileVersion"     "${APP_VERSION}"
VIAddVersionKey /LANG=2052 "ProductVersion"  "${APP_VERSION}"
VIAddVersionKey /LANG=2052 "LegalCopyright"  "MIT License"

!include "MUI2.nsh"
!define MUI_ICON   "..\resources\app.ico"
!define MUI_UNICON "..\resources\app.ico"
!define MUI_ABORTWARNING

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!define MUI_FINISHPAGE_RUN "$INSTDIR\${APP_EXE}"
!define MUI_FINISHPAGE_RUN_TEXT "立即运行 ${APP_NAME}"
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "主程序" SEC_MAIN
    SetOutPath "$INSTDIR"
    SetOverwrite on
    File /r "${SRC_DIR}\*.*"
    WriteRegStr HKCU "Software\PackagingDesigner" "InstallDir" "$INSTDIR"

    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0
    CreateShortCut "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk" "$INSTDIR\uninstall.exe"
    CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\${APP_EXE}" "" "$INSTDIR\${APP_EXE}" 0

    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "DisplayName" "${APP_NAME}（${APP_NAME_EN}）"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "Publisher" "${APP_PUBLISHER}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "URLInfoAbout" "${APP_URL}"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "InstallLocation" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "NoModify" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "NoRepair" 1
    WriteRegDWORD HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner" "EstimatedSize" 420000
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\卸载 ${APP_NAME}.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"
    Delete "$DESKTOP\${APP_NAME}.lnk"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\PackagingDesigner"
    DeleteRegKey HKCU "Software\PackagingDesigner"
SectionEnd

Function .onInit
    ; 默认勾选桌面快捷方式（此处仅提示用户安装位置，保持流程简洁）
FunctionEnd
