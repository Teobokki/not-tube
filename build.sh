#!/bin/sh
# ONE Windows build: PyInstaller onedir -> Inno Setup installer, plus ONE standalone portable .exe (no zip)
set -e
export PATH=/workspace/wine-portable/current/bin:$PATH WINEPREFIX=/workspace/exwifi/.wine WINEDEBUG=-all
cd /workspace/not-tube
V=1.0.8
rm -rf build "dist/NOT TUBE" dist/NOT-TUBE-PORTABLE.exe
wine 'C:\Python311\python.exe' -m PyInstaller --noconfirm "NOT TUBE.spec" > pyi.log 2>&1; echo PYI_DONE
wine 'C:\InnoSetup\ISCC.exe' installer.iss > iss.log 2>&1; echo ISS_DONE
wine 'C:\Python311\python.exe' -m PyInstaller --noconfirm "NOT TUBE Portable.spec" > pyi_portable.log 2>&1; echo PYI_PORTABLE_DONE
mv -f dist/NOT-TUBE-PORTABLE.exe "dist/NOT-TUBE-$V-Portable.exe"
cd dist && ls -la "NOT-TUBE-Setup-$V.exe" "NOT-TUBE-$V-Portable.exe"
sha256sum "NOT-TUBE-Setup-$V.exe" "NOT-TUBE-$V-Portable.exe"
