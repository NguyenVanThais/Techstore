"""Diem khoi chay ung dung.

Chay tu thu muc goc du an:  python -m app.main
"""
from app.views.main_window import MainWindow


def main():
    app = MainWindow()
    # neu ket noi DB that bai, MainWindow.__init__ da goi destroy()
    if app.winfo_exists():
        app.mainloop()


if __name__ == "__main__":
    main()
