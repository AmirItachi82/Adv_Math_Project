# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Dark Theme Styles

This module provides the dark theme styling for the application,
including custom stylesheets and theme application functions.

The design follows modern UI principles with:
- Dark background colors for reduced eye strain
- High contrast text for readability
- Consistent spacing and padding
- Professional appearance suitable for engineering applications
"""

from typing import Optional

# Color palette for the dark theme
COLORS = {
    'background': '#1e1e1e',
    'background_alt': '#252526',
    'background_lighter': '#2d2d30',
    'surface': '#333333',
    'surface_hover': '#3e3e42',
    'primary': '#0078d4',
    'primary_hover': '#1084d8',
    'primary_pressed': '#006cbd',
    'secondary': '#6c757d',
    'success': '#28a745',
    'warning': '#ffc107',
    'danger': '#dc3545',
    'text': '#e0e0e0',
    'text_secondary': '#a0a0a0',
    'text_disabled': '#6c6c6c',
    'border': '#3f3f46',
    'border_focus': '#0078d4',
    'scrollbar': '#4a4a4a',
    'scrollbar_hover': '#5a5a5a',
    'table_header': '#2d2d30',
    'table_row_alt': '#292929',
    'plot_background': '#1e1e1e',
    'plot_grid': '#3f3f46',
}

# Font specifications
FONTS = {
    'family': 'Segoe UI, -apple-system, BlinkMacSystemFont, sans-serif',
    'monospace': 'Consolas, Monaco, "Courier New", monospace',
    'size_body': '12pt',
    'size_small': '10pt',
    'size_title': '16pt',
    'size_header': '18pt',
}

# Spacing values
SPACING = {
    'padding_small': '6px',
    'padding': '12px',
    'padding_large': '16px',
    'margin': '8px',
    'margin_large': '16px',
    'border_radius': '4px',
}

# Complete Qt Stylesheet
STYLESHEET = f"""
/* Global Application Styling */
QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['text']};
    font-family: {FONTS['family']};
    font-size: {FONTS['size_body']};
}}

/* Main Window */
QMainWindow {{
    background-color: {COLORS['background']};
}}

/* Tab Widget */
QTabWidget::pane {{
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    background-color: {COLORS['background']};
    padding: 4px;
}}

QTabBar::tab {{
    background-color: {COLORS['background_alt']};
    color: {COLORS['text_secondary']};
    border: 1px solid {COLORS['border']};
    border-bottom: none;
    border-top-left-radius: {SPACING['border_radius']};
    border-top-right-radius: {SPACING['border_radius']};
    padding: 10px 20px;
    margin-right: 2px;
    font-size: {FONTS['size_body']};
}}

QTabBar::tab:selected {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border-color: {COLORS['primary']};
}}

QTabBar::tab:hover:!selected {{
    background-color: {COLORS['surface_hover']};
}}

/* Group Boxes */
QGroupBox {{
    background-color: {COLORS['background_alt']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    margin-top: 16px;
    padding: {SPACING['padding']};
    font-size: {FONTS['size_body']};
    font-weight: bold;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 8px;
    color: {COLORS['text']};
    background-color: {COLORS['background_alt']};
}}

/* Labels */
QLabel {{
    color: {COLORS['text']};
    background-color: transparent;
    padding: 2px;
}}

QLabel#title {{
    font-size: {FONTS['size_title']};
    font-weight: bold;
    color: {COLORS['text']};
}}

QLabel#header {{
    font-size: {FONTS['size_header']};
    font-weight: bold;
    color: {COLORS['primary']};
}}

QLabel#subtitle {{
    font-size: {FONTS['size_body']};
    color: {COLORS['text_secondary']};
}}

/* Input Fields */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    padding: 8px 12px;
    selection-background-color: {COLORS['primary']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['border_focus']};
}}

QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {COLORS['background_lighter']};
    color: {COLORS['text_disabled']};
}}

/* Spin Box Buttons */
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background-color: {COLORS['surface_hover']};
    border: none;
    width: 20px;
}}

QSpinBox::up-button:hover, QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {{
    background-color: {COLORS['primary']};
}}

/* Combo Boxes */
QComboBox {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    padding: 8px 12px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_focus']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {COLORS['text']};
    margin-right: 8px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    selection-color: white;
}}

/* Check Boxes */
QCheckBox {{
    spacing: 8px;
    color: {COLORS['text']};
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['surface']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['border_focus']};
}}

/* Push Buttons */
QPushButton {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    padding: 10px 20px;
    font-weight: bold;
    min-width: 80px;
}}

QPushButton:hover {{
    background-color: {COLORS['surface_hover']};
    border-color: {COLORS['border_focus']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary_pressed']};
}}

QPushButton:disabled {{
    background-color: {COLORS['background_lighter']};
    color: {COLORS['text_disabled']};
    border-color: {COLORS['background_lighter']};
}}

QPushButton#primary {{
    background-color: {COLORS['primary']};
    color: white;
    border: none;
    font-size: 14pt;
    padding: 14px 32px;
}}

QPushButton#primary:hover {{
    background-color: {COLORS['primary_hover']};
}}

QPushButton#primary:pressed {{
    background-color: {COLORS['primary_pressed']};
}}

QPushButton#primary:disabled {{
    background-color: {COLORS['secondary']};
}}

QPushButton#danger {{
    background-color: {COLORS['danger']};
    color: white;
    border: none;
}}

QPushButton#danger:hover {{
    background-color: #c82333;
}}

QPushButton#success {{
    background-color: {COLORS['success']};
    color: white;
    border: none;
}}

QPushButton#success:hover {{
    background-color: #218838;
}}

/* Tables */
QTableView, QTableWidget {{
    background-color: {COLORS['background']};
    alternate-background-color: {COLORS['table_row_alt']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['primary']};
    selection-color: white;
}}

QTableView::item, QTableWidget::item {{
    padding: 8px;
}}

QTableView::item:hover, QTableWidget::item:hover {{
    background-color: {COLORS['surface_hover']};
}}

QHeaderView::section {{
    background-color: {COLORS['table_header']};
    color: {COLORS['text']};
    padding: 10px;
    border: none;
    border-bottom: 2px solid {COLORS['border']};
    border-right: 1px solid {COLORS['border']};
    font-weight: bold;
}}

QHeaderView::section:hover {{
    background-color: {COLORS['surface_hover']};
}}

/* Scroll Bars */
QScrollBar:vertical {{
    background-color: {COLORS['background']};
    width: 12px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['scrollbar']};
    border-radius: 6px;
    min-height: 30px;
    margin: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['background']};
    height: 12px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['scrollbar']};
    border-radius: 6px;
    min-width: 30px;
    margin: 2px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['scrollbar_hover']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* Progress Bar */
QProgressBar {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    text-align: center;
    color: {COLORS['text']};
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 2px;
}}

QSplitter::handle:vertical {{
    height: 2px;
}}

/* Tool Tips */
QToolTip {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: {SPACING['border_radius']};
    padding: 6px;
}}

/* Menu */
QMenu {{
    background-color: {COLORS['surface']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
}}

QMenu::item:selected {{
    background-color: {COLORS['primary']};
}}

/* Status Bar */
QStatusBar {{
    background-color: {COLORS['background_alt']};
    color: {COLORS['text_secondary']};
    border-top: 1px solid {COLORS['border']};
}}

QStatusBar::item {{
    border: none;
}}

/* Frame */
QFrame {{
    border: none;
}}

QFrame#separator {{
    background-color: {COLORS['border']};
    max-height: 1px;
}}
"""


def apply_dark_theme(app) -> None:
    """
    Apply the dark theme to the application.
    
    Args:
        app: QApplication instance to style.
    
    This function attempts to use qdarktheme if available,
    otherwise falls back to the built-in stylesheet.
    """
    try:
        import qdarktheme
        # Use qdarktheme with customizations
        qdarktheme.setup_theme(
            theme="dark",
            custom_colors={
                "[dark]": {
                    "primary": COLORS['primary'],
                    "background": COLORS['background'],
                }
            }
        )
        # Apply additional custom styles
        current_style = app.styleSheet()
        app.setStyleSheet(current_style + _get_additional_styles())
    except ImportError:
        # Fall back to built-in stylesheet
        app.setStyleSheet(STYLESHEET)


def _get_additional_styles() -> str:
    """Get additional custom styles to apply on top of qdarktheme."""
    return f"""
        QPushButton#primary {{
            background-color: {COLORS['primary']};
            color: white;
            border: none;
            font-size: 14pt;
            font-weight: bold;
            padding: 14px 32px;
            border-radius: 4px;
        }}
        
        QPushButton#primary:hover {{
            background-color: {COLORS['primary_hover']};
        }}
        
        QPushButton#primary:disabled {{
            background-color: {COLORS['secondary']};
        }}
        
        QPushButton#danger {{
            background-color: {COLORS['danger']};
            color: white;
            border: none;
        }}
        
        QLabel#header {{
            font-size: {FONTS['size_header']};
            font-weight: bold;
            color: {COLORS['primary']};
        }}
    """


def get_plot_style() -> dict:
    """
    Get style configuration for pyqtgraph plots.
    
    Returns:
        Dictionary with plot styling parameters.
    """
    return {
        'background': COLORS['plot_background'],
        'foreground': COLORS['text'],
        'grid_color': COLORS['plot_grid'],
        'axis_color': COLORS['text_secondary'],
        'best_fitness_color': COLORS['primary'],
        'avg_fitness_color': COLORS['success'],
        'font_size': 11,
    }
