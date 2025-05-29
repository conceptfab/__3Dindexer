import json
import os
from datetime import datetime
from typing import Dict, Tuple


def load_config() -> Dict:
    """Ładuje konfigurację z pliku config.json"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Błąd odczytu config.json: {e}")
        return {}


def load_index_json(folder_path: str) -> Dict:
    """Ładuje plik index.json z folderu"""
    index_path = os.path.join(folder_path, "index.json")
    if not os.path.exists(index_path):
        return {}

    try:
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Błąd odczytu {index_path}: {e}")
        return {}


def analyze_folder(folder_path: str) -> Tuple[int, int, int, int]:
    """
    Analizuje folder i zwraca statystyki dopasowań
    Zwraca: (liczba_zwykłych_dopasowań, liczba_ai_dopasowań,
            liczba_plików_bez_podglądu, liczba_obrazów_bez_pary)
    """
    data = load_index_json(folder_path)
    if not data:
        return 0, 0, 0, 0

    # Liczba dopasowań zwykłym algorytmem
    classic_matches = len(data.get("files_with_previews", []))

    # Liczba dopasowań AI
    ai_matches = len(data.get("AI_matches", []))

    # Liczba plików bez podglądu
    files_without_preview = len(data.get("files_without_previews", []))

    # Liczba obrazów bez pary
    other_images = len(data.get("other_images", []))

    return classic_matches, ai_matches, files_without_preview, other_images


def calculate_effectiveness(matches: int, total_files: int) -> float:
    """Oblicza procentową skuteczność dopasowań"""
    if total_files == 0:
        return 0.0
    return (matches / total_files) * 100


def analyze_work_directory(work_dir: str) -> Dict:
    """
    Analizuje cały folder roboczy i zwraca statystyki
    """
    results = {
        "folders": {},  # Statystyki dla każdego folderu
        "total": {  # Suma dla całego folderu roboczego
            "classic_matches": 0,
            "ai_matches": 0,
            "files_without_preview": 0,
            "other_images": 0,
            "folders_analyzed": 0,
        },
    }

    # Przejdź przez wszystkie foldery
    for root, dirs, files in os.walk(work_dir):
        if "index.json" in files:
            # Analizuj folder
            classic, ai, no_preview, other = analyze_folder(root)

            # Dodaj statystyki dla folderu
            rel_path = os.path.relpath(root, work_dir)
            # Całkowita liczba plików do dopasowania
            total_files = classic + no_preview

            results["folders"][rel_path] = {
                "classic_matches": classic,
                "ai_matches": ai,
                "files_without_preview": no_preview,
                "other_images": other,
                "classic_effectiveness": calculate_effectiveness(classic, total_files),
                "ai_effectiveness": calculate_effectiveness(ai, total_files),
                "improvement_percent": (
                    calculate_effectiveness(ai, total_files)
                    - calculate_effectiveness(classic, total_files)
                ),
            }

            # Dodaj do sumy
            results["total"]["classic_matches"] += classic
            results["total"]["ai_matches"] += ai
            results["total"]["files_without_preview"] += no_preview
            results["total"]["other_images"] += other
            results["total"]["folders_analyzed"] += 1

    # Oblicz ogólną skuteczność
    total_files = (
        results["total"]["classic_matches"] + results["total"]["files_without_preview"]
    )

    results["total"]["classic_effectiveness"] = calculate_effectiveness(
        results["total"]["classic_matches"], total_files
    )
    results["total"]["ai_effectiveness"] = calculate_effectiveness(
        results["total"]["ai_matches"], total_files
    )
    results["total"]["improvement_percent"] = (
        results["total"]["ai_effectiveness"] - results["total"]["classic_effectiveness"]
    )

    return results


def print_results(results: Dict):
    """Wyświetla wyniki analizy"""
    print("\n=== WYNIKI ANALIZY DOPASOWAŃ ===")
    print(f"Data analizy: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n--- STATYSTYKI OGÓLNE ---")
    print(f"Przeanalizowano folderów: {results['total']['folders_analyzed']}")
    print(
        f"Łączna liczba dopasowań zwykłym algorytmem: "
        f"{results['total']['classic_matches']}"
    )
    print(f"Łączna liczba dopasowań AI: {results['total']['ai_matches']}")
    print(
        f"Łączna liczba plików bez podglądu: "
        f"{results['total']['files_without_preview']}"
    )
    print(f"Łączna liczba obrazów bez pary: {results['total']['other_images']}")

    # Oblicz różnicę między AI a zwykłym algorytmem
    diff = results["total"]["ai_matches"] - results["total"]["classic_matches"]
    print(f"\nRóżnica (AI - zwykły): {diff:+d}")

    # Wyświetl skuteczność
    print("\n--- SKUTECZNOŚĆ OGÓLNA ---")
    print(
        f"Skuteczność zwykłego algorytmu: "
        f"{results['total']['classic_effectiveness']:.1f}%"
    )
    print(f"Skuteczność AI: {results['total']['ai_effectiveness']:.1f}%")
    print(f"Poprawa skuteczności: {results['total']['improvement_percent']:+.1f}%")

    # Filtruj foldery z różnicami
    folders_with_differences = {
        folder: stats 
        for folder, stats in results["folders"].items()
        if stats["ai_matches"] != stats["classic_matches"]
    }

    if folders_with_differences:
        print("\n--- STATYSTYKI PER FOLDER (tylko z różnicami) ---")
        for folder, stats in sorted(folders_with_differences.items()):
            print(f"\nFolder: {folder}")
            print(f"  Dopasowania zwykłe: {stats['classic_matches']}")
            print(f"  Dopasowania AI: {stats['ai_matches']}")
            print(f"  Pliki bez podglądu: {stats['files_without_preview']}")
            print(f"  Obrazy bez pary: {stats['other_images']}")

            # Różnica dla tego folderu
            folder_diff = stats["ai_matches"] - stats["classic_matches"]
            print(f"  Różnica (AI - zwykły): {folder_diff:+d}")

            # Skuteczność dla tego folderu
            print(
                f"  Skuteczność zwykłego algorytmu: "
                f"{stats['classic_effectiveness']:.1f}%"
            )
            print(f"  Skuteczność AI: {stats['ai_effectiveness']:.1f}%")
            print(f"  Poprawa skuteczności: {stats['improvement_percent']:+.1f}%")
    else:
        print("\nNie znaleziono folderów z różnicami w dopasowaniach.")


def main():
    """Funkcja główna"""
    print("=== ANALIZA DOPASOWAŃ ARCHIWUM-PODGLĄD ===")

    # Pobierz konfigurację
    config = load_config()
    if not config:
        print("Nie można załadować konfiguracji!")
        return

    work_dir = config.get("work_directory")
    if not work_dir:
        print("Nie znaleziono ścieżki do folderu roboczego w konfiguracji!")
        return

    if not os.path.exists(work_dir):
        print(f"Folder nie istnieje: {work_dir}")
        return

    if not os.path.isdir(work_dir):
        print(f"Podana ścieżka nie jest folderem: {work_dir}")
        return

    print(f"\nAnalizuję folder: {work_dir}")
    results = analyze_work_directory(work_dir)

    # Wyświetl wyniki
    print_results(results)

    # Zapisz wyniki do pliku
    output_file = os.path.join(work_dir, "matches_analysis.json")
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=4, ensure_ascii=False)
        print(f"\nWyniki zapisano do: {output_file}")
    except Exception as e:
        print(f"\nBłąd zapisu wyników: {e}")


if __name__ == "__main__":
    main()
