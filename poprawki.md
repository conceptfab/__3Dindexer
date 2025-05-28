Zmiany w pliku ai_sbert_matcher.py
1. Dodanie importu config_manager
Plik: ai_sbert_matcher.py
Sekcja: Importy na początku pliku
Proponowany kod:
pythonimport config_manager  # Dodaj po linii z innymi importami
2. Modyfikacja klasy AIFolderProcessor - konstruktor
Plik: ai_sbert_matcher.py
Funkcja: AIFolderProcessor.__init__
Proponowany kod:
pythondef __init__(self):
    self.matcher = SBERTFileMatcher()
    # Pobierz folder roboczy z konfiguracji
    self.work_directory = config_manager.get_work_directory()
    if not self.work_directory:
        logger.warning("Brak folderu roboczego w konfiguracji")
3. Nowa funkcja start_ai_processing
Plik: ai_sbert_matcher.py
Funkcja: Nowa funkcja w klasie AIFolderProcessor
Proponowany kod:
pythondef start_ai_processing(self, progress_callback=None):
    """Rozpoczyna przetwarzanie AI od folderu roboczego z konfiguracji"""
    if not self.work_directory:
        logger.error("Brak folderu roboczego w konfiguracji")
        if progress_callback:
            progress_callback("❌ Brak folderu roboczego w konfiguracji")
        return False
    
    if not os.path.isdir(self.work_directory):
        logger.error(f"Folder roboczy nie istnieje: {self.work_directory}")
        if progress_callback:
            progress_callback(f"❌ Folder roboczy nie istnieje: {self.work_directory}")
        return False
    
    logger.info(f"🤖 Rozpoczynam przetwarzanie AI dla: {self.work_directory}")
    if progress_callback:
        progress_callback(f"🤖 Rozpoczynam przetwarzanie AI dla: {self.work_directory}")
    
    return self.process_folder_recursive(self.work_directory, progress_callback)
4. Modyfikacja process_folder_recursive
Plik: ai_sbert_matcher.py
Funkcja: AIFolderProcessor.process_folder_recursive
Proponowany kod:
pythondef process_folder_recursive(self, root_folder_path, progress_callback=None):
    """
    Przetwarza folder rekurencyjnie (łącznie z podfolderami)
    """
    logger.info(f"🚀 Rozpoczynam rekurencyjne przetwarzanie AI: {root_folder_path}")
    
    if progress_callback:
        progress_callback(f"🚀 Rozpoczynam rekurencyjne przetwarzanie AI: {root_folder_path}")

    processed_folders = 0
    error_folders = 0

    for root, dirs, files in os.walk(root_folder_path):
        # Pomiń linki symboliczne
        if os.path.islink(root):
            continue

        # Sprawdź czy folder zawiera index.json (został już przeskanowany)
        index_json_path = os.path.join(root, "index.json")
        if not os.path.exists(index_json_path):
            logger.debug(f"⏭️ Pomijam folder bez index.json: {root}")
            continue

        logger.info(f"📁 Przetwarzam AI dla folderu: {root}")
        if progress_callback:
            progress_callback(f"📁 Przetwarzam AI dla folderu: {root}")

        if self.process_folder(root, progress_callback):
            processed_folders += 1
        else:
            error_folders += 1

    success_msg = f"✅ Przetwarzanie AI zakończone: {processed_folders} folderów OK, {error_folders} błędów"
    logger.info(success_msg)
    if progress_callback:
        progress_callback(success_msg)
    
    return processed_folders > 0
5. Modyfikacja process_folder
Plik: ai_sbert_matcher.py
Funkcja: AIFolderProcessor.process_folder
Proponowany kod:
pythondef process_folder(self, folder_path, progress_callback=None):
    """
    Przetwarza jeden folder - dodaje dane AI do index.json
    """
    logger.info(f"🔍 Przetwarzanie AI folderu: {folder_path}")

    if progress_callback:
        progress_callback(f"🔍 Przetwarzanie AI folderu: {folder_path}")

    if not os.path.isdir(folder_path):
        logger.error(f"❌ Ścieżka nie jest folderem: {folder_path}")
        return False

    # Sprawdź czy istnieje index.json (folder musi być już przeskanowany)
    index_json_path = os.path.join(folder_path, "index.json")
    if not os.path.exists(index_json_path):
        logger.warning(f"⚠️ Brak index.json w folderze: {folder_path}")
        if progress_callback:
            progress_callback(f"⚠️ Brak index.json w folderze: {folder_path}")
        return False

    # Zbierz pliki
    archive_files, image_files = self.collect_files_in_folder(folder_path)

    if not archive_files and not image_files:
        logger.info(f"⚠️ Folder pusty (brak plików do analizy AI): {folder_path}")
        if progress_callback:
            progress_callback(f"⚠️ Folder pusty (brak plików do analizy AI): {folder_path}")
        return True

    logger.info(f"📊 Znaleziono: {len(archive_files)} archiwów, {len(image_files)} obrazów")

    # Załaduj istniejący index.json
    index_data = self.load_existing_index(folder_path)

    # Sprawdź czy AI już przetwarzało ten folder
    if "AI_processing_date" in index_data:
        logger.info(f"🔄 Aktualizuję istniejące dane AI dla: {folder_path}")
        if progress_callback:
            progress_callback(f"🔄 Aktualizuję istniejące dane AI dla: {folder_path}")
    else:
        logger.info(f"🆕 Pierwsze przetwarzanie AI dla: {folder_path}")
        if progress_callback:
            progress_callback(f"🆕 Pierwsze przetwarzanie AI dla: {folder_path}")

    # Jeśli nie ma podstawowej struktury, utwórz ją
    if "folder_info" not in index_data:
        index_data["folder_info"] = {
            "path": os.path.abspath(folder_path),
            "scan_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    # Dodaj sekcję AI
    ai_data = {
        "AI_processing_date": datetime.now().isoformat(),
        "AI_model_info": {
            "name": "sentence-transformers/all-MiniLM-L6-v2",
            "type": "SBERT",
            "version": "1.0",
        },
        "AI_file_analysis": {
            "total_archive_files": len(archive_files),
            "total_image_files": len(image_files),
            "archive_files": archive_files,
            "image_files": image_files,
        },
    }

    # Znajdź dopasowania AI
    if archive_files and image_files:
        logger.info("🤖 Uruchamiam analizę AI...")
        if progress_callback:
            progress_callback("🤖 Uruchamiam analizę AI...")
        
        start_time = time.time()

        matches = self.matcher.find_best_matches(archive_files, image_files)

        ai_time = time.time() - start_time
        logger.info(f"⏱️ Analiza AI zakończona w {ai_time:.2f}s")
        if progress_callback:
            progress_callback(f"⏱️ Analiza AI zakończona w {ai_time:.2f}s")

        ai_data["AI_matches"] = matches
        ai_data["AI_statistics"] = {
            "total_possible_pairs": len(archive_files) * len(image_files),
            "found_matches": len(matches),
            "match_rate": len(matches) / len(archive_files) if archive_files else 0,
            "processing_time_seconds": ai_time,
            "high_confidence_matches": len(
                [m for m in matches if m["confidence_level"] == "HIGH"]
            ),
            "medium_confidence_matches": len(
                [m for m in matches if m["confidence_level"] == "MEDIUM"]
            ),
        }

        # Dodaj szczegółowe analizy dla najlepszych dopasowań
        detailed_analyses = []
        for match in matches[:3]:  # Tylko 3 najlepsze dla oszczędności miejsca
            analysis = self.matcher.analyze_similarity_details(
                match["archive_file"], match["image_file"]
            )
            detailed_analyses.append(analysis)

        ai_data["AI_detailed_analysis_samples"] = detailed_analyses

        if progress_callback:
            progress_callback(f"✅ Znaleziono {len(matches)} dopasowań AI")

    else:
        ai_data["AI_matches"] = []
        ai_data["AI_statistics"] = {
            "total_possible_pairs": 0,
            "found_matches": 0,
            "match_rate": 0,
            "reason": "Brak plików archiwów lub obrazów do dopasowania",
        }

    # Dodaj dane AI do index_data
    for key, value in ai_data.items():
        index_data[key] = value

    # Zapisz plik
    self.save_index_with_ai_data(folder_path, index_data)

    return True
6. Modyfikacja funkcji main
Plik: ai_sbert_matcher.py
Funkcja: main
Proponowany kod:
pythondef main():
    """
    Funkcja główna - automatycznie pobiera folder roboczy z konfiguracji
    """
    print("🤖 AI SBERT File Matcher - Automatyczne przetwarzanie")
    print("=" * 60)

    # Utwórz procesor i sprawdź konfigurację
    processor = AIFolderProcessor()
    
    if not processor.work_directory:
        print("❌ Brak folderu roboczego w konfiguracji!")
        print("💡 Uruchom najpierw główną aplikację i ustaw folder roboczy.")
        return

    print(f"📁 Folder roboczy z konfiguracji: {processor.work_directory}")

    if not os.path.exists(processor.work_directory):
        print(f"❌ Folder roboczy nie istnieje: {processor.work_directory}")
        return

    # Zapytaj o tryb przetwarzania
    print("\n🔄 Tryby przetwarzania:")
    print("1. Automatyczne (cały folder roboczy)")
    print("2. Konkretny folder")
    print("3. Wyjście")
    
    choice = input("\nWybierz opcję (1-3): ").strip()
    
    if choice == "1":
        # Automatyczne przetwarzanie całego folderu roboczego
        print(f"\n🚀 Rozpoczynam automatyczne przetwarzanie AI...")
        processor.start_ai_processing(print)
        
    elif choice == "2":
        # Konkretny folder
        test_folder = input("Podaj ścieżkę do konkretnego folderu: ").strip()
        if not test_folder:
            print("❌ Nie podano ścieżki")
            return
            
        if not os.path.exists(test_folder):
            print(f"❌ Folder nie istnieje: {test_folder}")
            return
            
        print(f"🔍 Przetwarzam konkretny folder: {test_folder}")
        processor.process_folder_recursive(test_folder, print)
        
    elif choice == "3":
        print("👋 Do widzenia!")
        return
    else:
        print("❌ Nieprawidłowy wybór")
        return

    print("\n🎉 Przetwarzanie AI zakończone! Sprawdź pliki index.json w folderach.")
    print("🔍 Wyszukaj klucze zaczynające się od 'AI_' aby zobaczyć wyniki.")
7. Dodanie funkcji pomocniczej get_work_directory_from_config
Plik: ai_sbert_matcher.py
Funkcja: Nowa funkcja pomocnicza (dodaj przed klasą AIFolderProcessor)
Proponowany kod:
pythondef get_work_directory_from_config():
    """Pobiera folder roboczy z konfiguracji lub None jeśli nie ustawiony"""
    try:
        work_dir = config_manager.get_work_directory()
        if work_dir and os.path.isdir(work_dir):
            logger.info(f"📁 Znaleziono folder roboczy w konfiguracji: {work_dir}")
            return work_dir
        else:
            logger.warning("⚠️ Brak prawidłowego folderu roboczego w konfiguracji")
            return None
    except Exception as e:
        logger.error(f"❌ Błąd pobierania folderu roboczego z konfiguracji: {e}")
        return None
Podsumowanie zmian
Te zmiany sprawią, że ai_sbert_matcher.py:

Pobiera folder roboczy z config.json - tak jak scanner_logic.py
Działa rekurencyjnie na całym drzewie katalogów - przetwarzając wszystkie foldery z index.json
Integruje się z istniejącym workflow - uzupełnia dane w już istniejących plikach index.json
Zapewnia kompatybilność z główną aplikacją - używa tej samej konfiguracji
Oferuje elastyczne opcje uruchamiania - automatycznie lub dla konkretnego folderu

Po wprowadzeniu tych zmian można uruchomić ai_sbert_matcher.py jako skrypt standalone, który automatycznie pobierze folder roboczy z konfiguracji i przetworzy całe drzewo katalogów, dodając dane AI do istniejących plików index.json.