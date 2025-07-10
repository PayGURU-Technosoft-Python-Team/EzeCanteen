# EzeeCanteen Application

## Installation Options

### Option 1: Using the Executable Directly
1. Copy the `EzeeCanteen.exe` from the `dist` folder to your desired location
2. Copy the `appSettings.json` file to the same location
3. Create subdirectories: `Reports`, `logs`, and `output`
4. Run the application by double-clicking `EzeeCanteen.exe`

### Option 2: Using the Setup Batch File
1. Double-click the `setup.bat` file
2. The script will:
   - Create an EzeeCanteen folder on your desktop
   - Copy all required files
   - Create a desktop shortcut
3. Run the application from the created shortcut

### Option 3: Building an Installer (Requires NSIS)
1. Install NSIS (Nullsoft Scriptable Install System) from https://nsis.sourceforge.io/
2. Right-click on `installer.nsi` and select "Compile NSIS Script"
3. This will create an `EzeeCanteenSetup.exe` installer
4. Distribute this installer to users

## Building the Executable

If you need to rebuild the executable:

1. Install PyInstaller: `pip install pyinstaller`
2. Run PyInstaller with: `python -m PyInstaller EzeeCanteen.spec`
3. The executable will be created in the `dist` folder

## Troubleshooting

- If you encounter a MySQL connection error, ensure MySQL is properly installed on your system
- If you see "libmysql.dll not found", you need to install MySQL Connector for Python or copy the DLL to the application directory
- If the application doesn't start, check Windows Event Viewer for details

## System Requirements

- Windows 10 or later
- 4GB RAM or more
- Screen resolution: 1024x768 or higher
- MySQL server (accessible via network)

## Support

For any issues, please contact PayGURU Technosoft Pvt. Ltd. 