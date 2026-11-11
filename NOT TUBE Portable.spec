# -*- mode: python ; coding: utf-8 -*-
# Portable build: ONE standalone .exe (no zip)
from PyInstaller.utils.hooks import collect_all
d, b, h = collect_all('imageio_ffmpeg')
a = Analysis(['not_tube.py'],
             datas=[('assets', 'assets'), ('samples', 'samples')] + d,
             binaries=b,
             hiddenimports=['PIL.ImageTk', 'PIL.ImageDraw', 'PIL.ImageFont', 'PIL.ImageGrab'] + h,
             excludes=['matplotlib', 'scipy', 'pandas', 'IPython', 'pytest', 'torch', 'cv2'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='NOT-TUBE-PORTABLE', console=False, upx=False,
          runtime_tmpdir=None, version='version.txt', icon=['assets/logo.ico'])
