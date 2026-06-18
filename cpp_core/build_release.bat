@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" x64

set "CMAKE=%USERPROFILE%\AppData\Roaming\Python\Python314\site-packages\cmake\data\bin\cmake.exe"
set "NINJA=%USERPROFILE%\AppData\Roaming\Python\Python314\Scripts\ninja.exe"
set "PB11=C:\Users\julia\AppData\Roaming\Python\Python314\site-packages\pybind11\share\cmake\pybind11"
set "PYEXE=C:\Python314\python.exe"
set "SRC=C:\Users\julia\Desktop\School\Projects GitHub\psycholinguistic_text_analyzer\cpp_core"
set "BLD=C:\Users\julia\Desktop\School\Projects GitHub\psycholinguistic_text_analyzer\cpp_core\build"
set "INST=C:\Users\julia\Desktop\School\Projects GitHub\psycholinguistic_text_analyzer"

echo [1/3] Configuring...
"%CMAKE%" -B "%BLD%" -S "%SRC%" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_MAKE_PROGRAM="%NINJA%" -Dpybind11_DIR="%PB11%" -DPython_EXECUTABLE="%PYEXE%"
if errorlevel 1 ( echo Configure FAILED & exit /b 1 )

echo [2/3] Building...
"%CMAKE%" --build "%BLD%" --config Release
if errorlevel 1 ( echo Build FAILED & exit /b 1 )

echo [3/3] Installing to project root...
"%CMAKE%" --install "%BLD%" --prefix "%INST%"
if errorlevel 1 ( echo Install FAILED & exit /b 1 )

echo SUCCESS: psycho_core.pyd is in the project root.
