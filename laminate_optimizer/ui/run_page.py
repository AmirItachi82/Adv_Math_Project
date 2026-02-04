# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Run Page (Optimization & Monitoring)

This module provides the main optimization control and monitoring page,
featuring:
- GA settings panel with editable parameters
- Real-time fitness plot
- Results table
- Start/Stop controls

Composite Engineering Note:
    This page is the control center for running the genetic algorithm
    optimization. The live fitness plot shows convergence progress,
    while the settings panel allows fine-tuning of the GA parameters.
"""

from typing import Optional, Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from PySide6.QtCore import Qt, Signal, Slot, QObject, QThread
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QPushButton, QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
    QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSplitter, QScrollArea, QSizePolicy, QProgressBar
)
from PySide6.QtGui import QColor, QFont

import pyqtgraph as pg

# Support both package import and direct script execution
try:
    from ..models.laminate_model import LaminateModel, GAConfig
    from ..ga_adapter import GAAdapter, OptimizationResult
    from .styles import get_plot_style
except ImportError:
    from models.laminate_model import LaminateModel, GAConfig
    from ga_adapter import GAAdapter, OptimizationResult
    from ui.styles import get_plot_style


class GAWorker(QObject):
    """
    Worker object for running GA optimization in a separate thread.
    
    This class encapsulates the GA execution and communicates with
    the UI thread through Qt signals to maintain thread safety.
    
    Signals:
        generation_completed(int, float, float): Emitted after each generation
            with (generation_number, best_fitness, average_fitness)
        finished(OptimizationResult): Emitted when optimization completes
        aborted(): Emitted when optimization is aborted by user
        error(str): Emitted when an error occurs
    """
    
    generation_completed = Signal(int, float, float)
    finished = Signal(object)  # OptimizationResult
    aborted = Signal()
    error = Signal(str)
    
    def __init__(self, adapter: GAAdapter):
        super().__init__()
        self._adapter = adapter
        self._is_running = False
    
    @property
    def is_running(self) -> bool:
        return self._is_running
    
    @Slot()
    def run(self):
        """Execute the GA optimization."""
        self._is_running = True
        
        try:
            def progress_callback(gen: int, best_fit: float, avg_fit: float):
                self.generation_completed.emit(gen, best_fit, avg_fit)
            
            result = self._adapter.run_optimization(progress_callback)
            
            if result.extra_data.get('was_stopped', False):
                self.aborted.emit()
            else:
                self.finished.emit(result)
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._is_running = False
    
    def stop(self):
        """Request the GA to stop."""
        self._adapter.request_stop()


class ResultsTableModel:
    """Helper for managing the results table data."""
    
    COLUMNS = ['Generation', 'Best Fitness', 'Avg Fitness', 'Best Angles', 'Thickness']
    
    def __init__(self, table: QTableWidget):
        self._table = table
        self._setup_table()
    
    def _setup_table(self):
        """Initialize the table widget."""
        self._table.setColumnCount(len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)
    
    def clear(self):
        """Clear all data from the table."""
        self._table.setRowCount(0)
    
    def add_result(self, gen: int, best_fit: float, avg_fit: float, 
                   angles: Optional[List[float]] = None, thickness: float = 0.0):
        """Add a result row to the table."""
        row = self._table.rowCount()
        self._table.insertRow(row)
        
        # Generation
        item = QTableWidgetItem(str(gen))
        item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 0, item)
        
        # Best fitness
        item = QTableWidgetItem(f"{best_fit:.6e}")
        item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 1, item)
        
        # Average fitness
        item = QTableWidgetItem(f"{avg_fit:.6e}")
        item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 2, item)
        
        # Best angles
        angles_str = ", ".join([f"{a:.0f}°" for a in (angles or [])])
        item = QTableWidgetItem(angles_str)
        self._table.setItem(row, 3, item)
        
        # Thickness
        item = QTableWidgetItem(f"{thickness*1000:.3f} mm")
        item.setTextAlignment(Qt.AlignCenter)
        self._table.setItem(row, 4, item)
        
        # Scroll to show latest
        self._table.scrollToBottom()


class RunPage(QWidget):
    """
    Main optimization and monitoring page.
    
    This page provides:
    - Left panel: GA settings with editable parameters
    - Right panel: Live fitness plot and results table
    - Control buttons: Start, Stop, Reset
    
    Composite Engineering Note:
        The GA settings allow engineers to tune the optimization
        process based on problem complexity and available time.
        Higher populations and generations improve solution quality
        but increase computation time.
    """
    
    optimization_started = Signal()
    optimization_finished = Signal(object)  # OptimizationResult
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._model = LaminateModel()
        self._adapter = GAAdapter()
        self._worker: Optional[GAWorker] = None
        self._worker_thread: Optional[QThread] = None
        self._history: List[Tuple[int, float, float]] = []
        
        self._setup_ui()
        self._connect_signals()
        self._load_defaults()
    
    def _setup_ui(self):
        """Set up the user interface."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)
        
        # Left panel: Settings (360px)
        left_panel = self._create_settings_panel()
        left_panel.setFixedWidth(360)
        main_layout.addWidget(left_panel)
        
        # Right panel: Results and plot
        right_panel = self._create_results_panel()
        main_layout.addWidget(right_panel, 1)
    
    def _create_settings_panel(self) -> QWidget:
        """Create the GA settings panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("GA Settings")
        header.setObjectName("header")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(16)
        
        # GA Parameters group
        ga_group = QGroupBox("Algorithm Parameters")
        ga_layout = QGridLayout(ga_group)
        ga_layout.setSpacing(10)
        
        row = 0
        
        # Population size
        ga_layout.addWidget(QLabel("Population Size:"), row, 0)
        self._pop_size_spin = QSpinBox()
        self._pop_size_spin.setRange(10, 1000)
        self._pop_size_spin.setValue(200)
        self._pop_size_spin.setToolTip("Number of individuals in each generation")
        ga_layout.addWidget(self._pop_size_spin, row, 1)
        row += 1
        
        # Number of generations
        ga_layout.addWidget(QLabel("Generations:"), row, 0)
        self._generations_spin = QSpinBox()
        self._generations_spin.setRange(10, 2000)
        self._generations_spin.setValue(300)
        self._generations_spin.setToolTip("Maximum number of generations to evolve")
        ga_layout.addWidget(self._generations_spin, row, 1)
        row += 1
        
        # Crossover rate
        ga_layout.addWidget(QLabel("Crossover Rate:"), row, 0)
        self._crossover_spin = QDoubleSpinBox()
        self._crossover_spin.setRange(0.0, 1.0)
        self._crossover_spin.setSingleStep(0.05)
        self._crossover_spin.setValue(0.9)
        self._crossover_spin.setDecimals(2)
        self._crossover_spin.setToolTip("Probability of crossover between parents")
        ga_layout.addWidget(self._crossover_spin, row, 1)
        row += 1
        
        # Mutation rate
        ga_layout.addWidget(QLabel("Mutation Rate:"), row, 0)
        self._mutation_spin = QDoubleSpinBox()
        self._mutation_spin.setRange(0.0, 1.0)
        self._mutation_spin.setSingleStep(0.01)
        self._mutation_spin.setValue(0.08)
        self._mutation_spin.setDecimals(3)
        self._mutation_spin.setToolTip("Probability of mutation per bit")
        ga_layout.addWidget(self._mutation_spin, row, 1)
        row += 1
        
        # Elitism count
        ga_layout.addWidget(QLabel("Elitism Count:"), row, 0)
        self._elitism_spin = QSpinBox()
        self._elitism_spin.setRange(0, 20)
        self._elitism_spin.setValue(2)
        self._elitism_spin.setToolTip("Number of best individuals preserved each generation")
        ga_layout.addWidget(self._elitism_spin, row, 1)
        row += 1
        
        # Selection method
        ga_layout.addWidget(QLabel("Selection Method:"), row, 0)
        self._selection_combo = QComboBox()
        self._selection_combo.addItems(['tournament', 'roulette', 'rank'])
        self._selection_combo.setToolTip("Parent selection strategy")
        ga_layout.addWidget(self._selection_combo, row, 1)
        row += 1
        
        # Tournament size
        ga_layout.addWidget(QLabel("Tournament Size:"), row, 0)
        self._tournament_spin = QSpinBox()
        self._tournament_spin.setRange(2, 10)
        self._tournament_spin.setValue(3)
        self._tournament_spin.setToolTip("Number of individuals in tournament selection")
        ga_layout.addWidget(self._tournament_spin, row, 1)
        
        scroll_layout.addWidget(ga_group)
        
        # Composite constraints group
        constraint_group = QGroupBox("Composite Constraints")
        constraint_layout = QGridLayout(constraint_group)
        constraint_layout.setSpacing(10)
        
        row = 0
        
        # Max thickness
        constraint_layout.addWidget(QLabel("Max Thickness (mm):"), row, 0)
        self._max_thickness_spin = QDoubleSpinBox()
        self._max_thickness_spin.setRange(0.1, 100.0)
        self._max_thickness_spin.setValue(10.0)
        self._max_thickness_spin.setDecimals(2)
        self._max_thickness_spin.setToolTip("Maximum allowable laminate thickness")
        constraint_layout.addWidget(self._max_thickness_spin, row, 1)
        row += 1
        
        # Symmetry required
        self._symmetry_check = QCheckBox("Symmetry Required")
        self._symmetry_check.setChecked(True)
        self._symmetry_check.setToolTip("Enforce symmetric layup about midplane")
        constraint_layout.addWidget(self._symmetry_check, row, 0, 1, 2)
        row += 1
        
        # Balanced required
        self._balanced_check = QCheckBox("Balanced Required")
        self._balanced_check.setChecked(False)
        self._balanced_check.setToolTip("Enforce balanced layup (+θ/-θ pairs)")
        constraint_layout.addWidget(self._balanced_check, row, 0, 1, 2)
        
        scroll_layout.addWidget(constraint_group)
        
        # Target strains group
        target_group = QGroupBox("Optimization Targets")
        target_layout = QGridLayout(target_group)
        target_layout.setSpacing(8)
        
        # Target strain εx
        target_layout.addWidget(QLabel("Target εx:"), 0, 0)
        self._target_ex_spin = QDoubleSpinBox()
        self._target_ex_spin.setRange(-1.0, 1.0)
        self._target_ex_spin.setDecimals(6)
        self._target_ex_spin.setValue(0.0287)
        self._target_ex_spin.setSingleStep(0.001)
        target_layout.addWidget(self._target_ex_spin, 0, 1)
        
        # Target strain εy
        target_layout.addWidget(QLabel("Target εy:"), 1, 0)
        self._target_ey_spin = QDoubleSpinBox()
        self._target_ey_spin.setRange(-1.0, 1.0)
        self._target_ey_spin.setDecimals(6)
        self._target_ey_spin.setValue(-0.0085)
        self._target_ey_spin.setSingleStep(0.001)
        target_layout.addWidget(self._target_ey_spin, 1, 1)
        
        # Applied force Nx
        target_layout.addWidget(QLabel("Force Nx (N/m):"), 2, 0)
        self._force_nx_spin = QDoubleSpinBox()
        self._force_nx_spin.setRange(-1e9, 1e9)
        self._force_nx_spin.setDecimals(0)
        self._force_nx_spin.setValue(2e6)
        self._force_nx_spin.setSingleStep(1e5)
        target_layout.addWidget(self._force_nx_spin, 2, 1)
        
        scroll_layout.addWidget(target_group)
        
        # Random seed group
        seed_group = QGroupBox("Reproducibility")
        seed_layout = QHBoxLayout(seed_group)
        
        self._use_seed_check = QCheckBox("Use Random Seed:")
        self._use_seed_check.setChecked(True)
        seed_layout.addWidget(self._use_seed_check)
        
        self._seed_spin = QSpinBox()
        self._seed_spin.setRange(0, 999999)
        self._seed_spin.setValue(42)
        seed_layout.addWidget(self._seed_spin)
        
        scroll_layout.addWidget(seed_group)
        
        # Engineering note
        note_frame = QFrame()
        note_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d30;
                border: 1px solid #0078d4;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        note_layout = QVBoxLayout(note_frame)
        note_layout.setContentsMargins(12, 12, 12, 12)
        
        note_title = QLabel("📘 Composite Engineering Note")
        note_title.setStyleSheet("font-weight: bold; color: #0078d4;")
        note_layout.addWidget(note_title)
        
        note_text = QLabel(
            "Higher population sizes explore more solutions but take longer. "
            "Mutation rate affects diversity—too high causes random search, "
            "too low leads to premature convergence."
        )
        note_text.setWordWrap(True)
        note_text.setStyleSheet("color: #a0a0a0;")
        note_layout.addWidget(note_text)
        
        scroll_layout.addWidget(note_frame)
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self._defaults_btn = QPushButton("Load Defaults")
        self._defaults_btn.setMinimumWidth(100)
        button_layout.addWidget(self._defaults_btn)
        
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setMinimumWidth(80)
        button_layout.addWidget(self._reset_btn)
        
        layout.addLayout(button_layout)
        
        return panel
    
    def _create_results_panel(self) -> QWidget:
        """Create the results and control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QLabel("Optimization Results")
        header.setObjectName("header")
        header.setStyleSheet("font-size: 18pt; font-weight: bold; color: #0078d4;")
        layout.addWidget(header)
        
        # Plot (55% height)
        plot_group = QGroupBox("Live Fitness Plot")
        plot_layout = QVBoxLayout(plot_group)
        
        # Configure pyqtgraph for dark theme
        pg.setConfigOptions(antialias=True)
        style = get_plot_style()
        
        self._plot_widget = pg.PlotWidget()
        self._plot_widget.setBackground(style['background'])
        self._plot_widget.setMinimumHeight(350)
        self._plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self._plot_widget.setLabel('left', 'Fitness Value')
        self._plot_widget.setLabel('bottom', 'Generation')
        self._plot_widget.addLegend()
        
        # Create plot curves
        self._best_curve = self._plot_widget.plot(
            pen=pg.mkPen(color=style['best_fitness_color'], width=2),
            name='Best Fitness'
        )
        self._avg_curve = self._plot_widget.plot(
            pen=pg.mkPen(color=style['avg_fitness_color'], width=2, style=Qt.DashLine),
            name='Avg Fitness'
        )
        
        plot_layout.addWidget(self._plot_widget)
        layout.addWidget(plot_group)
        
        # Control section
        control_layout = QHBoxLayout()
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("Ready")
        control_layout.addWidget(self._progress_bar, 1)
        
        # Start button
        self._start_btn = QPushButton("▶ START OPTIMIZATION")
        self._start_btn.setObjectName("primary")
        self._start_btn.setMinimumWidth(200)
        self._start_btn.setMinimumHeight(50)
        control_layout.addWidget(self._start_btn)
        
        # Stop button
        self._stop_btn = QPushButton("⏹ STOP")
        self._stop_btn.setObjectName("danger")
        self._stop_btn.setMinimumWidth(100)
        self._stop_btn.setMinimumHeight(50)
        self._stop_btn.setEnabled(False)
        control_layout.addWidget(self._stop_btn)
        
        layout.addLayout(control_layout)
        
        # Results table (45% height)
        table_group = QGroupBox("Results History")
        table_layout = QVBoxLayout(table_group)
        
        self._results_table = QTableWidget()
        self._results_model = ResultsTableModel(self._results_table)
        self._results_table.setMinimumHeight(200)
        table_layout.addWidget(self._results_table)
        
        layout.addWidget(table_group)
        
        # Status label
        self._status_label = QLabel("Status: Ready")
        self._status_label.setStyleSheet("color: #a0a0a0; padding: 4px;")
        layout.addWidget(self._status_label)
        
        return panel
    
    def _connect_signals(self):
        """Connect widget signals to slots."""
        self._start_btn.clicked.connect(self._on_start)
        self._stop_btn.clicked.connect(self._on_stop)
        self._defaults_btn.clicked.connect(self._load_defaults)
        self._reset_btn.clicked.connect(self._on_reset)
    
    def _load_defaults(self):
        """Load default GA configuration values."""
        config = GAConfig()
        
        self._pop_size_spin.setValue(config.population_size)
        self._generations_spin.setValue(config.num_generations)
        self._crossover_spin.setValue(config.crossover_rate)
        self._mutation_spin.setValue(config.mutation_rate)
        self._elitism_spin.setValue(config.elitism_count)
        self._selection_combo.setCurrentText(config.selection_method)
        self._tournament_spin.setValue(config.tournament_size)
        self._max_thickness_spin.setValue(config.max_total_thickness * 1000)
        self._symmetry_check.setChecked(config.symmetry_required)
        self._balanced_check.setChecked(config.balanced_required)
        
        self._target_ex_spin.setValue(config.target_strains[0])
        self._target_ey_spin.setValue(config.target_strains[1])
        self._force_nx_spin.setValue(config.force_moment[0])
        
        if config.random_seed is not None:
            self._use_seed_check.setChecked(True)
            self._seed_spin.setValue(config.random_seed)
        else:
            self._use_seed_check.setChecked(False)
    
    def _get_config_from_ui(self) -> Dict[str, Any]:
        """Get GA configuration from UI controls."""
        target_strains = [
            self._target_ex_spin.value(),
            self._target_ey_spin.value(),
            0.0, 0.0, 0.0, 0.0
        ]
        force_moment = [
            self._force_nx_spin.value(),
            0.0, 0.0, 0.0, 0.0, 0.0
        ]
        
        return {
            'population_size': self._pop_size_spin.value(),
            'num_generations': self._generations_spin.value(),
            'crossover_rate': self._crossover_spin.value(),
            'mutation_rate': self._mutation_spin.value(),
            'elitism_count': self._elitism_spin.value(),
            'selection_method': self._selection_combo.currentText(),
            'tournament_size': self._tournament_spin.value(),
            'max_total_thickness': self._max_thickness_spin.value() / 1000.0,
            'symmetry_required': self._symmetry_check.isChecked(),
            'balanced_required': self._balanced_check.isChecked(),
            'target_strains': target_strains,
            'force_moment': force_moment,
            'random_seed': self._seed_spin.value() if self._use_seed_check.isChecked() else None
        }
    
    def set_model(self, model: LaminateModel):
        """Set the laminate model."""
        self._model = model
    
    def set_layup_data(self, df: pd.DataFrame):
        """Set the layup data for optimization."""
        self._adapter.set_layup_data(df)
    
    @Slot()
    def _on_start(self):
        """Start the optimization."""
        # Get layup data from model
        df = self._model.dataframe
        if len(df) == 0:
            self._status_label.setText("Status: ❌ No layup data! Please define plies first.")
            self._status_label.setStyleSheet("color: #dc3545; padding: 4px;")
            return
        
        # Validate layup
        validation = self._adapter.validate_layup()
        if not validation['valid']:
            errors = '\n'.join(validation['errors'])
            self._status_label.setText(f"Status: ❌ Invalid layup: {errors}")
            self._status_label.setStyleSheet("color: #dc3545; padding: 4px;")
            return
        
        # Update adapter configuration
        config = self._get_config_from_ui()
        self._adapter.config = config
        self._adapter.set_layup_data(df)
        
        # Clear previous results
        self._history.clear()
        self._results_model.clear()
        self._best_curve.setData([], [])
        self._avg_curve.setData([], [])
        
        # Create worker and thread
        self._worker_thread = QThread()
        self._worker = GAWorker(self._adapter)
        self._worker.moveToThread(self._worker_thread)
        
        # Connect signals
        self._worker_thread.started.connect(self._worker.run)
        self._worker.generation_completed.connect(self._on_generation_completed)
        self._worker.finished.connect(self._on_optimization_finished)
        self._worker.aborted.connect(self._on_optimization_aborted)
        self._worker.error.connect(self._on_optimization_error)
        
        # Cleanup connections
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.aborted.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._cleanup_worker)
        
        # Update UI state
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("Running... 0%")
        self._status_label.setText("Status: 🔄 Optimization running...")
        self._status_label.setStyleSheet("color: #ffc107; padding: 4px;")
        
        # Start the thread
        self._worker_thread.start()
        self.optimization_started.emit()
    
    @Slot()
    def _on_stop(self):
        """Stop the optimization."""
        if self._worker:
            self._worker.stop()
        self._status_label.setText("Status: ⏸️ Stopping...")
        self._status_label.setStyleSheet("color: #ffc107; padding: 4px;")
    
    @Slot()
    def _on_reset(self):
        """Reset the results."""
        self._history.clear()
        self._results_model.clear()
        self._best_curve.setData([], [])
        self._avg_curve.setData([], [])
        self._progress_bar.setValue(0)
        self._progress_bar.setFormat("Ready")
        self._status_label.setText("Status: Ready")
        self._status_label.setStyleSheet("color: #a0a0a0; padding: 4px;")
    
    @Slot(int, float, float)
    def _on_generation_completed(self, gen: int, best_fit: float, avg_fit: float):
        """Handle generation completion."""
        self._history.append((gen, best_fit, avg_fit))
        
        # Update plot
        gens = [h[0] for h in self._history]
        bests = [h[1] for h in self._history]
        avgs = [h[2] for h in self._history]
        
        self._best_curve.setData(gens, bests)
        self._avg_curve.setData(gens, avgs)
        
        # Update progress
        max_gen = self._generations_spin.value()
        progress = int(100 * gen / max_gen)
        self._progress_bar.setValue(progress)
        self._progress_bar.setFormat(f"Running... {progress}% (Gen {gen}/{max_gen})")
        
        # Add to results table (every 10 generations)
        if gen % 10 == 0 or gen == 1:
            thickness = self._model.total_thickness
            self._results_model.add_result(gen, best_fit, avg_fit, thickness=thickness)
    
    @Slot(object)
    def _on_optimization_finished(self, result: OptimizationResult):
        """Handle optimization completion."""
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setValue(100)
        self._progress_bar.setFormat("Completed!")
        
        if result.success:
            self._status_label.setText(
                f"Status: ✅ Optimization complete! Best fitness: {result.best_fitness:.6e}"
            )
            self._status_label.setStyleSheet("color: #28a745; padding: 4px;")
            
            # Add final result to table
            thickness = result.extra_data.get('total_thickness', 0)
            self._results_model.add_result(
                len(result.history) - 1, 
                result.best_fitness,
                result.history[-1][2] if result.history else 0,
                result.best_angles,
                thickness
            )
        else:
            self._status_label.setText(f"Status: ⚠️ {result.message}")
            self._status_label.setStyleSheet("color: #ffc107; padding: 4px;")
        
        self.optimization_finished.emit(result)
    
    @Slot()
    def _on_optimization_aborted(self):
        """Handle optimization abort."""
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setFormat("Stopped")
        self._status_label.setText("Status: ⏹️ Optimization stopped by user")
        self._status_label.setStyleSheet("color: #ffc107; padding: 4px;")
    
    @Slot(str)
    def _on_optimization_error(self, error_msg: str):
        """Handle optimization error."""
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress_bar.setFormat("Error")
        self._status_label.setText(f"Status: ❌ Error: {error_msg}")
        self._status_label.setStyleSheet("color: #dc3545; padding: 4px;")
    
    def _cleanup_worker(self):
        """Clean up worker thread resources."""
        self._worker = None
        self._worker_thread = None
