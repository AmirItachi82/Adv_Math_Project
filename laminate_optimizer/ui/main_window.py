# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Main Window

This module provides the main application window which contains
the tab-based navigation between the optimization page and the
layup editor page.

The window is fixed at 1280x1024 to ensure consistent layout
across different displays.
"""

import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QMessageBox, QMenuBar, QMenu, QFileDialog
)
from PySide6.QtGui import QAction, QIcon, QFont

# Support both package import and direct script execution
try:
    from .run_page import RunPage
    from .layup_editor import LayupEditor
    from ..models.laminate_model import LaminateModel
    from ..demo_data import create_demo_layup_data
except ImportError:
    from ui.run_page import RunPage
    from ui.layup_editor import LayupEditor
    from models.laminate_model import LaminateModel
    from demo_data import create_demo_layup_data


class MainWindow(QMainWindow):
    """
    Main application window for the Laminate Optimizer.
    
    This window provides:
    - Tab-based navigation between pages
    - Menu bar for file operations
    - Status bar for application state
    - Fixed 1024x800 resolution
    
    Pages:
    1. Optimization & Monitoring - GA settings and live results
    2. Layup Editor - Excel-like ply data editing
    """
    
    WINDOW_WIDTH = 1024
    WINDOW_HEIGHT = 800
    
    def __init__(self):
        super().__init__()
        self._model = LaminateModel()
        self._setup_window()
        self._setup_menu()
        self._setup_ui()
        self._setup_status_bar()
        self._connect_signals()
        self._load_demo_data()
    
    def _setup_window(self):
        """Configure the main window properties."""
        self.setWindowTitle("Composite Laminate Optimizer - Genetic Algorithm")
        self.setFixedSize(self.WINDOW_WIDTH, self.WINDOW_HEIGHT)
        
        # Center the window on screen
        screen = self.screen().geometry()
        x = (screen.width() - self.WINDOW_WIDTH) // 2
        y = (screen.height() - self.WINDOW_HEIGHT) // 2
        self.move(x, y)
    
    def _setup_menu(self):
        """Set up the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New action
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._on_new_project)
        file_menu.addAction(new_action)
        
        # Open action
        open_action = QAction("&Open Excel...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._on_open_file)
        file_menu.addAction(open_action)
        
        file_menu.addSeparator()
        
        # Save action
        save_action = QAction("&Save Excel...", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        # Load demo data
        demo_action = QAction("Load &Demo Data", self)
        demo_action.triggered.connect(self._load_demo_data)
        file_menu.addAction(demo_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)
        
        ga_info_action = QAction("&GA Information", self)
        ga_info_action.triggered.connect(self._on_ga_info)
        help_menu.addAction(ga_info_action)
    
    def _setup_ui(self):
        """Set up the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Tab widget for page navigation
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        
        # Set tab font
        tab_font = QFont()
        tab_font.setPointSize(12)
        self._tabs.setFont(tab_font)
        
        # Page 1: Optimization & Monitoring
        self._run_page = RunPage()
        self._tabs.addTab(self._run_page, "🎯 Optimization && Monitoring")
        
        # Page 2: Layup Editor
        self._layup_editor = LayupEditor()
        self._tabs.addTab(self._layup_editor, "📋 Layup Editor")
        
        layout.addWidget(self._tabs)
    
    def _setup_status_bar(self):
        """Set up the status bar."""
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("Ready - Load or create a laminate layup to begin")
    
    def _connect_signals(self):
        """Connect signals between components."""
        # Connect layup changes to run page
        self._layup_editor.layup_changed.connect(self._on_layup_changed)
        
        # Connect optimization events
        self._run_page.optimization_started.connect(self._on_optimization_started)
        self._run_page.optimization_finished.connect(self._on_optimization_finished)
    
    def _load_demo_data(self):
        """Load demonstration data."""
        df = create_demo_layup_data()
        self._model.dataframe = df
        self._layup_editor.set_dataframe(df)
        self._run_page.set_model(self._model)
        self._run_page.set_layup_data(df)
        self._status_bar.showMessage("Demo data loaded - 8-ply symmetric quasi-isotropic layup")
    
    @Slot(pd.DataFrame)
    def _on_layup_changed(self, df: pd.DataFrame):
        """Handle layup data changes."""
        self._model.dataframe = df
        self._run_page.set_model(self._model)
        self._run_page.set_layup_data(df)
        self._status_bar.showMessage(
            f"Layup updated: {len(df)} plies, {df['thickness'].sum()*1000:.3f} mm total"
        )
    
    @Slot()
    def _on_optimization_started(self):
        """Handle optimization start."""
        self._status_bar.showMessage("Optimization running...")
        # Switch to run page
        self._tabs.setCurrentIndex(0)
    
    @Slot(object)
    def _on_optimization_finished(self, result):
        """Handle optimization completion."""
        if result.success:
            self._status_bar.showMessage(
                f"Optimization complete! Best fitness: {result.best_fitness:.6e}"
            )
        else:
            self._status_bar.showMessage(f"Optimization ended: {result.message}")
    
    @Slot()
    def _on_new_project(self):
        """Create a new empty project."""
        reply = QMessageBox.question(
            self, "New Project",
            "Create a new project? This will clear the current layup data.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self._model = LaminateModel()
            self._layup_editor.set_dataframe(pd.DataFrame())
            self._run_page.set_model(self._model)
            self._status_bar.showMessage("New project created - Add plies in the Layup Editor")
    
    @Slot()
    def _on_open_file(self):
        """Open an Excel file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Layup File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        
        if filename:
            try:
                df = pd.read_excel(filename)
                self._model.dataframe = df
                self._layup_editor.set_dataframe(df)
                self._run_page.set_model(self._model)
                self._run_page.set_layup_data(df)
                self._status_bar.showMessage(f"Loaded: {filename}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to load file:\n{str(e)}"
                )
    
    @Slot()
    def _on_save_file(self):
        """Save to an Excel file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Layup File", "laminate_layup.xlsx",
            "Excel Files (*.xlsx);;All Files (*)"
        )
        
        if filename:
            try:
                df = self._layup_editor.get_dataframe()
                df.to_excel(filename, index=False)
                self._status_bar.showMessage(f"Saved: {filename}")
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to save file:\n{str(e)}"
                )
    
    @Slot()
    def _on_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About Laminate Optimizer",
            """<h2>Composite Laminate Optimizer</h2>
            <p>Version 1.0.0</p>
            <p>A professional desktop application for optimizing composite 
            laminate layup sequences using Genetic Algorithms.</p>
            <h3>Features:</h3>
            <ul>
                <li>Binary-coded Genetic Algorithm optimization</li>
                <li>Symmetric laminate enforcement</li>
                <li>Real-time fitness plotting</li>
                <li>Excel-like layup editor</li>
                <li>Classical Laminate Theory (CLT) analysis</li>
            </ul>
            <p><b>Composite Engineering Note:</b><br>
            This tool uses CLT to compute laminate stiffness matrices
            and optimize fiber orientations to achieve target strains
            under specified loading conditions.</p>
            """
        )
    
    @Slot()
    def _on_ga_info(self):
        """Show GA information dialog."""
        try:
            from ..ga_adapter import GAAdapter
        except ImportError:
            from ga_adapter import GAAdapter
        adapter = GAAdapter()
        info = adapter.get_ga_info()
        
        features = '\n'.join([f"• {f}" for f in info['supported_features']])
        
        QMessageBox.information(
            self, "Genetic Algorithm Information",
            f"""<h3>GA Implementation</h3>
            <p><b>Type:</b> {info['ga_type']}</p>
            <p><b>Description:</b> {info['description']}</p>
            <h4>Supported Features:</h4>
            <pre>{features}</pre>
            <h4>Composite Engineering Note:</h4>
            <p>The GA optimizes fiber orientation angles using a binary
            encoding with discrete angle choices (0°, ±45°, 90°). 
            For symmetric laminates, only half the plies are optimized
            and mirrored about the midplane.</p>
            """
        )
    
    def closeEvent(self, event):
        """Handle window close event."""
        reply = QMessageBox.question(
            self, "Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
