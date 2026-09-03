"""Core application shell (Blueprint v2, Phases 1-2)."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
)

from app.persistence import markups_db
from app.persistence.recent_files import add_recent_file
from app.ui.canvas.document_view import DocumentView
from app.ui.dashboard.home_dashboard import HomeDashboard
from app.ui.panels.markups_list_panel import MarkupsListPanel
from app.ui.theme.manager import ThemeManager


class MainWindow(QMainWindow):
    def __init__(self, theme_manager: ThemeManager) -> None:
        super().__init__()
        self._theme_manager = theme_manager
        self.setWindowTitle("PDF Pro")
        self.resize(1280, 800)

        self._stack = QStackedWidget()
        self.setCentralWidget(self._stack)

        self._dashboard = HomeDashboard()
        self._dashboard.browse_requested.connect(self._browse_for_file)
        self._dashboard.open_file_requested.connect(self.open_document)
        self._dashboard.new_file_requested.connect(self._browse_for_file)
        self._stack.addWidget(self._dashboard)

        self._document_view = DocumentView()
        self._document_view.undo_state_changed.connect(self._on_undo_state_changed)
        self._document_view.markups_changed.connect(self._refresh_markups_list)
        self._document_view.external_change_detected.connect(self._on_external_change_detected)
        self._stack.addWidget(self._document_view)

        self._current_path: str | None = None

        self._build_menu()
        self._build_markups_dock()

    @property
    def document_view(self) -> DocumentView:
        return self._document_view

    # -- menu -----------------------------------------------------------
    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("&File")
        open_action = QAction("&Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._browse_for_file)
        file_menu.addAction(open_action)

        home_action = QAction("&Home Dashboard", self)
        home_action.triggered.connect(self.show_dashboard)
        file_menu.addAction(home_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As…", self)
        save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        save_as_action.triggered.connect(self._save_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        edit_menu = menu.addMenu("&Edit")
        self._undo_action = QAction("&Undo", self)
        self._undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self._document_view.command_stack.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("&Redo", self)
        self._redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self._document_view.command_stack.redo)
        edit_menu.addAction(self._redo_action)

        view_menu = menu.addMenu("&View")
        toggle_theme_action = QAction("Toggle &Dark Mode", self)
        toggle_theme_action.setShortcut("Ctrl+Shift+D")
        toggle_theme_action.triggered.connect(self._theme_manager.toggle)
        view_menu.addAction(toggle_theme_action)

        palette_action = QAction("Command &Palette…", self)
        palette_action.setShortcut("Ctrl+K")
        palette_action.triggered.connect(self._document_view.open_command_palette)
        view_menu.addAction(palette_action)

        pages_menu = menu.addMenu("&Pages")
        self._add_pages_action(pages_menu, "Insert Blank Page", self._insert_page)
        self._add_pages_action(pages_menu, "Delete Current Page", self._delete_page)
        self._add_pages_action(pages_menu, "Rotate Left", lambda: self._document_view.rotate_current_page(-90))
        self._add_pages_action(pages_menu, "Rotate Right", lambda: self._document_view.rotate_current_page(90))
        self._add_pages_action(pages_menu, "Move Page…", self._move_page)
        pages_menu.addSeparator()
        self._add_pages_action(pages_menu, "Extract Pages…", self._extract_pages)
        self._add_pages_action(pages_menu, "Merge PDFs…", self._merge_pdfs)
        self._add_pages_action(pages_menu, "Split PDF…", self._split_pdf)
        pages_menu.addSeparator()
        self._add_pages_action(pages_menu, "Add Watermark…", self._add_watermark)
        self._add_pages_action(pages_menu, "Add Bates Numbering…", self._add_bates)
        self._add_pages_action(pages_menu, "Add Header/Footer…", self._add_header_footer)
        self._add_pages_action(pages_menu, "Edit Bookmarks (TOC)…", self._edit_toc)

    def _add_pages_action(self, menu, label: str, handler) -> None:
        action = QAction(label, self)
        action.triggered.connect(handler)
        menu.addAction(action)

    def _build_markups_dock(self) -> None:
        self._markups_panel = MarkupsListPanel(self._document_view.select_object)
        dock = QDockWidget("Markups List", self)
        dock.setWidget(self._markups_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)
        self._markups_dock = dock

    def _refresh_markups_list(self) -> None:
        if self._document_view.pdf.path:
            rows = markups_db.list_markups(self._document_view.pdf.path)
            self._markups_panel.set_rows(rows)

    def _on_external_change_detected(self, path: str) -> None:
        answer = QMessageBox.question(
            self,
            "File changed on disk",
            f"{path}\n\nThis file changed outside PDF Pro. Reload it? Unsaved markup edits are kept "
            "separately in the autosave journal and won't be lost, but any unsaved page/document "
            "structure changes (page insert/delete/rotate, watermark, etc.) will be.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.open_document(path)

    # -- page management ----------------------------------------------------
    def _insert_page(self) -> None:
        self._document_view.insert_page(self._document_view.current_page)

    def _delete_page(self) -> None:
        confirm = QMessageBox.question(self, "Delete Page", "Delete the current page? This also removes its markups.")
        if confirm == QMessageBox.StandardButton.Yes:
            self._document_view.delete_current_page()

    def _move_page(self) -> None:
        dv = self._document_view
        target, ok = QInputDialog.getInt(
            self, "Move Page", "Move current page to position:", dv.current_page + 1, 1, dv.pdf.page_count
        )
        if ok:
            dv.move_page(dv.current_page, target - 1)

    def _extract_pages(self) -> None:
        dv = self._document_view
        text, ok = QInputDialog.getText(self, "Extract Pages", "Page numbers (e.g. 1,3,5-7):", text=str(dv.current_page + 1))
        if not ok or not text.strip():
            return
        indices = self._parse_page_ranges(text, dv.pdf.page_count)
        if not indices:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Extracted Pages", "", "PDF files (*.pdf)")
        if out_path:
            dv.pdf.extract_pages(indices, out_path)
            QMessageBox.information(self, "Extracted", f"Saved {len(indices)} page(s) to {out_path}")

    @staticmethod
    def _parse_page_ranges(text: str, page_count: int) -> list[int]:
        indices: list[int] = []
        for part in text.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                try:
                    indices.extend(range(int(start) - 1, int(end)))
                except ValueError:
                    continue
            else:
                try:
                    indices.append(int(part) - 1)
                except ValueError:
                    continue
        return [i for i in indices if 0 <= i < page_count]

    def _merge_pdfs(self) -> None:
        from app.core.pdf_document import merge_pdfs

        paths, _ = QFileDialog.getOpenFileNames(self, "Select PDFs to merge, in order", "", "PDF files (*.pdf)")
        if len(paths) < 2:
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "Save Merged PDF", "", "PDF files (*.pdf)")
        if out_path:
            merge_pdfs(paths, out_path)
            QMessageBox.information(self, "Merged", f"Saved merged PDF to {out_path}")

    def _split_pdf(self) -> None:
        from app.core.pdf_document import split_pdf

        if not self._current_path:
            return
        pages_per_file, ok = QInputDialog.getInt(self, "Split PDF", "Pages per file:", 1, 1, 1000)
        if not ok:
            return
        out_dir = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if out_dir:
            outputs = split_pdf(self._current_path, out_dir, pages_per_file)
            QMessageBox.information(self, "Split", f"Created {len(outputs)} file(s) in {out_dir}")

    def _add_watermark(self) -> None:
        text, ok = QInputDialog.getText(self, "Add Watermark", "Watermark text:")
        if ok and text.strip():
            self._document_view.apply_watermark(text.strip())

    def _add_bates(self) -> None:
        prefix, ok = QInputDialog.getText(self, "Add Bates Numbering", "Prefix (e.g. ABC-):")
        if not ok:
            return
        start, ok = QInputDialog.getInt(self, "Add Bates Numbering", "Starting number:", 1, 1)
        if ok:
            self._document_view.apply_bates_numbers(prefix, start)

    def _add_header_footer(self) -> None:
        header, ok = QInputDialog.getText(self, "Add Header/Footer", "Header text:")
        if not ok:
            return
        footer, ok = QInputDialog.getText(self, "Add Header/Footer", "Footer text:")
        if ok:
            self._document_view.apply_header_footer(header, footer)

    def _edit_toc(self) -> None:
        from app.ui.panels.toc_editor_dialog import TocEditorDialog

        dv = self._document_view
        dialog = TocEditorDialog(dv.pdf.get_toc(), dv.pdf.page_count, self)
        if dialog.exec():
            dv.pdf.set_toc(dialog.result_toc())

    def _on_undo_state_changed(self, can_undo: bool, can_redo: bool) -> None:
        self._undo_action.setEnabled(can_undo)
        self._redo_action.setEnabled(can_redo)

    # -- navigation -------------------------------------------------------
    def show_dashboard(self) -> None:
        self._dashboard.refresh_recent_files()
        self._stack.setCurrentWidget(self._dashboard)

    def _browse_for_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open PDF", "", "PDF files (*.pdf)")
        if path:
            self.open_document(path)

    def open_document(self, path: str) -> None:
        try:
            has_journal = self._document_view.load(path)
        except Exception as exc:  # surfaced to the user, not swallowed
            QMessageBox.critical(self, "Could not open file", str(exc))
            return
        add_recent_file(path)
        self._current_path = path
        self._stack.setCurrentWidget(self._document_view)

        if has_journal:
            answer = QMessageBox.question(
                self,
                "Recover unsaved work?",
                "PDF Pro found unsaved changes from a previous session for this file. Recover them?",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._document_view.recover_from_journal()
            else:
                self._document_view.discard_journal()

    def _save(self) -> None:
        if not self._current_path:
            return
        self._export_to(self._current_path)

    def _save_as(self) -> None:
        if not self._current_path:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save PDF As", self._current_path, "PDF files (*.pdf)")
        if path:
            self._export_to(path)

    def _export_to(self, path: str) -> None:
        if path == self._document_view.pdf.path:
            self._document_view.notify_saving()
        try:
            self._document_view.pdf.export(path, self._document_view.markup_document.all_objects())
        except Exception as exc:
            QMessageBox.critical(self, "Could not save file", str(exc))
            return
        self._document_view.discard_journal()
        QMessageBox.information(self, "Saved", f"Saved to {path}")
