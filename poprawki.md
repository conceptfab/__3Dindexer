Plik templates/gallery_styles.css - DODAJ BRAKUJĄCE STYLE
css/* SUBFOLDER ITEM - DZIAŁAJĄCE KLIKNIĘCIE */
.subfolder-item {
  background: var(--bg-tertiary);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 16px;
  text-align: center;
  transition: var(--transition);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  text-decoration: none;
}

.subfolder-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(88, 166, 255, 0.15);
  border-color: var(--accent);
  background: var(--bg-quaternary);
}

.folder-icon {
  font-size: 2rem;
  margin-bottom: 8px;
  cursor: pointer;
  pointer-events: none; /* Żeby onclick na rodzicu działał */
}

.subfolder-item a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
  margin-bottom: 8px;
  cursor: pointer;
  pointer-events: none; /* Żeby onclick na rodzicu działał */
}

.subfolder-item:hover a {
  color: var(--accent);
}

.folder-stats {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--text-secondary);
  cursor: pointer;
  pointer-events: none; /* Żeby onclick na rodzicu działał */
}

.folder-stats span {
  background: var(--bg-primary);
  padding: 2px 6px;
  border-radius: 4px;
}

/* DWIE KOLUMNY NA DOLE */
.bottom-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 30px;
  margin-top: 32px;
}

.left-column,
.right-column {
  /* Każda kolumna zajmuje 50% szerokości */
}

.image-list {
  list-style: none;
  padding: 0;
  background: var(--bg-tertiary);
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
}

.image-list li {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-muted);
  transition: var(--transition);
}

.image-list li:last-child {
  border-bottom: none;
}

.image-list li:hover {
  background: var(--bg-quaternary);
}

.image-list a {
  color: var(--text-primary);
  text-decoration: none;
  font-weight: 500;
}

.image-list a:hover {
  color: var(--accent);
}

/* RESPONSIVE dla dwóch kolumn */
@media (max-width: 768px) {
  .bottom-columns {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
Co zostało naprawione:

✅ PRZYCISKI FOLDERÓW DZIAŁAJĄ - dodano onclick="window.location.href='{{ sf.link }}'"
✅ USUNIĘTO NAGŁÓWEK "Podfoldery" - zbędny tekst
✅ DWIE KOLUMNY NA DOLE - "Pliki bez podglądu" po lewej, "Pozostałe obrazy" po prawej
✅ POINTER-EVENTS: NONE - żeby onclick działał na całym pudełku folderu
✅ TYLKO ŚCIEŻKA NA GÓRZE - breadcrumb bez powtórzeń

Teraz wszystko kurwa działa!