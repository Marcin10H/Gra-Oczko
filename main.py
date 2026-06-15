# Uruchomienie: python main.py
# exe: python -m PyInstaller --noconfirm GraOczko.spec

from gui.app import OczkoApp


def main():
    app = OczkoApp()
    app.mainloop()


if __name__ == "__main__":
    main()
