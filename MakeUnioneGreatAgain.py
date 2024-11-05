from kivy.config import Config
Config.set('input', 'mouse', 'mouse,multitouch_on_demand')

import requests
import json
import time
import os
import threading
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserIconView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.animation import Animation
from kivy.core.window import Window
import urllib3

# Отключаем предупреждения о небезопасном соединении
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Устанавливаем размер окна и стиль фона
Window.size = (400, 500)
Window.clearcolor = (0.4, 0.4, 0.4, 1)  # Серый фон окна


class MyGrid(GridLayout):
    def __init__(self, **kwargs):
        super(MyGrid, self).__init__(**kwargs)
        self.cols = 1

        # Заголовок
        self.add_widget(Label(text='Download Manager', font_size=24, bold=True, size_hint=(1, 0.2)))

        # Поля ввода API ключа и дат
        grid_inputs = GridLayout(cols=2, size_hint=(1, 0.6), padding=10, spacing=10)

        # API Key
        grid_inputs.add_widget(Label(text='API Key:'))
        self.api_key = TextInput(multiline=False, hint_text="Введите API ключ")
        grid_inputs.add_widget(self.api_key)

        # Date From
        grid_inputs.add_widget(Label(text='Date From:'))
        self.date_from = TextInput(multiline=False, hint_text="YYYY-MM-DD")
        grid_inputs.add_widget(self.date_from)

        # Date To
        grid_inputs.add_widget(Label(text='Date To:'))
        self.date_to = TextInput(multiline=False, hint_text="YYYY-MM-DD")
        grid_inputs.add_widget(self.date_to)

        self.add_widget(grid_inputs)

        # Кнопка для выбора папки
        self.select_folder_btn = Button(text="Select Folder", size_hint=(1, 0.2))
        self.select_folder_btn.bind(on_press=self.show_file_chooser)
        self.add_widget(self.select_folder_btn)

        # Кнопка для загрузки данных
        self.submit = Button(text="Download Data", size_hint=(1, 0.2))
        self.submit.bind(on_press=self.start_background_thread)
        self.add_widget(self.submit)

        # Отображение сообщений
        self.message_label = Label(text="Сообщения будут здесь", size_hint=(1, 0.2))
        self.add_widget(self.message_label)

        # Папка по умолчанию
        self.download_folder = os.path.expanduser("~")

    def log_message(self, message):
        # Обновляем текст в интерфейсе для сообщений
        self.message_label.text = message

    def show_file_chooser(self, instance):
        # Открываем окно для выбора папки
        content = BoxLayout(orientation='vertical')
        file_chooser = FileChooserIconView(path=self.download_folder, dirselect=True)
        select_button = Button(text="Select")
        select_button.bind(on_press=lambda x: self.set_folder_and_close(file_chooser.path, popup))
        content.add_widget(file_chooser)
        content.add_widget(select_button)

        popup = Popup(title="Select Download Folder", content=content, size_hint=(0.9, 0.9))
        popup.open()

    def set_folder_and_close(self, folder_path, popup):
        # Устанавливаем выбранную папку
        if os.path.isdir(folder_path):  # Проверяем, что это действующая папка
            self.download_folder = folder_path
            self.log_message(f"Выбрана папка: {self.download_folder}")
        else:
            self.log_message("Ошибка: выбрана недействительная папка")
        popup.dismiss()

    def start_background_thread(self, instance):
        # Запуск потока, чтобы основной поток не зависал
        thread = threading.Thread(target=self.run_all_scripts)
        thread.start()

    def run_all_scripts(self):
        api_key = self.api_key.text.strip()
        date_from = self.date_from.text.strip()
        date_to = self.date_to.text.strip()

        # Проверка на пустые поля и на корректность формата даты
        if not api_key or not date_from or not date_to:
            self.log_message("Please provide all inputs")
            return

        if date_from >= date_to:
            self.log_message("Date From must be earlier than Date To")
            return

        try:
            base_url = 'https://eu1.unione.io/ru/transactional/api/v1'
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-API-KEY': api_key
            }

            # Step 1: Delete Dumps
            self.log_message("Отправляю запрос на удаление старых дампов...")
            request_body = {}
            r = requests.post(base_url + '/event-dump/list.json', json=request_body, headers=headers, verify=False)
            r.raise_for_status()
            data = r.json()

            if 'event_dumps' in data and len(data['event_dumps']) > 0:
                for i in range(min(20, len(data['event_dumps']))):
                    dumps = data['event_dumps'][i]['dump_id']
                    request_body = {"dump_id": dumps}
                    r = requests.post(base_url + '/event-dump/delete.json', json=request_body, headers=headers, verify=False)
                    r.raise_for_status()
                    self.log_message(f"Удалён дамп с ID: {dumps}")
            else:
                self.log_message("Нет старых дампов. Продолжаем...")

            # Step 2: Order Dump
            self.log_message("Отправляю запрос на Dump...")
            start_time = f"{date_from} 00:00:00"
            end_time = f"{date_to} 23:59:59"
            request_body = {
                "start_time": start_time,
                "end_time": end_time,
                "limit": 50000,
                "delimiter": ";",
                "format": "csv"
            }

            r = requests.post(base_url + '/event-dump/create.json', json=request_body, headers=headers, verify=False)
            r.raise_for_status()
            
            API_data_create = r.json()
            if 'dump_id' in API_data_create:
                dump_id = API_data_create['dump_id']
                self.log_message("Всё окей. Запрашиваю файлы...")
            else:
                self.log_message("Ошибка: dump_id не получен.")
                return

            # Step 3: Wait for Dump to be Ready and Get Download Links
            request_body = {"dump_id": dump_id}
            wait_time = 15  # Уменьшено для тестирования

            while True:
                r = requests.post(base_url + '/event-dump/get.json', json=request_body, headers=headers, verify=False)
                r.raise_for_status()
                data = r.json()

                if r.status_code == 200:
                    dump_status = data['event_dump']['dump_status']
                    if dump_status == "ready":
                        self.log_message("Ссылки получены. Скачиваю...")
                        download_links = [file['url'] for file in data['event_dump']['files']]
                        break
                    else:
                        self.log_message(f"Статус дампа: {dump_status}. Жду {wait_time} сек...")
                        time.sleep(wait_time)
                else:
                    self.log_message("Ошибка получения статуса дампа.")
                    return

            # Step 4: Download the Files
            downloaded_files = []
            for i, url in enumerate(download_links):
                file_name = url.split("/")[-1]
                self.log_message(f"Скачиваю файл: {file_name}")
                response = requests.get(url)

                if response.status_code == 200:
                    full_file_path = os.path.join(self.download_folder, file_name)
                    with open(full_file_path, 'wb') as file:
                        file.write(response.content)
                    downloaded_files.append(full_file_path)
                    self.log_message(f"Файл {file_name} скачан успешно в {self.download_folder}.")
                else:
                    self.log_message(f"Ошибка при скачивании файла {file_name}. Код ответа: {response.status_code}")

            # Финальное сообщение об успешном завершении и запуск анимации
            self.log_message("Всё готово")
            self.animate_success()

        except requests.RequestException as e:
            self.log_message(f"Ошибка: {e}")

    def animate_success(self):
        # Создание анимации для отображения "Готово!"
        animation = Animation(font_size=40, duration=0.5) + Animation(font_size=20, duration=0.5)
        animation.start(self.message_label)


class MyApp(App):
    def build(self):
        return MyGrid()


if __name__ == "__main__":
    MyApp().run()