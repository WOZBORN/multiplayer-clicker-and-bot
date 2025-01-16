import threading
import time
import tkinter as tk
from tkinter import messagebox

import requests

import session_manager as sm

BASE_URL = "http://127.0.0.1:5000"  # Адрес API

class ClickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Кликер")
        self.session = None
        self.click_count = 0
        self.synced_clicks = 0

        # Основные элементы
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(padx=20, pady=20)

        saved_nickname = sm.load_session()
        if saved_nickname:
            try:
                user_info = self._get_user_info(saved_nickname)
                self.session = {"nickname": saved_nickname}
                self.click_count = user_info.get("clicks", 0)
                self.synced_clicks = self.click_count
                self.create_clicker_frame()
            except Exception as e:
                print(f"Ошибка загрузки сессии: {e}")
                self.create_login_frame()
        else:
            self.create_login_frame()

    def _get_user_info(self, tg_nickname):
        response = requests.get(f"{BASE_URL}/show_user_info/{tg_nickname}")
        return response.json()

    def create_login_frame(self):
        """Создает интерфейс для входа в систему."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        tk.Label(self.main_frame, text="Авторизация", font=("Arial", 16)).pack(pady=10)

        tk.Label(self.main_frame, text="Никнейм:").pack()
        self.nickname_entry = tk.Entry(self.main_frame)
        self.nickname_entry.pack()

        tk.Label(self.main_frame, text="Пароль:").pack()
        self.password_entry = tk.Entry(self.main_frame, show="*")
        self.password_entry.pack()

        tk.Button(self.main_frame, text="Войти", command=self.login).pack(pady=10)

    def create_clicker_frame(self):
        """Создает интерфейс для кликера."""
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        tk.Label(self.main_frame, text=f"Добро пожаловать, {self.session['nickname']}!", font=("Arial", 16)).pack(pady=10)
        self.click_label = tk.Label(self.main_frame, text=f"Клики: {self.click_count}", font=("Arial", 14))
        self.click_label.pack(pady=10)

        tk.Button(self.main_frame, text="Кликнуть!", font=("Arial", 14), command=self.increment_click).pack(pady=10)

        tk.Button(self.main_frame, text="Выйти", command=self.logout).pack(pady=10)

        # Запускаем синхронизацию в фоновом потоке
        self.sync_thread = threading.Thread(target=self.sync_clicks, daemon=True)
        self.sync_thread.start()

    def login(self):
        """Обработка входа пользователя."""
        nickname = self.nickname_entry.get()
        password = self.password_entry.get()

        if not nickname or not password:
            messagebox.showerror("Ошибка", "Введите никнейм и пароль")
            return

        data = {"tg_nickname": nickname, "password": password}
        response = requests.post(f"{BASE_URL}/login_user", json=data)

        if response.status_code == 200:
            self.session = {"nickname": nickname}
            sm.save_session(nickname)
            user_info = self._get_user_info(nickname)
            self.click_count = user_info.get("clicks", 0)
            self.synced_clicks = self.click_count
            self.create_clicker_frame()
        else:
            messagebox.showerror("Ошибка", "Неверный никнейм или пароль")

    def logout(self):
        """Обработка выхода пользователя."""
        self.session = None
        self.click_count = 0
        sm.clear_session()
        self.create_login_frame()

    def increment_click(self):
        """Увеличение счетчика кликов."""
        self.click_count += 1
        self.click_label.config(text=f"Клики: {self.click_count}")

    def sync_clicks(self):
        """Синхронизация кликов с сервером каждые 5 секунд."""
        while self.session:
            if self.synced_clicks != self.click_count:
                data = {
                    "tg_nickname": self.session.get("nickname"),  # Используем telegram_id из сессии
                    "clicks": self.click_count
                }
                response = requests.post(f"{BASE_URL}/sync_clicks", json=data)

                if not response.status_code == 200:
                    print(f"Ошибка синхронизации кликов: {response.json().get('message')}")
                else:
                    self.synced_clicks = self.click_count
            time.sleep(5)

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("400x300")  # Устанавливаем фиксированные размеры окна (ширина x высота)
    app = ClickerApp(root)
    root.mainloop()
