import sys
from PyQt5.QtWidgets import QApplication
from settings import EzeeCanteenWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Set up asyncio event loop
    import nest_asyncio
    nest_asyncio.apply()
    
    # Create and show the main window
    window = EzeeCanteenWindow()
    window.show()
    
    # Start the application
    sys.exit(app.exec_()) 