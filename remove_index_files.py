import os
import logging
import config_manager
from pathlib import Path

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def remove_index_files(root_path: str) -> tuple[int, int]:
    """
    Usuwa wszystkie pliki index.json z folderu i jego podfolderów.
    
    Args:
        root_path: Ścieżka do folderu głównego
        
    Returns:
        tuple[int, int]: (liczba usuniętych plików, liczba błędów)
    """
    removed_count = 0
    error_count = 0
    
    try:
        # Sprawdź czy folder istnieje
        if not os.path.exists(root_path):
            logger.error(f"Folder nie istnieje: {root_path}")
            return 0, 1
            
        # Rekurencyjne przeszukiwanie folderów
        for root, dirs, files in os.walk(root_path):
            if "index.json" in files:
                index_path = os.path.join(root, "index.json")
                try:
                    os.remove(index_path)
                    removed_count += 1
                    logger.info(f"Usunięto: {index_path}")
                except Exception as e:
                    error_count += 1
                    logger.error(f"Błąd usuwania {index_path}: {e}")
                    
    except Exception as e:
        logger.error(f"Błąd podczas przeszukiwania folderu {root_path}: {e}")
        error_count += 1
        
    return removed_count, error_count

def main():
    """Funkcja główna"""
    print("=== USUWANIE PLIKÓW INDEX.JSON ===")
    
    # Pobierz folder roboczy z konfiguracji
    work_dir = config_manager.get_work_directory()
    if not work_dir:
        print("❌ Nie znaleziono folderu roboczego w konfiguracji!")
        return
        
    if not os.path.exists(work_dir):
        print(f"❌ Folder nie istnieje: {work_dir}")
        return
        
    if not os.path.isdir(work_dir):
        print(f"❌ Podana ścieżka nie jest folderem: {work_dir}")
        return
        
    print(f"\n🔍 Analizuję folder: {work_dir}")
    
    # Potwierdzenie od użytkownika
    confirm = input("\n⚠️ Czy na pewno chcesz usunąć wszystkie pliki index.json? (t/n): ").lower()
    if confirm != 't':
        print("Operacja anulowana.")
        return
        
    # Usuń pliki
    removed, errors = remove_index_files(work_dir)
    
    # Podsumowanie
    print("\n=== PODSUMOWANIE ===")
    print(f"✅ Usunięto plików: {removed}")
    if errors > 0:
        print(f"❌ Liczba błędów: {errors}")
    print("\nOperacja zakończona.")

if __name__ == "__main__":
    main() 