# config_manager.py
import json
import os
import logging

CONFIG_FILE = 'config.json'
_config_data = {}  # Сюда будет загружена конфигурация

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')


def load_config():
    """
    Загружает конфигурацию из config.json.
    Если файл не существует, создает его с дефолтными значениями
    и выводит предупреждение.
    """
    global _config_data
    if not os.path.exists(CONFIG_FILE):
        logging.warning(f"Файл конфигурации '{CONFIG_FILE}' не найден. Создаю новый с дефолтными значениями.")
        default_config = {
            "BOT_TOKEN": "YOUR_BOT_TOKEN_HERE",
            "ADMIN_USERNAME": "YOUR_ADMIN_USERNAME_HERE",
            "ADMIN_PASSWORD": "default_password",  # Дефолтный пароль
            "PHOTO_URLS": [
                "https://example.com/placeholder_photo1.jpg",
                "https://example.com/placeholder_photo2.jpg"
            ]
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4)
        _config_data = default_config
        logging.info(f"Создан новый файл '{CONFIG_FILE}'. Пожалуйста, обновите его своими данными.")
        return _config_data

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            _config_data = json.load(f)
        logging.info(f"Конфигурация успешно загружена из '{CONFIG_FILE}'.")
    except json.JSONDecodeError as e:
        logging.error(f"Ошибка чтения JSON из '{CONFIG_FILE}': {e}. Убедитесь, что файл имеет корректный формат JSON.")
        _config_data = {}  # Очищаем конфиг, чтобы избежать использования некорректных данных
    except Exception as e:
        logging.error(f"Неизвестная ошибка при загрузке '{CONFIG_FILE}': {e}")
        _config_data = {}

    return _config_data


def save_config():
    """Сохраняет текущую конфигурацию в config.json."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(_config_data, f, indent=4)
        logging.info(f"Конфигурация успешно сохранена в '{CONFIG_FILE}'.")
    except Exception as e:
        logging.error(f"Ошибка сохранения конфигурации в '{CONFIG_FILE}': {e}")


def get_setting(key: str, default_value=None):
    """Получает значение настройки по ключу."""
    return _config_data.get(key, default_value)


def set_setting(key: str, value: str):
    """Устанавливает значение настройки и сохраняет конфигурацию."""
    _config_data[key] = value
    save_config()


# Загружаем конфигурацию сразу при импорте модуля
load_config()

