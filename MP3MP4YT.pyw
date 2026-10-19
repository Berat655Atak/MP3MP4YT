import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import customtkinter as ctk
from ui.main_window import YouTubeDownloaderApp
from ui.splash import SplashLoader

def main():
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    SplashLoader(root, on_complete=YouTubeDownloaderApp)
    root.mainloop()

if __name__ == "__main__":
    main()
