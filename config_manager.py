# config_manager.py
import json
import os

CONFIG_FILE = "config.json"

def load_config():
    """Wczytuje konfigurację z pliku config.json."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Błąd: Plik {CONFIG_FILE} jest uszkodzony. Używam domyślnych wartości.")
            return {} # lub można rzucić wyjątek albo zwrócić None
    return {}

def save_config(config_data):
    """Zapisuje konfigurację do pliku config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except IOError:
        print(f"Błąd: Nie można zapisać pliku {CONFIG_FILE}.")
        return False

def get_work_directory():
    """Pobiera ścieżkę roboczą z konfiguracji."""
    config = load_config()
    return config.get("work_directory")

def set_work_directory(path):
    """Ustawia i zapisuje ścieżkę roboczą w konfiguracji."""
    config = load_config() # Załaduj istniejącą, aby nie nadpisać innych ustawień
    config["work_directory"] = path
    return save_config(config)

if __name__ == '__main__':
    # Testowanie
    # set_work_directory("/tmp/test_work_dir")
    print(f"Aktualny katalog roboczy: {get_work_directory()}")
    # set_work_directory(None) # Usunięcie dla testów
    # print(f"Aktualny katalog roboczy po usunięciu: {get_work_directory()}")