@echo off
echo Setting up EzeeCanteen...

REM Creating application directory
md "%USERPROFILE%\Desktop\EzeeCanteen" 2>nul

REM Copy the executable
echo Copying application files...
copy "dist\EzeeCanteen.exe" "%USERPROFILE%\Desktop\EzeeCanteen\" /y

REM Copy required data files
echo Copying configuration files...
copy "appSettings.json" "%USERPROFILE%\Desktop\EzeeCanteen\" /y
copy "*.xlsx" "%USERPROFILE%\Desktop\EzeeCanteen\" /y
copy "*.png" "%USERPROFILE%\Desktop\EzeeCanteen\" /y
copy "*.jpg" "%USERPROFILE%\Desktop\EzeeCanteen\" /y

REM Create subdirectories
echo Creating directories...
md "%USERPROFILE%\Desktop\EzeeCanteen\Reports" 2>nul
md "%USERPROFILE%\Desktop\EzeeCanteen\logs" 2>nul
md "%USERPROFILE%\Desktop\EzeeCanteen\output" 2>nul

REM Create shortcut on desktop
echo Creating desktop shortcut...
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\EzeeCanteen.lnk'); $s.TargetPath = '%USERPROFILE%\Desktop\EzeeCanteen\EzeeCanteen.exe'; $s.Save()"

echo Setup complete!
echo The EzeeCanteen application has been installed to your Desktop.
pause 