#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Composite Laminate Optimizer - Main Entry Point

A professional desktop GUI application for composite laminate layup
optimization using Genetic Algorithms.

This application provides:
- Excel-like layup editor for defining ply properties
- Genetic Algorithm optimization with configurable parameters
- Real-time fitness plotting during optimization
- Thread-safe execution with responsive UI

Usage:
    python main.py

Requirements:
    - Python 3.10+
    - PySide6
    - pyqtgraph
    - pandas
    - numpy
    - openpyxl

Composite Engineering Note:
    This tool implements Classical Laminate Theory (CLT) for computing
    laminate stiffness matrices and uses a binary-coded Genetic Algorithm
    to optimize fiber orientations for achieving target strain objectives.
"""

import sys
import os

# Ensure the package directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """
    Main entry point for the Laminate Optimizer application.
    
    Initializes the Qt application with dark theme and launches
    the main window.
    """
    # Import Qt modules
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    
    # Import application modules
    from ui.main_window import MainWindow
    from ui.styles import apply_dark_theme
    
    # Create the application
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Composite Laminate Optimizer")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Composite Engineering")
    
    # Set default font
    font = QFont("Segoe UI", 11)
    app.setFont(font)
    
    # Apply dark theme
    apply_dark_theme(app)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Run the application event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
