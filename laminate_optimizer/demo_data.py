# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Demo Data Generator

This module provides demo data for testing the application when
the user's Excel data is not available.

Composite Engineering Note:
    The demo data represents a typical 8-ply symmetric laminate
    using T300/5208 carbon fiber/epoxy material, which is commonly
    used in aerospace and automotive applications.
"""

import pandas as pd
import numpy as np


def create_demo_layup_data() -> pd.DataFrame:
    """
    Create a demonstration laminate layup dataset.
    
    Composite Engineering Note:
        This creates an 8-ply symmetric layup with quasi-isotropic
        properties using the common T300/5208 carbon/epoxy system.
        The ply thickness of 0.125mm is typical for aerospace prepregs.
    
    Returns:
        pandas DataFrame with laminate ply data.
    """
    # T300/5208 carbon/epoxy material properties
    material = 'T300/5208'
    e_x = 181e9       # Longitudinal modulus (Pa)
    e_y = 10.3e9      # Transverse modulus (Pa)
    e_s = 7.17e9      # Shear modulus (Pa)
    v_x = 0.28        # Poisson's ratio
    thickness = 0.000125  # Ply thickness (m) = 0.125 mm
    
    # 8-ply symmetric quasi-isotropic layup [0/45/-45/90]s
    angles = [0, 45, -45, 90, 90, -45, 45, 0]
    
    data = []
    for i, angle in enumerate(angles):
        data.append({
            'material': material,
            'deg': float(angle),
            'num': 1,
            't': thickness,
            'thickness': thickness,
            'e_x': e_x,
            'e_y': e_y,
            'e_s': e_s,
            'v_x': v_x
        })
    
    return pd.DataFrame(data)


def create_demo_config() -> dict:
    """
    Create default GA configuration settings.
    
    Composite Engineering Note:
        These default parameters are tuned for typical laminate
        optimization problems. The population size of 200 and 
        300 generations provide a good balance between solution
        quality and computation time.
    
    Returns:
        Dictionary with GA configuration parameters.
    """
    return {
        'population_size': 200,
        'num_generations': 300,
        'crossover_rate': 0.9,
        'mutation_rate': 0.08,
        'elitism_count': 2,
        'selection_method': 'tournament',
        'tournament_size': 3,
        'max_total_thickness': 0.01,  # 10mm
        'symmetry_required': True,
        'balanced_required': False,
        'target_strains': [0.0287, -0.0085, 0.0, 0.0, 0.0, 0.0],
        'force_moment': [2e6, 0.0, 0.0, 0.0, 0.0, 0.0],
        'fitness_weights': [1.0, 1.0, 0.0],
        'angle_set': [0.0, 45.0, -45.0, 90.0],
        'random_seed': 42
    }


def get_material_database() -> dict:
    """
    Get a dictionary of common composite materials and their properties.
    
    Composite Engineering Note:
        These are typical unidirectional lamina properties for
        various fiber/matrix systems used in industry.
    
    Returns:
        Dictionary mapping material names to property dictionaries.
    """
    return {
        'T300/5208': {
            'description': 'Carbon/Epoxy (Aerospace Grade)',
            'e_x': 181e9,
            'e_y': 10.3e9,
            'e_s': 7.17e9,
            'v_x': 0.28,
            'density': 1600,  # kg/m³
            'typical_thickness': 0.000125  # m
        },
        'AS4/3501-6': {
            'description': 'Carbon/Epoxy (High Performance)',
            'e_x': 142e9,
            'e_y': 10.3e9,
            'e_s': 7.2e9,
            'v_x': 0.27,
            'density': 1580,
            'typical_thickness': 0.000140
        },
        'IM7/8552': {
            'description': 'Carbon/Epoxy (Intermediate Modulus)',
            'e_x': 165e9,
            'e_y': 8.4e9,
            'e_s': 5.6e9,
            'v_x': 0.34,
            'density': 1590,
            'typical_thickness': 0.000131
        },
        'S-Glass/Epoxy': {
            'description': 'Glass/Epoxy (High Strength)',
            'e_x': 43e9,
            'e_y': 8.9e9,
            'e_s': 4.5e9,
            'v_x': 0.27,
            'density': 2000,
            'typical_thickness': 0.000150
        },
        'E-Glass/Epoxy': {
            'description': 'Glass/Epoxy (General Purpose)',
            'e_x': 38.6e9,
            'e_y': 8.27e9,
            'e_s': 4.14e9,
            'v_x': 0.26,
            'density': 1970,
            'typical_thickness': 0.000150
        },
        'Kevlar-49/Epoxy': {
            'description': 'Aramid/Epoxy (Impact Resistant)',
            'e_x': 80e9,
            'e_y': 5.5e9,
            'e_s': 2.2e9,
            'v_x': 0.34,
            'density': 1380,
            'typical_thickness': 0.000125
        }
    }


def get_angle_presets() -> dict:
    """
    Get common angle orientation presets for laminate design.
    
    Composite Engineering Note:
        These presets represent commonly used layup configurations
        in composite design. The 0°, ±45°, 90° system is particularly
        popular because it provides quasi-isotropic behavior.
    
    Returns:
        Dictionary mapping preset names to angle lists.
    """
    return {
        'Standard (0/±45/90)': [0.0, 45.0, -45.0, 90.0],
        'Extended (0/±30/±45/±60/90)': [0.0, 30.0, -30.0, 45.0, -45.0, 60.0, -60.0, 90.0],
        'Fine (0/±15/±30/±45/±60/±75/90)': [0.0, 15.0, -15.0, 30.0, -30.0, 45.0, -45.0, 
                                            60.0, -60.0, 75.0, -75.0, 90.0],
        'Binary (0/90)': [0.0, 90.0],
        'Cross-ply': [0.0, 90.0],
        'Angle-ply (±45)': [45.0, -45.0]
    }
