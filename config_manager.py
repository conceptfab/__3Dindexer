# config_manager.py
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "work_directory": None,
    "preview_size": 400,
    "thumbnail_size": 150,
    "performance": {
        "max_worker_threads": 4,
        "cache_previews": True,
        "lazy_loading": True,
        "max_cache_size_mb": 1024,
        "cache_ttl_hours": 24,
    },
    "ui": {"animation_speed": 300, "hover_delay": 500, "max_preview_size": 1200},
    "security": {
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
        "max_file_size_mb": 50,
    },
}


class ConfigError(Exception):
    """Wyjątek dla błędów konfiguracji."""

    pass


def validate_config(config: Dict[str, Any]) -> bool:
    """Waliduje konfigurację."""
    try:
        if not isinstance(config, dict):
            raise ConfigError("Konfiguracja musi być słownikiem")

        required_keys = ["work_directory", "preview_size", "thumbnail_size"]
        for key in required_keys:
            if key not in config:
                raise ConfigError(f"Brak wymaganego klucza: {key}")

        if config["work_directory"] and not os.path.exists(config["work_directory"]):
            raise ConfigError(
                f"Katalog roboczy nie istnieje: {config['work_directory']}"
            )

        return True
    except Exception as e:
        logger.error(f"Błąd walidacji konfiguracji: {e}")
        return False


def load_config() -> Dict[str, Any]:
    """Wczytuje konfigurację z pliku config.json z domyślnymi wartościami."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                config = DEFAULT_CONFIG.copy()
                config.update(user_config)

                if not validate_config(config):
                    logger.warning(
                        "Używam domyślnej konfiguracji z powodu błędów walidacji"
                    )
                    return DEFAULT_CONFIG.copy()

                return config
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        logger.error(f"Błąd wczytywania konfiguracji: {e}")
        return DEFAULT_CONFIG.copy()


def save_config(config_data: Dict[str, Any]) -> bool:
    """Zapisuje konfigurację do pliku config.json."""
    try:
        if not validate_config(config_data):
            return False

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Błąd zapisywania konfiguracji: {e}")
        return False


def get_config_value(key: str, default: Any = None) -> Any:
    """Pobiera wartość z konfiguracji."""
    try:
        config = load_config()
        keys = key.split(".")
        value = config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    except Exception as e:
        logger.error(f"Błąd pobierania wartości konfiguracji: {e}")
        return default


def set_config_value(key: str, value: Any) -> bool:
    """Ustawia wartość w konfiguracji."""
    try:
        config = load_config()
        keys = key.split(".")
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        return save_config(config)
    except Exception as e:
        logger.error(f"Błąd ustawiania wartości konfiguracji: {e}")
        return False


# Funkcje pomocnicze dla kompatybilności
def get_work_directory() -> Optional[str]:
    return get_config_value("work_directory")


def set_work_directory(path: str) -> bool:
    path_obj = Path(path)
    if not path_obj.exists():
        logger.error(f"Katalog nie istnieje: {path}")
        return False
    return set_config_value("work_directory", str(path_obj.absolute()))


def get_preview_size() -> int:
    return get_config_value("preview_size", 400)


def get_thumbnail_size() -> int:
    return get_config_value("thumbnail_size", 150)


def get_allowed_extensions() -> List[str]:
    return get_config_value(
        "security.allowed_extensions",
        [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    )


def get_archive_color(file_extension):
    """Pobiera kolor dla danego typu archiwum."""
    try:
        colors = get_config_value("archive_colors", {})
        # Konwertuj rozszerzenie na małe litery dla porównania
        ext_lower = file_extension.lower() if file_extension else ""

        # Sprawdź czy mamy kolor dla tego rozszerzenia
        if ext_lower in colors:
            return colors[ext_lower]

        # Sprawdź specjalne przypadki (tar.gz, tar.bz2)
        if ext_lower.endswith(".tar.gz"):
            return colors.get(".tar.gz", colors.get("default", "#6c757d"))
        elif ext_lower.endswith(".tar.bz2"):
            return colors.get(".tar.bz2", colors.get("default", "#6c757d"))

        return colors.get("default", "#6c757d")
    except Exception as e:
        logger.error(f"Błąd pobierania koloru archiwum: {e}")
        return "#6c757d"


def get_archive_colors():
    """Pobiera wszystkie kolory archiwów jako słownik."""
    return get_config_value("archive_colors", {})


if __name__ == "__main__":
    # Testowanie
    # set_work_directory("/tmp/test_work_dir")
    print(f"Aktualny katalog roboczy: {get_work_directory()}")
    # set_work_directory(None) # Usunięcie dla testów
    # print(f"Aktualny katalog roboczy po usunięciu: {get_work_directory()}")
