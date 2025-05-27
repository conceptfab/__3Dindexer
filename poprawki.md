Zmiany w pliku main.py
python# main.py - ZMODYFIKOWANE CZĘŚCI

# Dodaj import na górze pliku
import qdarktheme  # Nowy import

# W funkcji main (na końcu pliku) - ZMIEŃ SEKCJĘ INICJALIZACJI
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # ZASTOSUJ CIEMNY MOTYW - DODAJ TO
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    # Opcjonalnie: konfiguracja dla lepszego wyglądu
    app.setStyle('Fusion')  # Lepszy styl bazowy
    
    # Reszta kodu pozostaje bez zmian...
    script_dir = os.path.dirname(os.path.abspath(__file__))
    templates_path = os.path.join(script_dir, "templates")
    
    # ... reszta istniejącego kodu
    
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec())
Ulepszenia stylistyczne w main.py
pythonclass MainWindow(QMainWindow):
    def init_ui(self):
        # ZMIEŃ STYLE PRZYCISKÓW - lepiej wyglądają z qdarktheme
        
        # Zamiast kolorowych przycisków, użyj bardziej subtelnych stylów
        self.select_folder_button = QPushButton("📁 Wybierz Folder")
        # USUŃ lub zmień stary styl:
        # self.select_folder_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        # DODAJ nowy, subtelny styl:
        self.select_folder_button.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #2d5aa0;
            }
        """)
        
        # Podobnie dla innych przycisków - usuń stare style lub zmień na subtelniejsze
        self.start_scan_button = QPushButton("🔍 Skanuj Foldery")
        self.start_scan_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        self.rebuild_gallery_button = QPushButton("🔄 Przebuduj Galerię")
        self.rebuild_gallery_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        self.open_gallery_button = QPushButton("👁️ Pokaż Galerię")
        self.open_gallery_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        self.clear_gallery_cache_button = QPushButton("🗑️ Wyczyść Cache")
        self.clear_gallery_cache_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #c62d42;
            }
        """)
        
        self.cancel_button = QPushButton("❌ Anuluj")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
        """)
        
        # ULEPSZONY panel statystyk - dostosowany do qdarktheme
        self.stats_panel.setStyleSheet("""
            QWidget { 
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 8px;
            }
            QLabel {
                color: #ffffff;
                padding: 4px;
                background: transparent;
            }
        """)
        
        self.stats_title.setStyleSheet("""
            font-weight: bold; 
            font-size: 14px; 
            color: #3daee9;
            background: transparent;
        """)
Dodaj do requirements.txt lub zainstaluj
bashpip install pyqtdarktheme
Opcjonalne: Konfiguracja motywów
python# W main.py - dodaj funkcję przełączania motywów (opcjonalne)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # ... istniejący kod ...
        
        # Dodaj do menu opcję przełączania motywów
        self.setup_theme_menu()
    
    def setup_theme_menu(self):
        """Dodaje menu przełączania motywów."""
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("Motyw")
        
        dark_action = theme_menu.addAction("Ciemny")
        light_action = theme_menu.addAction("Jasny")
        auto_action = theme_menu.addAction("Automatyczny")
        
        dark_action.triggered.connect(lambda: self.change_theme("dark"))
        light_action.triggered.connect(lambda: self.change_theme("light"))
        auto_action.triggered.connect(lambda: self.change_theme("auto"))
    
    def change_theme(self, theme):
        """Zmienia motyw aplikacji."""
        QApplication.instance().setStyleSheet(qdarktheme.load_stylesheet(theme))
        # Zapisz wybór do konfiguracji
        config_manager.set_config_value("ui.theme", theme)
Aktualizacja config.json
json{
    "work_directory": "W:\\3Dsky\\ARCHITECTURE",
    "preview_size": 400,
    "thumbnail_size": 150,
    "dark_theme": true,
    "performance": {
        "max_worker_threads": 4,
        "cache_previews": true,
        "lazy_loading": true,
        "max_cache_size_mb": 1024,
        "cache_ttl_hours": 24
    },
    "ui": {
        "animation_speed": 300,
        "hover_delay": 500,
        "max_preview_size": 1200,
        "theme": "dark"
    },
    "security": {
        "allowed_extensions": [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".webp"
        ],
        "max_file_size_mb": 50
    }
}
Zminimalizowany progress bar styling
python# W init_ui(), dla progress bara
self.progress_bar = QProgressBar()
self.progress_bar.setVisible(False)
self.progress_bar.setStyleSheet("""
    QProgressBar {
        border-radius: 4px;
        text-align: center;
        height: 20px;
    }
    QProgressBar::chunk {
        border-radius: 4px;
        background-color: #3daee9;
    }
""")
Korzyści z pyqtdarktheme:
✅ Profesjonalny wygląd - aplikacja wygląda nowocześnie
✅ Konsystentność - wszystkie elementy Qt mają spójny styl
✅ Mniej custom CSS - nie musisz stylować każdego elementu
✅ Automatic detection - może automatycznie wykrywać motyw systemu
✅ Cross-platform - działa identycznie na Windows/Linux/macOS
Rezultat:
Twoja aplikacja będzie miała:

Profesjonalny ciemny motyw
Lepiej wyglądające przyciski i kontrolki
Spójne kolory w całej aplikacji
Zachowaną funkcjonalność HTML/CSS galerii
Możliwość przełączania motywów

Motyw będzie idealnie komponować się z Twoim ciemnym motywem galerii HTML! 🎨