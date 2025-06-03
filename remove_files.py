import sys
import os
import shutil
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QFileDialog, QTextEdit, QMessageBox
)
from PyQt6.QtCore import Qt

class FolderProcessorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Przetwarzanie Folderów")
        self.setGeometry(100, 100, 600, 400)

        self.working_directory = None

        # Centralny widget i layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Sekcja wyboru folderu
        dir_selection_layout = QHBoxLayout()
        self.dir_label = QLineEdit()
        self.dir_label.setPlaceholderText("Nie wybrano folderu roboczego")
        self.dir_label.setReadOnly(True)
        self.select_dir_button = QPushButton("Wybierz folder roboczy")
        self.select_dir_button.clicked.connect(self.select_working_directory)
        dir_selection_layout.addWidget(self.dir_label)
        dir_selection_layout.addWidget(self.select_dir_button)
        main_layout.addLayout(dir_selection_layout)

        # Przycisk przetwarzania
        self.process_button = QPushButton("Przetwórz foldery")
        self.process_button.clicked.connect(self.process_folders_action)
        self.process_button.setEnabled(False) # Domyślnie wyłączony
        main_layout.addWidget(self.process_button)

        # Logi
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        main_layout.addWidget(self.log_area)

    def _log(self, message):
        """Dodaje wiadomość do pola logów."""
        self.log_area.append(message)
        QApplication.processEvents() # Aby UI pozostało responsywne

    def select_working_directory(self):
        """Otwiera dialog wyboru folderu."""
        directory = QFileDialog.getExistingDirectory(self, "Wybierz folder roboczy")
        if directory:
            self.working_directory = directory
            self.dir_label.setText(self.working_directory)
            self.process_button.setEnabled(True)
            self._log(f"Wybrano folder roboczy: {self.working_directory}")
        else:
            self.process_button.setEnabled(False)
            self._log("Nie wybrano folderu roboczego.")


    def process_folders_action(self):
        """Obsługuje kliknięcie przycisku przetwarzania."""
        if not self.working_directory or not os.path.isdir(self.working_directory):
            QMessageBox.warning(self, "Błąd", "Nie wybrano prawidłowego folderu roboczego.")
            self._log("Błąd: Brak prawidłowego folderu roboczego.")
            return

        self.log_area.clear()
        self._log(f"Rozpoczynam przetwarzanie folderu: {self.working_directory}")
        self.process_button.setEnabled(False) # Zablokuj przycisk podczas przetwarzania

        try:
            subfolders_processed_count = 0
            files_moved_count = 0
            folders_deleted_count = 0

            # Przechodzimy przez elementy w folderze roboczym
            for item_name in os.listdir(self.working_directory):
                item_path = os.path.join(self.working_directory, item_name)

                # Interesują nas tylko podfoldery
                if os.path.isdir(item_path):
                    self._log(f"\nPrzetwarzanie podfolderu: {item_name}")
                    subfolders_processed_count += 1
                    files_in_subfolder = os.listdir(item_path)

                    if not files_in_subfolder:
                        self._log(f"Podfolder '{item_name}' jest pusty.")
                    else:
                        for file_name in files_in_subfolder:
                            source_file_path = os.path.join(item_path, file_name)
                            destination_file_path = os.path.join(self.working_directory, file_name)

                            # Upewniamy się, że to plik, a nie kolejny podfolder w podfolderze
                            if os.path.isfile(source_file_path):
                                try:
                                    self._log(f"  Przenoszenie pliku: {file_name} z '{item_name}' do folderu roboczego.")
                                    # shutil.move automatycznie nadpisuje, jeśli plik docelowy istnieje
                                    shutil.move(source_file_path, destination_file_path)
                                    files_moved_count += 1
                                    self._log(f"  Przeniesiono: {file_name}")
                                except Exception as e:
                                    self._log(f"  BŁĄD podczas przenoszenia {file_name}: {e}")
                            else:
                                self._log(f"  '{file_name}' w '{item_name}' nie jest plikiem, pomijanie.")


                    # Po przeniesieniu plików, sprawdź czy folder jest pusty i usuń
                    if not os.listdir(item_path): # Sprawdza czy lista plików/folderów jest pusta
                        try:
                            os.rmdir(item_path)
                            folders_deleted_count += 1
                            self._log(f"Usunięto pusty podfolder: {item_name}")
                        except OSError as e:
                            self._log(f"BŁĄD: Nie można usunąć folderu '{item_name}': {e}. Może zawiera ukryte pliki lub nie jest pusty.")
                    else:
                        self._log(f"Podfolder '{item_name}' nie jest pusty po próbie przeniesienia plików, nie został usunięty.")
                        self._log(f"  Zawartość '{item_name}': {os.listdir(item_path)}")


            summary = (
                f"\n--- Podsumowanie ---\n"
                f"Przetworzono podfolderów: {subfolders_processed_count}\n"
                f"Przeniesiono plików: {files_moved_count}\n"
                f"Usunięto pustych folderów: {folders_deleted_count}\n"
                f"Zakończono przetwarzanie."
            )
            self._log(summary)
            QMessageBox.information(self, "Zakończono", "Przetwarzanie folderów zakończone. Sprawdź logi po szczegóły.")

        except Exception as e:
            self._log(f"Wystąpił krytyczny błąd podczas przetwarzania: {e}")
            QMessageBox.critical(self, "Błąd krytyczny", f"Wystąpił błąd: {e}")
        finally:
            self.process_button.setEnabled(True) # Odblokuj przycisk


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FolderProcessorApp()
    window.show()
    sys.exit(app.exec())