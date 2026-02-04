# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Layup Editor Page

This module provides the Excel-like layup editor for modifying
the composite laminate ply data. Features include:
- Editable table with inline editing
- Add/remove row functionality
- Material property management
- Real-time constraint validation

Composite Engineering Note:
    The layup editor allows engineers to define the composite
    laminate structure including fiber orientations, thicknesses,
    and material properties for each ply.
"""

from typing import Optional, List, Any
import pandas as pd
import numpy as np

from PySide6.QtCore import Qt, Signal, QAbstractTableModel, QModelIndex, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QGroupBox, QLabel, QFormLayout, QHeaderView, QAbstractItemView,
    QComboBox, QDoubleSpinBox, QMessageBox, QFileDialog, QFrame, QSplitter
)
from PySide6.QtGui import QColor, QFont

# Support both package import and direct script execution
try:
    from ..models.laminate_model import LaminateModel
    from ..demo_data import get_material_database
except ImportError:
    from models.laminate_model import LaminateModel
    from demo_data import get_material_database


class LaminateTableModel(QAbstractTableModel):
    """
    Table model for the laminate ply data.
    
    This model wraps a pandas DataFrame and provides the interface
    needed by QTableView for display and editing.
    
    Composite Engineering Note:
        The model tracks changes to ply properties and can emit
        signals when data changes for real-time constraint updates.
    """
    
    data_changed = Signal()
    
    # Column definitions: (internal_name, display_name, editable, format_func)
    COLUMNS = [
        ('index', 'Ply #', False, lambda x: str(int(x))),
        ('material', 'Material', True, str),
        ('deg', 'Angle (°)', True, lambda x: f"{float(x):.1f}"),
        ('thickness', 'Thickness (m)', True, lambda x: f"{float(x):.6f}"),
        ('e_x', 'E₁ (Pa)', True, lambda x: f"{float(x):.2e}"),
        ('e_y', 'E₂ (Pa)', True, lambda x: f"{float(x):.2e}"),
        ('e_s', 'G₁₂ (Pa)', True, lambda x: f"{float(x):.2e}"),
        ('v_x', 'ν₁₂', True, lambda x: f"{float(x):.3f}"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._df = pd.DataFrame()
        self._setup_empty_df()
    
    def _setup_empty_df(self):
        """Initialize empty DataFrame with proper columns."""
        cols = [c[0] for c in self.COLUMNS if c[0] != 'index']
        self._df = pd.DataFrame(columns=cols)
    
    def set_dataframe(self, df: pd.DataFrame):
        """Set the underlying DataFrame."""
        self.beginResetModel()
        self._df = df.copy()
        self._df.columns = [c.lower() for c in self._df.columns]
        self.endResetModel()
        self.data_changed.emit()
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the underlying DataFrame."""
        return self._df.copy()
    
    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._df)
    
    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.COLUMNS)
    
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        
        row = index.row()
        col = index.column()
        col_def = self.COLUMNS[col]
        col_name = col_def[0]
        format_func = col_def[3]
        
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col_name == 'index':
                return str(row)
            if col_name in self._df.columns:
                value = self._df.iloc[row][col_name]
                if role == Qt.DisplayRole:
                    try:
                        return format_func(value)
                    except (ValueError, TypeError):
                        return str(value)
                return value
            return ""
        
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        
        if role == Qt.BackgroundRole:
            # Zebra striping
            if row % 2 == 1:
                return QColor('#0A1628')
        
        return None
    
    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or role != Qt.EditRole:
            return False
        
        row = index.row()
        col = index.column()
        col_name = self.COLUMNS[col][0]
        
        if col_name == 'index':
            return False
        
        if col_name in self._df.columns:
            try:
                # Convert value to appropriate type
                if col_name in ['deg', 'thickness', 'e_x', 'e_y', 'e_s', 'v_x']:
                    value = float(value)
                self._df.at[row, col_name] = value
                self.dataChanged.emit(index, index)
                self.data_changed.emit()
                return True
            except (ValueError, TypeError):
                return False
        return False
    
    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        
        col = index.column()
        editable = self.COLUMNS[col][2]
        
        flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if editable:
            flags |= Qt.ItemIsEditable
        return flags
    
    def headerData(self, section: int, orientation: Qt.Orientation, 
                   role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.COLUMNS[section][1]
            else:
                return str(section)
        return None
    
    def add_row(self, row_data: Optional[dict] = None):
        """Add a new row to the table."""
        self.beginInsertRows(QModelIndex(), len(self._df), len(self._df))
        
        defaults = {
            'material': 'T300/5208',
            'deg': 0.0,
            'num': 1,
            't': 0.000125,
            'thickness': 0.000125,
            'e_x': 181e9,
            'e_y': 10.3e9,
            'e_s': 7.17e9,
            'v_x': 0.28
        }
        if row_data:
            defaults.update(row_data)
        
        new_row = pd.DataFrame([defaults])
        self._df = pd.concat([self._df, new_row], ignore_index=True)
        
        self.endInsertRows()
        self.data_changed.emit()
    
    def remove_row(self, row: int):
        """Remove a row from the table."""
        if 0 <= row < len(self._df):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._df = self._df.drop(row).reset_index(drop=True)
            self.endRemoveRows()
            self.data_changed.emit()


class LayupEditor(QWidget):
    """
    Widget for editing the composite laminate layup.
    
    This widget provides a spreadsheet-like interface for defining
    the laminate structure with features for adding/removing plies
    and importing/exporting data.
    
    Composite Engineering Note:
        The editor validates inputs in real-time and shows
        constraint status (symmetry, balance, thickness) to
        guide the design process.
    """
    
    layup_changed = Signal(pd.DataFrame)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = LaminateModel()
        self._table_model = LaminateTableModel(self)
        self._materials_db = get_material_database()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Laminate Layup Editor")
        title.setObjectName("header")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #007DD7;")
        header_layout.addWidget(title)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Create splitter for table and side panel
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side: Table
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        table_layout.setContentsMargins(0, 0, 0, 0)
        
        # Table view
        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setAlternatingRowColors(True)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table_view.setSortingEnabled(True)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.setMinimumHeight(400)
        table_layout.addWidget(self._table_view)
        
        # Table buttons
        button_layout = QHBoxLayout()
        
        self._add_btn = QPushButton("➕ Add Ply")
        self._add_btn.setMinimumWidth(100)
        button_layout.addWidget(self._add_btn)
        
        self._remove_btn = QPushButton("➖ Remove Ply")
        self._remove_btn.setMinimumWidth(100)
        button_layout.addWidget(self._remove_btn)
        
        self._duplicate_btn = QPushButton("📋 Duplicate")
        self._duplicate_btn.setMinimumWidth(100)
        button_layout.addWidget(self._duplicate_btn)
        
        button_layout.addStretch()
        
        self._import_btn = QPushButton("📥 Import Excel")
        self._import_btn.setMinimumWidth(120)
        button_layout.addWidget(self._import_btn)
        
        self._export_btn = QPushButton("📤 Export Excel")
        self._export_btn.setMinimumWidth(120)
        button_layout.addWidget(self._export_btn)
        
        table_layout.addLayout(button_layout)
        splitter.addWidget(table_widget)
        
        # Right side: Info panel
        info_widget = QWidget()
        info_widget.setMaximumWidth(350)
        info_widget.setMinimumWidth(280)
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(12)
        
        # Summary group
        summary_group = QGroupBox("Laminate Summary")
        summary_layout = QFormLayout(summary_group)
        summary_layout.setSpacing(8)
        
        self._num_plies_label = QLabel("0")
        self._num_plies_label.setStyleSheet("font-weight: bold;")
        summary_layout.addRow("Total Plies:", self._num_plies_label)
        
        self._thickness_label = QLabel("0.000 mm")
        self._thickness_label.setStyleSheet("font-weight: bold;")
        summary_layout.addRow("Total Thickness:", self._thickness_label)
        
        self._optimizable_label = QLabel("0")
        self._optimizable_label.setStyleSheet("font-weight: bold;")
        summary_layout.addRow("Optimizable Plies:", self._optimizable_label)
        
        info_layout.addWidget(summary_group)
        
        # Constraint status group
        constraint_group = QGroupBox("Constraint Status")
        constraint_layout = QVBoxLayout(constraint_group)
        constraint_layout.setSpacing(8)
        
        self._symmetry_status = QLabel("Symmetry: —")
        constraint_layout.addWidget(self._symmetry_status)
        
        self._balance_status = QLabel("Balance: —")
        constraint_layout.addWidget(self._balance_status)
        
        self._thickness_status = QLabel("Thickness: —")
        constraint_layout.addWidget(self._thickness_status)
        
        info_layout.addWidget(constraint_group)
        
        # Quick add material group
        material_group = QGroupBox("Quick Add Material")
        material_layout = QVBoxLayout(material_group)
        
        self._material_combo = QComboBox()
        self._material_combo.addItems(list(self._materials_db.keys()))
        material_layout.addWidget(self._material_combo)
        
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle (°):"))
        self._angle_spin = QDoubleSpinBox()
        self._angle_spin.setRange(-90, 90)
        self._angle_spin.setValue(0)
        self._angle_spin.setDecimals(1)
        angle_layout.addWidget(self._angle_spin)
        material_layout.addLayout(angle_layout)
        
        self._quick_add_btn = QPushButton("Add with Material")
        self._quick_add_btn.setObjectName("success")
        material_layout.addWidget(self._quick_add_btn)
        
        info_layout.addWidget(material_group)
        
        # Engineering note
        note_frame = QFrame()
        note_frame.setStyleSheet("""
            QFrame {
                background-color: #132035;
                border: 1px solid #007DD7;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(12, 12, 12, 12)
        
        note_title = QLabel("📘 Composite Engineering Note")
        note_title.setStyleSheet("font-weight: bold; color: #007DD7;")
        note_layout.addWidget(note_title)
        
        note_text = QLabel(
            "The layup sequence defines the stacking order of plies "
            "from bottom to top. For symmetric laminates, optimize only "
            "the first half and the GA will mirror the sequence."
        )
        note_text.setWordWrap(True)
        note_text.setStyleSheet("color: #a0a0a0;")
        note_layout.addWidget(note_text)
        
        info_layout.addWidget(note_frame)
        info_layout.addStretch()
        
        splitter.addWidget(info_widget)
        splitter.setSizes([800, 350])
        
        main_layout.addWidget(splitter, 1)
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        self._add_btn.clicked.connect(self._on_add_ply)
        self._remove_btn.clicked.connect(self._on_remove_ply)
        self._duplicate_btn.clicked.connect(self._on_duplicate_ply)
        self._import_btn.clicked.connect(self._on_import_excel)
        self._export_btn.clicked.connect(self._on_export_excel)
        self._quick_add_btn.clicked.connect(self._on_quick_add)
        self._table_model.data_changed.connect(self._on_data_changed)
    
    def set_model(self, model: LaminateModel):
        """Set the laminate model."""
        self._model = model
        self._table_model.set_dataframe(model.dataframe)
        self._update_summary()
    
    def get_dataframe(self) -> pd.DataFrame:
        """Get the current layup data."""
        return self._table_model.get_dataframe()
    
    def set_dataframe(self, df: pd.DataFrame):
        """Set the layup data."""
        self._table_model.set_dataframe(df)
        self._update_summary()
    
    @Slot()
    def _on_add_ply(self):
        """Add a new ply with default values."""
        self._table_model.add_row()
        self._update_summary()
    
    @Slot()
    def _on_remove_ply(self):
        """Remove the selected ply."""
        selection = self._table_view.selectionModel().selectedRows()
        if selection:
            row = selection[0].row()
            self._table_model.remove_row(row)
            self._update_summary()
    
    @Slot()
    def _on_duplicate_ply(self):
        """Duplicate the selected ply."""
        selection = self._table_view.selectionModel().selectedRows()
        if selection:
            row = selection[0].row()
            df = self._table_model.get_dataframe()
            if row < len(df):
                row_data = df.iloc[row].to_dict()
                self._table_model.add_row(row_data)
                self._update_summary()
    
    @Slot()
    def _on_quick_add(self):
        """Add a ply with selected material and angle."""
        material_name = self._material_combo.currentText()
        angle = self._angle_spin.value()
        
        if material_name in self._materials_db:
            props = self._materials_db[material_name]
            row_data = {
                'material': material_name,
                'deg': angle,
                'num': 1,
                't': props['typical_thickness'],
                'thickness': props['typical_thickness'],
                'e_x': props['e_x'],
                'e_y': props['e_y'],
                'e_s': props['e_s'],
                'v_x': props['v_x']
            }
            self._table_model.add_row(row_data)
            self._update_summary()
    
    @Slot()
    def _on_import_excel(self):
        """Import layup data from Excel file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Import Excel File", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        if filename:
            try:
                df = pd.read_excel(filename)
                self._table_model.set_dataframe(df)
                self._update_summary()
                QMessageBox.information(self, "Success", 
                                       f"Imported {len(df)} plies from Excel file.")
            except Exception as e:
                QMessageBox.critical(self, "Import Error", 
                                    f"Failed to import file:\n{str(e)}")
    
    @Slot()
    def _on_export_excel(self):
        """Export layup data to Excel file."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Excel File", "laminate_layup.xlsx",
            "Excel Files (*.xlsx);;All Files (*)"
        )
        if filename:
            try:
                df = self._table_model.get_dataframe()
                df.to_excel(filename, index=False)
                QMessageBox.information(self, "Success", 
                                       f"Exported {len(df)} plies to Excel file.")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", 
                                    f"Failed to export file:\n{str(e)}")
    
    @Slot()
    def _on_data_changed(self):
        """Handle data changes in the table."""
        df = self._table_model.get_dataframe()
        self._model.dataframe = df
        self._update_summary()
        self.layup_changed.emit(df)
    
    def _update_summary(self):
        """Update the summary panel with current data."""
        df = self._table_model.get_dataframe()
        
        # Basic stats
        num_plies = len(df)
        self._num_plies_label.setText(str(num_plies))
        
        if num_plies > 0:
            total_thickness = df['thickness'].sum()
            self._thickness_label.setText(f"{total_thickness * 1000:.3f} mm")
            
            # Count optimizable plies
            non_core = [i for i, row in df.iterrows() 
                       if str(row.get('material', '')).lower() != 'core']
            self._optimizable_label.setText(str(len(non_core)))
            
            # Update constraint status
            self._update_constraint_status(df, non_core)
        else:
            self._thickness_label.setText("0.000 mm")
            self._optimizable_label.setText("0")
            self._symmetry_status.setText("Symmetry: —")
            self._balance_status.setText("Balance: —")
            self._thickness_status.setText("Thickness: —")
    
    def _update_constraint_status(self, df: pd.DataFrame, non_core: list):
        """Update constraint status indicators."""
        # Tolerance for angle comparison in degrees
        # Composite Engineering Note: 0.1 degrees is typical manufacturing tolerance
        ANGLE_TOLERANCE = 0.1
        
        # Symmetry check
        if len(df) > 0:
            angles = df['deg'].values
            is_symmetric = np.allclose(angles, angles[::-1], atol=ANGLE_TOLERANCE)
            if is_symmetric:
                self._symmetry_status.setText("Symmetry: ✅ Symmetric")
                self._symmetry_status.setStyleSheet("color: #28a745;")
            else:
                self._symmetry_status.setText("Symmetry: ⚠️ Not symmetric")
                self._symmetry_status.setStyleSheet("color: #ffc107;")
        
        # Balance check (simplified)
        if len(df) > 0:
            angles = df['deg'].values
            pos_angles = np.sum(angles > 0)
            neg_angles = np.sum(angles < 0)
            if pos_angles == neg_angles:
                self._balance_status.setText("Balance: ✅ Balanced")
                self._balance_status.setStyleSheet("color: #28a745;")
            else:
                self._balance_status.setText("Balance: ⚠️ Not balanced")
                self._balance_status.setStyleSheet("color: #ffc107;")
        
        # Thickness check (assume 10mm limit)
        if len(df) > 0:
            total = df['thickness'].sum()
            max_thickness = self._model.config.max_total_thickness
            if total <= max_thickness:
                self._thickness_status.setText(f"Thickness: ✅ OK ({total*1000:.2f}mm)")
                self._thickness_status.setStyleSheet("color: #28a745;")
            else:
                self._thickness_status.setText(f"Thickness: ❌ Exceeds ({total*1000:.2f}mm)")
                self._thickness_status.setStyleSheet("color: #dc3545;")
