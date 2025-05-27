<!DOCTYPE html>
└── <html>
    ├── <head>
    │   ├── meta charset
    │   ├── meta viewport
    │   ├── title
    │   └── link (gallery_styles.css)
    │
    └── <body>
        ├── <div class="container">
        │   ├── breadcrumb (nawigacja)
        │   │   └── ścieżka folderów
        │   │
        │   ├── sekcja subfolders (jeśli istnieją)
        │   │   └── subfolders-grid
        │   │       └── subfolder-item
        │   │           ├── folder-icon
        │   │           ├── link
        │   │           └── folder-stats
        │   │
        │   ├── sekcja files_with_previews (jeśli istnieją)
        │   │   ├── nagłówek
        │   │   └── gallery
        │   │       └── gallery-item
        │   │           ├── preview-image
        │   │           ├── link
        │   │           └── file-info
        │   │
        │   ├── sekcja other_images (jeśli istnieją) -> sekcja do usunięcia
        │   │   ├── nagłówek
        │   │   └── gallery
        │   │       └── gallery-item
        │   │           ├── preview-image
        │   │           ├── link
        │   │           └── file-info
        │   │
        │   └── bottom-columns (jeśli istnieją)
        │       ├── left-column (files_without_previews)
        │       │   ├── nagłówek
        │       │   └── no-preview-list
        │       │
        │       └── right-column (other_images) -> po najechaniu na nazwę pliku/link - ma się pojawić podgląd pliku jak w wyżej
        │           ├── nagłówek
        │           └── image-list
        │
        ├── preview-backdrop (modal)
        ├── preview-modal
        │   └── previewImg
        │
        └── <script>
            └── obsługa podglądu obrazów
                ├── showPreview()
                ├── hidePreview()
                └── event listeners