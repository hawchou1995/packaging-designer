# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 规格：包装设计器（onedir + windowed），资源 / OCP / ezdxf 全量收集。

构建：  pyinstaller --noconfirm --clean packaging-designer.spec
产物：  dist/PackagingDesigner/（内含 PackagingDesigner.exe）
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

HERE = os.path.abspath(os.getcwd())

datas = [("resources", "resources")]
binaries = []
hiddenimports = ["matplotlib.backends.backend_agg", "matplotlib.backends.backend_pdf"]

for pkg in ("OCP", "ezdxf", "matplotlib", "PIL", "fontTools"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as e:                                    # pragma: no cover
        print("collect_all 跳过", pkg, e)

hiddenimports += collect_submodules("OCP")
hiddenimports += ["pkg_resources", "setuptools", "xml.etree.ElementTree"]

excludes = [
    "tkinter", "PyQt5", "PyQt6", "PySide2", "IPython", "notebook", "pytest",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickWidgets",
    "PySide6.Qt3DCore", "PySide6.Qt3DRender", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtBluetooth",
    "PySide6.QtDesigner", "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtPositioning", "PySide6.QtSensors", "PySide6.QtSerialPort",
    "PySide6.QtWebSockets", "PySide6.QtWebChannel", "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSvgWidgets", "PySide6.QtOpenGLWidgets", "PySide6.QtNfc", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtSpatialAudio", "PySide6.QtStateMachine", "PySide6.QtUiTools",
    "scipy", "pandas", "sympy", "h5py", "sphinx",
]

a = Analysis(
    ["app.py"],
    pathex=[HERE, os.path.join(HERE, "core"), os.path.join(HERE, "ui")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PackagingDesigner",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=os.path.join(HERE, "resources", "app.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="PackagingDesigner",
)
