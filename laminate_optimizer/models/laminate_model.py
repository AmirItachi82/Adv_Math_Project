# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Data Models and Constraints

This module contains the core data models used throughout the application
for managing composite laminate data and genetic algorithm configuration.

Composite Engineering Note:
    These models represent the essential parameters for composite laminate
    optimization including ply properties, stacking sequences, and 
    manufacturing constraints such as symmetry and balance requirements.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np


# Tolerance for angle comparisons in degrees
# Composite Engineering Note: 0.01 degrees is well below typical manufacturing
# tolerance (~0.5-1 degree) but allows for floating point comparison
ANGLE_TOLERANCE_DEG = 0.01


@dataclass
class PlyData:
    """
    Represents a single ply in the composite laminate.
    
    Composite Engineering Note:
        A ply is a single layer of composite material with specific
        fiber orientation and mechanical properties. The orientation
        angle significantly affects the laminate's mechanical behavior.
    
    Attributes:
        index: Ply position in the stack (0-indexed from bottom)
        material: Material designation (e.g., 'T300/5208')
        angle: Fiber orientation angle in degrees
        thickness: Ply thickness in meters
        e_x: Longitudinal modulus in Pa
        e_y: Transverse modulus in Pa
        e_s: Shear modulus in Pa
        v_x: Poisson's ratio (major)
    """
    index: int
    material: str
    angle: float
    thickness: float
    e_x: float
    e_y: float
    e_s: float
    v_x: float
    
    @property
    def is_core(self) -> bool:
        """Check if this ply is a core material (not optimizable)."""
        return self.material.lower() == 'core'


@dataclass
class GAConfig:
    """
    Genetic Algorithm configuration parameters.
    
    Composite Engineering Note:
        The GA parameters control the optimization process. Higher population
        sizes and generation counts typically yield better solutions but
        require more computation time. Crossover and mutation rates affect
        the balance between exploration and exploitation in the search.
    
    Attributes:
        population_size: Number of individuals in each generation
        num_generations: Maximum number of generations to evolve
        crossover_rate: Probability of crossover between parents (0-1)
        mutation_rate: Probability of mutation per bit (0-1)
        elitism_count: Number of best individuals preserved each generation
        selection_method: Selection strategy ('tournament', 'roulette', 'rank')
        tournament_size: Size of tournament for tournament selection
        max_total_thickness: Maximum allowable laminate thickness (m)
        symmetry_required: Enforce symmetric layup about midplane
        balanced_required: Enforce balanced layup (+θ/-θ pairs)
        
        target_strains: Target strain values [εx, εy, γxy, κx, κy, κxy]
        force_moment: Applied loads [Nx, Ny, Nxy, Mx, My, Mxy]
        fitness_weights: Weighting factors for strain components
    """
    # GA Parameters
    population_size: int = 200
    num_generations: int = 300
    crossover_rate: float = 0.9
    mutation_rate: float = 0.08
    elitism_count: int = 2
    selection_method: str = "tournament"
    tournament_size: int = 3
    
    # Composite Constraints
    max_total_thickness: float = 0.01  # 10mm default
    symmetry_required: bool = True
    balanced_required: bool = False
    
    # Optimization Targets
    target_strains: np.ndarray = field(
        default_factory=lambda: np.array([0.0287, -0.0085, 0.0, 0.0, 0.0, 0.0])
    )
    force_moment: np.ndarray = field(
        default_factory=lambda: np.array([2e6, 0.0, 0.0, 0.0, 0.0, 0.0])
    )
    fitness_weights: np.ndarray = field(
        default_factory=lambda: np.array([1.0, 1.0, 0.0])
    )
    
    # Angle discretization
    angle_set: np.ndarray = field(
        default_factory=lambda: np.array([0.0, 45.0, -45.0, 90.0])
    )
    
    # Random seed for reproducibility (None for non-deterministic)
    random_seed: Optional[int] = 42
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            'population_size': self.population_size,
            'num_generations': self.num_generations,
            'crossover_rate': self.crossover_rate,
            'mutation_rate': self.mutation_rate,
            'elitism_count': self.elitism_count,
            'selection_method': self.selection_method,
            'tournament_size': self.tournament_size,
            'max_total_thickness': self.max_total_thickness,
            'symmetry_required': self.symmetry_required,
            'balanced_required': self.balanced_required,
            'target_strains': self.target_strains.tolist(),
            'force_moment': self.force_moment.tolist(),
            'fitness_weights': self.fitness_weights.tolist(),
            'angle_set': self.angle_set.tolist(),
            'random_seed': self.random_seed
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GAConfig':
        """Create configuration from dictionary."""
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                if key in ['target_strains', 'force_moment', 'fitness_weights', 'angle_set']:
                    setattr(config, key, np.array(value))
                else:
                    setattr(config, key, value)
        return config


class LaminateModel:
    """
    Main data model for managing the composite laminate layup.
    
    Composite Engineering Note:
        The laminate model manages the complete stack of plies and
        provides methods for constraint validation, data import/export,
        and integration with the genetic algorithm optimization.
    
    This class wraps a pandas DataFrame internally and provides
    a clean interface for the UI to interact with the data.
    """
    
    # Column definitions for the laminate data
    COLUMNS = ['material', 'deg', 'num', 't', 'thickness', 'e_x', 'e_y', 'e_s', 'v_x']
    DISPLAY_COLUMNS = ['Ply Index', 'Material', 'Angle (°)', 'Thickness (m)', 
                       'E_x (Pa)', 'E_y (Pa)', 'E_s (Pa)', 'ν_x']
    
    def __init__(self, df: Optional[pd.DataFrame] = None):
        """
        Initialize the laminate model.
        
        Args:
            df: Optional pandas DataFrame with laminate data.
                If None, creates an empty model.
        """
        if df is not None:
            self._df = df.copy()
            self._ensure_columns()
        else:
            self._df = pd.DataFrame(columns=self.COLUMNS)
        
        self._config = GAConfig()
    
    def _ensure_columns(self):
        """Ensure all required columns exist with lowercase names."""
        self._df.columns = [c.lower() for c in self._df.columns]
        # Add missing columns with default values
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
        for col, default in defaults.items():
            if col not in self._df.columns:
                self._df[col] = default
    
    @property
    def dataframe(self) -> pd.DataFrame:
        """Get the underlying DataFrame."""
        return self._df.copy()
    
    @dataframe.setter
    def dataframe(self, df: pd.DataFrame):
        """Set the underlying DataFrame."""
        self._df = df.copy()
        self._ensure_columns()
    
    @property
    def config(self) -> GAConfig:
        """Get the GA configuration."""
        return self._config
    
    @config.setter
    def config(self, config: GAConfig):
        """Set the GA configuration."""
        self._config = config
    
    @property
    def num_plies(self) -> int:
        """Get the total number of plies."""
        return len(self._df)
    
    @property
    def total_thickness(self) -> float:
        """
        Get the total laminate thickness.
        
        Composite Engineering Note:
            Total thickness is a critical parameter as it affects
            the laminate's weight, stiffness, and manufacturing cost.
        """
        return float(self._df['thickness'].sum()) if len(self._df) > 0 else 0.0
    
    @property
    def non_core_indices(self) -> List[int]:
        """Get indices of non-core (optimizable) plies."""
        return [i for i, row in self._df.iterrows() 
                if str(row['material']).lower() != 'core']
    
    def get_ply(self, index: int) -> Optional[PlyData]:
        """Get a single ply by index."""
        if 0 <= index < len(self._df):
            row = self._df.iloc[index]
            return PlyData(
                index=index,
                material=str(row['material']),
                angle=float(row['deg']),
                thickness=float(row['thickness']),
                e_x=float(row['e_x']),
                e_y=float(row['e_y']),
                e_s=float(row['e_s']),
                v_x=float(row['v_x'])
            )
        return None
    
    def set_ply_value(self, row: int, column: str, value: Any):
        """Set a value for a specific ply and column."""
        if 0 <= row < len(self._df) and column in self._df.columns:
            self._df.at[row, column] = value
    
    def add_ply(self, ply_data: Optional[Dict[str, Any]] = None):
        """
        Add a new ply to the laminate.
        
        Args:
            ply_data: Optional dictionary with ply properties.
                     If None, uses default values.
        """
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
        if ply_data:
            defaults.update(ply_data)
        
        new_row = pd.DataFrame([defaults])
        self._df = pd.concat([self._df, new_row], ignore_index=True)
    
    def remove_ply(self, index: int):
        """Remove a ply by index."""
        if 0 <= index < len(self._df):
            self._df = self._df.drop(index).reset_index(drop=True)
    
    def validate_constraints(self) -> Dict[str, bool]:
        """
        Validate the laminate against configured constraints.
        
        Composite Engineering Note:
            Constraint validation ensures the laminate design meets
            manufacturing and structural requirements. Symmetry ensures
            no warping under thermal loads, while balance prevents
            extension-shear coupling.
        
        Returns:
            Dictionary with constraint names and their pass/fail status.
        """
        results = {}
        
        # Thickness constraint
        results['thickness_valid'] = self.total_thickness <= self._config.max_total_thickness
        
        # Symmetry check (if required)
        if self._config.symmetry_required:
            results['symmetry_valid'] = self._check_symmetry()
        else:
            results['symmetry_valid'] = True
        
        # Balance check (if required)
        if self._config.balanced_required:
            results['balance_valid'] = self._check_balance()
        else:
            results['balance_valid'] = True
        
        return results
    
    def _check_symmetry(self) -> bool:
        """
        Check if the layup is symmetric about the midplane.
        
        Composite Engineering Note:
            A symmetric laminate has plies mirrored about the midplane.
            This eliminates the B-matrix (coupling stiffness), preventing
            warping during cure and simplifying analysis.
        """
        if len(self._df) == 0:
            return True
        
        n = len(self._df)
        for i in range(n // 2):
            if self._df.iloc[i]['deg'] != self._df.iloc[n - 1 - i]['deg']:
                return False
        return True
    
    def _check_balance(self) -> bool:
        """
        Check if the layup is balanced (equal +θ and -θ plies).
        
        Composite Engineering Note:
            A balanced laminate has equal numbers of +θ and -θ plies,
            eliminating extension-shear coupling (A16 = A26 = 0).
        """
        if len(self._df) == 0:
            return True
        
        angles = self._df['deg'].values
        # Exclude 0 and 90 degree plies (they don't need balance)
        non_zero_angles = angles[np.abs(angles) > ANGLE_TOLERANCE_DEG]
        non_zero_angles = non_zero_angles[np.abs(np.abs(non_zero_angles) - 90) > ANGLE_TOLERANCE_DEG]
        
        # Count positive and negative angles
        for angle in np.unique(np.abs(non_zero_angles)):
            pos_count = np.sum(np.isclose(non_zero_angles, angle, atol=ANGLE_TOLERANCE_DEG))
            neg_count = np.sum(np.isclose(non_zero_angles, -angle, atol=ANGLE_TOLERANCE_DEG))
            if pos_count != neg_count:
                return False
        return True
    
    @classmethod
    def from_excel(cls, filepath: str) -> 'LaminateModel':
        """
        Load laminate data from an Excel file.
        
        Args:
            filepath: Path to the Excel file.
        
        Returns:
            New LaminateModel instance with loaded data.
        """
        df = pd.read_excel(filepath)
        return cls(df)
    
    def to_excel(self, filepath: str):
        """
        Export laminate data to an Excel file.
        
        Args:
            filepath: Path for the output Excel file.
        """
        self._df.to_excel(filepath, index=False)
    
    def get_display_dataframe(self) -> pd.DataFrame:
        """
        Get a DataFrame formatted for UI display.
        
        Returns:
            DataFrame with human-readable column names and formatting.
        """
        display_df = pd.DataFrame()
        display_df['Ply Index'] = range(len(self._df))
        display_df['Material'] = self._df['material'].values
        display_df['Angle (°)'] = self._df['deg'].values
        display_df['Thickness (m)'] = self._df['thickness'].values
        display_df['E_x (Pa)'] = self._df['e_x'].values
        display_df['E_y (Pa)'] = self._df['e_y'].values
        display_df['E_s (Pa)'] = self._df['e_s'].values
        display_df['ν_x'] = self._df['v_x'].values
        return display_df
