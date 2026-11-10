# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
d, b, h = collect_all('imageio_ffmpeg')
a = Analysis(['not_tube.py'],
             datas=[('assets', 'assets')] + d,
             binaries=b,
             hiddenimports=['PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageGrab'] + h,
             excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'pytest', 'torch', 'cv2'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='NOT TUBE', console=False, upx=False,
          version='version.txt', icon=['assets/logo.ico'])
coll = COLLECT(exe, a.binaries, a.datas, upx=False, name='NOT TUBE')
