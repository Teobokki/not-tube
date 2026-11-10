#!/bin/sh
# ONE Windows build: PyInstaller onedir -> Inno Setup installer + portable zip
set -e
export PATH=/workspace/wine-portable/current/bin:$PATH WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd /workspace/not-tube
V=1.0.0
rm -rf build "dist/NOT TUBE"
wine 'C:\Python311\python.exe' -m PyInstaller --noconfirm "NOT TUBE.spec" > pyi.log 2>&1; echo PYI_DONE
wine 'C:\InnoSetup\ISCC.exe' installer.iss > iss.log 2>&1; echo ISS_DONE
cd dist && rm -f NOT-TUBE-$V-Windows-x64.zip && python3 -c "import shutil;shutil.make_archive('NOT-TUBE-$V-Windows-x64','zip','.','NOT TUBE')" && echo ZIP_DONE
ls -la
sha256sum "NOT-TUBE-Setup-$V.exe" "NOT-TUBE-$V-Windows-x64.zip"
