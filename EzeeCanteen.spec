# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['settings.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('appSettings.json', '.'),
        ('*.xlsx', '.'),
        ('*.png', '.'),
        ('*.jpg', '.'),
        ('*.xml', '.'),
    ],
    hiddenimports=[
        'mysql.connector',
        'PyQt5.QtWidgets',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'timeBase',
        'CanteenSettings',
        'AddMail',
        'AddPrinter',
        'AddDevice',
        'licenseManager',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EzeeCanteen',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='fp.png',
)
