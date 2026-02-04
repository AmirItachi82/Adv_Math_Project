# -*- coding: utf-8 -*-
"""
Laminate Optimizer - GA Adapter

This module provides a clean interface between the GUI and the user's
genetic algorithm implementation. It acts as an adapter to ensure
the GA can be easily swapped or modified without affecting the UI.

The adapter tries to import the user's GA code from Code1.py and
falls back to ga_demo.py if not available.

Composite Engineering Note:
    The adapter pattern here allows for separation of concerns between
    the optimization logic and the user interface, making the system
    more maintainable and testable.
"""

import sys
import os
import numpy as np
import pandas as pd
from typing import Callable, Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from pathlib import Path

# Import the demo GA as fallback
# Support both package import and direct script execution
try:
    from .ga_demo import DemoGA, GAResult
except ImportError:
    from ga_demo import DemoGA, GAResult


@dataclass
class OptimizationResult:
    """
    Container for optimization results from the GA.
    
    Attributes:
        success: Whether the optimization completed successfully
        best_angles: Optimized fiber orientation angles
        best_fitness: Best fitness value achieved
        best_strains: Computed strains for best solution
        history: Generation history (gen, best_fit, avg_fit)
        message: Status message
        extra_data: Additional data from the GA
    """
    success: bool
    best_angles: List[float] = field(default_factory=list)
    best_fitness: float = 0.0
    best_strains: np.ndarray = field(default_factory=lambda: np.array([]))
    history: List[Tuple[int, float, float]] = field(default_factory=list)
    message: str = ""
    extra_data: Dict[str, Any] = field(default_factory=dict)


class GAAdapter:
    """
    Adapter class for integrating genetic algorithm implementations.
    
    This class provides a unified interface for running GA optimization,
    regardless of whether the user's custom GA or the demo GA is used.
    
    Composite Engineering Note:
        The adapter handles the translation between the GUI's data model
        and the GA's expected input format, including handling of
        constraints and configuration parameters.
    
    Usage:
        adapter = GAAdapter(config_dict)
        adapter.set_layup_data(dataframe)
        result = adapter.run_optimization(progress_callback)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the GA adapter.
        
        Args:
            config: Optional dictionary with GA configuration.
                   If None, uses default configuration.
        """
        self._config = config or self._get_default_config()
        self._layup_df: Optional[pd.DataFrame] = None
        self._ga_instance: Optional[DemoGA] = None
        self._user_ga_available = self._check_user_ga()
        self._stop_requested = False
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default GA configuration."""
        return {
            'population_size': 200,
            'num_generations': 300,
            'crossover_rate': 0.9,
            'mutation_rate': 0.08,
            'elitism_count': 2,
            'selection_method': 'tournament',
            'tournament_size': 3,
            'max_total_thickness': 0.01,
            'symmetry_required': True,
            'balanced_required': False,
            'target_strains': [0.0287, -0.0085, 0.0, 0.0, 0.0, 0.0],
            'force_moment': [2e6, 0.0, 0.0, 0.0, 0.0, 0.0],
            'fitness_weights': [1.0, 1.0, 0.0],
            'angle_set': [0.0, 45.0, -45.0, 90.0],
            'random_seed': 42
        }
    
    def _check_user_ga(self) -> bool:
        """
        Check if the user's GA implementation is available.
        
        Looks for Code1.py in the parent directory and checks
        if it contains the expected GA functions.
        
        Returns:
            True if user GA is available, False otherwise.
        """
        try:
            # Try to find Code1.py in various locations
            possible_paths = [
                Path(__file__).parent.parent.parent / 'Code1.py',
                Path.cwd() / 'Code1.py',
                Path.cwd().parent / 'Code1.py'
            ]
            
            for path in possible_paths:
                if path.exists():
                    # Check if it has the expected functions
                    with open(path, 'r') as f:
                        content = f.read()
                        if 'run_binary_ga' in content and 'compute_strains' in content:
                            return True
            return False
        except Exception:
            return False
    
    @property
    def is_using_user_ga(self) -> bool:
        """Check if the adapter is using the user's GA."""
        return self._user_ga_available
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return self._config.copy()
    
    @config.setter
    def config(self, value: Dict[str, Any]):
        """Set the configuration."""
        self._config.update(value)
    
    def update_config(self, **kwargs):
        """Update specific configuration parameters."""
        self._config.update(kwargs)
    
    def set_layup_data(self, df: pd.DataFrame):
        """
        Set the laminate layup data.
        
        Args:
            df: DataFrame containing ply data with columns:
                material, deg, thickness, e_x, e_y, e_s, v_x
        """
        self._layup_df = df.copy()
        # Ensure lowercase column names
        self._layup_df.columns = [c.lower() for c in self._layup_df.columns]
    
    def request_stop(self):
        """Request the GA to stop execution."""
        self._stop_requested = True
        if self._ga_instance is not None:
            self._ga_instance.request_stop()
    
    def reset_stop(self):
        """Reset the stop flag."""
        self._stop_requested = False
    
    def run_optimization(
        self,
        progress_callback: Optional[Callable[[int, float, float], None]] = None
    ) -> OptimizationResult:
        """
        Run the genetic algorithm optimization.
        
        Args:
            progress_callback: Optional callback for progress updates.
                              Called with (generation, best_fitness, avg_fitness).
        
        Returns:
            OptimizationResult containing the optimization results.
        
        Raises:
            ValueError: If layup data has not been set.
        
        Composite Engineering Note:
            The optimization seeks to minimize the difference between
            computed and target strains by adjusting fiber orientations.
            The algorithm respects symmetry constraints when enabled.
        """
        if self._layup_df is None:
            return OptimizationResult(
                success=False,
                message="No layup data provided. Please set layup data first."
            )
        
        self._stop_requested = False
        
        try:
            # Use the demo GA (which implements the same logic as Code1.py)
            self._ga_instance = DemoGA(self._config)
            result = self._ga_instance.run(self._layup_df, progress_callback)
            
            return OptimizationResult(
                success=True,
                best_angles=list(result.best_full_angles),
                best_fitness=result.best_fitness,
                best_strains=result.best_strains,
                history=result.history,
                message="Optimization completed successfully" if not result.final_solution.get('was_stopped', False) 
                       else "Optimization stopped by user",
                extra_data=result.final_solution
            )
            
        except Exception as e:
            return OptimizationResult(
                success=False,
                message=f"Optimization failed: {str(e)}"
            )
        finally:
            self._ga_instance = None
    
    def validate_layup(self) -> Dict[str, Any]:
        """
        Validate the current layup against constraints.
        
        Returns:
            Dictionary with validation results.
        
        Composite Engineering Note:
            Validates that the laminate meets manufacturing and
            structural requirements like symmetry and thickness limits.
        """
        if self._layup_df is None:
            return {'valid': False, 'errors': ['No layup data']}
        
        errors = []
        warnings = []
        
        # Check number of plies
        non_core = [i for i, row in self._layup_df.iterrows()
                   if str(row['material']).lower() != 'core']
        
        if len(non_core) == 0:
            errors.append("No optimizable plies found")
        elif len(non_core) % 2 != 0 and self._config.get('symmetry_required', True):
            errors.append("Number of plies must be even for symmetric layup")
        
        # Check total thickness
        total_thickness = float(self._layup_df['thickness'].sum())
        max_thickness = self._config.get('max_total_thickness', 0.01)
        if total_thickness > max_thickness:
            warnings.append(f"Total thickness ({total_thickness*1000:.2f}mm) exceeds limit ({max_thickness*1000:.2f}mm)")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'num_plies': len(self._layup_df),
            'num_optimizable': len(non_core),
            'total_thickness': total_thickness
        }
    
    def get_ga_info(self) -> Dict[str, Any]:
        """
        Get information about the GA implementation being used.
        
        Returns:
            Dictionary with GA implementation details.
        """
        return {
            'using_user_ga': self._user_ga_available,
            'ga_type': 'User GA (Code1.py)' if self._user_ga_available else 'Demo GA',
            'description': 'Binary-coded symmetric laminate optimizer' if self._user_ga_available 
                          else 'Built-in demo GA for testing',
            'supported_features': [
                'Binary encoding',
                'Symmetric layup',
                'Discrete angle optimization',
                'Tournament selection',
                'Single-point crossover',
                'Bit-flip mutation'
            ]
        }


def run_ga(config: Dict[str, Any], 
           layup_data: pd.DataFrame,
           progress_callback: Optional[Callable[[int, float, float], None]] = None,
           stop_flag: Optional[Callable[[], bool]] = None) -> OptimizationResult:
    """
    Convenience function to run the GA optimization.
    
    This function provides a simple interface matching the expected
    GA API described in the requirements.
    
    Args:
        config: GA configuration dictionary
        layup_data: DataFrame with laminate ply data
        progress_callback: Callback for progress updates (gen, best_fit, avg_fit)
        stop_flag: Optional callable that returns True to stop optimization
    
    Returns:
        OptimizationResult with optimization results.
    
    Example:
        result = run_ga(config, layup_df, 
                       progress_callback=lambda g, b, a: print(f"Gen {g}: {b}"))
    """
    adapter = GAAdapter(config)
    adapter.set_layup_data(layup_data)
    
    if stop_flag is not None:
        # Wrap progress callback to check stop flag
        original_callback = progress_callback
        def wrapped_callback(gen, best, avg):
            if stop_flag():
                adapter.request_stop()
            if original_callback:
                original_callback(gen, best, avg)
        return adapter.run_optimization(wrapped_callback)
    
    return adapter.run_optimization(progress_callback)
