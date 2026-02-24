import sys
import os

# Ana proje dizinini ekle, böylece `frontend.app` importları çalışır
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from frontend.app import LoginWindow

if __name__ == "__main__":
    app = LoginWindow()
    app.mainloop()
