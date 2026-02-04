# -*- coding: utf-8 -*-
"""
Laminate Optimizer - Demo/Fallback Genetic Algorithm

This module provides a standalone GA implementation that serves as a
fallback when the user's GA code is not available. It implements
the core optimization logic for composite laminate design.

Composite Engineering Note:
    This GA uses binary encoding with discrete angle choices (0°, 45°, -45°, 90°).
    The symmetric constraint is enforced by optimizing only half the plies
    and mirroring them about the midplane.
"""

import math
import numpy as np
import pandas as pd
from typing import Callable, Optional, Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class GAResult:
    """Container for GA optimization results."""
    best_bits: np.ndarray
    best_fitness: float
    best_strains: np.ndarray
    best_full_angles: np.ndarray
    history: List[Tuple[int, float, float]]  # (generation, best_fitness, avg_fitness)
    non_core_indices: List[int]
    final_solution: Dict[str, Any]


class DemoGA:
    """
    Demo Genetic Algorithm for composite laminate optimization.
    
    Composite Engineering Note:
        The GA optimizes the fiber orientation angles to minimize
        the difference between computed and target strains under
        applied mechanical loads.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the demo GA with configuration.
        
        Args:
            config: Dictionary containing GA parameters.
        """
        self.pop_size = config.get('population_size', 200)
        self.n_generations = config.get('num_generations', 300)
        self.crossover_rate = config.get('crossover_rate', 0.9)
        self.mutation_rate = config.get('mutation_rate', 0.08)
        self.elitism = config.get('elitism_count', 2)
        self.tournament_k = config.get('tournament_size', 3)
        
        self.angle_set = np.array(config.get('angle_set', [0.0, 45.0, -45.0, 90.0]))
        self.bits_per_var = int(np.ceil(np.log2(len(self.angle_set))))
        
        self.target_strains = np.array(config.get('target_strains', 
                                                   [0.0287, -0.0085, 0.0, 0.0, 0.0, 0.0]))
        self.force_moment = np.array(config.get('force_moment', 
                                                 [2e6, 0.0, 0.0, 0.0, 0.0, 0.0]))
        self.fit_weights = np.array(config.get('fitness_weights', [1.0, 1.0, 0.0]))
        
        self.random_seed = config.get('random_seed', 42)
        self._stop_requested = False
    
    def request_stop(self):
        """Request the GA to stop execution."""
        self._stop_requested = True
    
    def _bits_to_angle_indices(self, bits: np.ndarray, n_vars: int) -> np.ndarray:
        """Convert binary bits to angle indices."""
        bits = np.asarray(bits, dtype=int).flatten()
        resh = bits.reshape(n_vars, self.bits_per_var)
        powers = 2 ** np.arange(self.bits_per_var - 1, -1, -1)
        idxs = (resh * powers).sum(axis=1)
        idxs = np.mod(idxs, len(self.angle_set))
        return idxs.astype(int)
    
    def _indices_to_angles(self, idxs: np.ndarray) -> np.ndarray:
        """Convert angle indices to actual angles."""
        return self.angle_set[idxs]
    
    def _make_symmetric_full_angles(self, half_angles: np.ndarray) -> np.ndarray:
        """Create symmetric full angle array from half angles."""
        return np.concatenate([half_angles, half_angles[::-1]])
    
    def _decode_bits_to_full_angles(self, bits: np.ndarray, n_half_vars: int) -> np.ndarray:
        """Decode binary bits to full symmetric angle array."""
        idxs = self._bits_to_angle_indices(bits, n_half_vars)
        half_angles = self._indices_to_angles(idxs)
        return self._make_symmetric_full_angles(half_angles)
    
    def _init_population(self, n_half_vars: int) -> List[np.ndarray]:
        """Initialize random population."""
        pop = []
        total_bits = n_half_vars * self.bits_per_var
        for _ in range(self.pop_size):
            bits = np.random.randint(0, 2, size=total_bits, dtype=int)
            pop.append(bits)
        return pop
    
    def _tournament_select(self, pop: List[np.ndarray], fitness: List[float]) -> np.ndarray:
        """Tournament selection."""
        idxs = np.random.choice(len(pop), size=self.tournament_k, replace=False)
        best = min(idxs, key=lambda i: fitness[i])
        return pop[best].copy()
    
    def _crossover(self, b1: np.ndarray, b2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Single-point crossover."""
        if np.random.rand() > self.crossover_rate:
            return b1.copy(), b2.copy()
        total = b1.size
        p = np.random.randint(1, total)
        c1 = np.concatenate([b1[:p], b2[p:]])
        c2 = np.concatenate([b2[:p], b1[p:]])
        return c1, c2
    
    def _mutate(self, bits: np.ndarray) -> np.ndarray:
        """Bit-flip mutation."""
        b = bits.copy()
        flips = np.random.rand(b.size) < self.mutation_rate
        b[flips] = 1 - b[flips]
        return b
    
    def _compute_strains(self, df: pd.DataFrame, force_vec: np.ndarray, 
                         override_degrees: Optional[List[float]] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute global strains using Classical Laminate Theory.
        
        Composite Engineering Note:
            This implements the ABD matrix formulation from CLT.
            The global strains and curvatures are computed by solving
            the constitutive equation [N; M] = [A B; B D] * [ε; κ].
        """
        df_work = df.copy()
        if override_degrees is not None:
            deg_iter = iter(override_degrees)
            for i, row in df_work.iterrows():
                if str(row['material']).lower() != 'core':
                    df_work.at[i, 'deg'] = float(next(deg_iter))
        
        h = float(df_work['thickness'].sum())
        z = -0.5 * h
        
        D_vec = np.zeros((6, 1))
        B_vec = np.zeros((6, 1))
        A_vec = np.zeros((6, 1))
        
        plies = []
        for _, row in df_work.iterrows():
            ply = self._create_ply(row, z)
            plies.append(ply)
            if str(row['material']).lower() != 'core':
                D_vec += self._D_element_vec(ply)
                B_vec += self._B_element_vec(ply)
                A_vec += self._A_element_vec(ply)
            z += float(row['thickness'])
        
        A = self._to_3x3(A_vec)
        B = self._to_3x3(B_vec)
        D = self._to_3x3(D_vec)
        
        FM = np.block([[A, B], [B, D]])
        f = np.array(force_vec, dtype=float).reshape(6, 1)
        
        try:
            ans = np.linalg.solve(FM, f)
        except np.linalg.LinAlgError:
            ans = np.linalg.pinv(FM).dot(f)
        
        ply_stress = []
        for ply in plies:
            ep_local = np.array([
                ans[0] + ans[3] * ply['zm'],
                ans[1] + ans[4] * ply['zm'],
                ans[2] + ans[5] * ply['zm']
            ]).reshape(3, 1)
            T = self._rotation_strain_positive(ply['deg'])
            eps_12 = T @ ep_local
            Q = self._q_maker(ply)
            sigma_12 = Q @ eps_12 * 1e-6
            ply_stress.append(sigma_12.flatten())
        
        return ans, np.array(ply_stress)
    
    def _create_ply(self, row: pd.Series, z: float) -> Dict[str, float]:
        """Create ply dictionary from row data."""
        ex = float(row['e_x'])
        ey = float(row['e_y'])
        es = float(row['e_s'])
        vx = float(row['v_x'])
        vy = vx * ey / ex
        m = 1.0 / (1.0 - vx * vy)
        t = float(row['thickness'])
        
        return {
            'ex': ex, 'ey': ey, 'es': es, 'vx': vx, 'vy': vy, 'm': m,
            'deg': float(row['deg']), 't': t,
            'z1': z, 'z2': z + t, 'zm': z + 0.5 * t
        }
    
    def _q_maker(self, ply: Dict[str, float]) -> np.ndarray:
        """Create on-axis Q matrix."""
        q_xx = ply['m'] * ply['ex']
        q_yy = ply['m'] * ply['ey']
        q_xy = ply['m'] * ply['vy'] * ply['ex']
        q_ss = ply['es']
        return np.array([
            [q_xx, q_xy, 0.0],
            [q_xy, q_yy, 0.0],
            [0.0, 0.0, q_ss]
        ])
    
    def _rotation_strain_positive(self, deg: float) -> np.ndarray:
        """Create strain rotation matrix."""
        th = math.radians(deg)
        c, s = math.cos(th), math.sin(th)
        return np.array([
            [c*c, s*s, c*s],
            [s*s, c*c, -c*s],
            [-2*c*s, 2*c*s, c*c - s*s]
        ])
    
    def _element_vector(self, ply: Dict[str, float], dz_factor: float) -> np.ndarray:
        """Compute element vector for ABD matrix."""
        qm = [ply['m'] * ply['ex'], ply['m'] * ply['ey'],
              ply['m'] * ply['vy'] * ply['ex'], ply['es']]
        
        u1 = 0.125 * (3*qm[0] + 3*qm[1] + 2*qm[2] + 4*qm[3])
        u2 = 0.5 * (qm[0] - qm[1])
        u3 = 0.125 * (qm[0] + qm[1] - 2*qm[2] - 4*qm[3])
        u4 = 0.125 * (qm[0] + qm[1] + 6*qm[2] - 4*qm[3])
        u5 = 0.125 * (qm[0] + qm[1] - 2*qm[2] + 4*qm[3])
        um = [u1, u2, u3, u4, u5]
        
        th = math.radians(ply['deg'])
        c2, s2 = math.cos(2*th), math.sin(2*th)
        c4, s4 = math.cos(4*th), math.sin(4*th)
        
        aa1 = np.array([
            [um[0], c2, c4],
            [um[0], -c2, c4],
            [um[3], 0.0, -c4],
            [um[4], 0.0, -c4],
            [0.0, 0.5*s2, s4],
            [0.0, 0.5*s2, -s4]
        ])
        aa2 = np.array([[1.0], [um[1]], [um[2]]])
        return np.dot(aa1, aa2) * dz_factor
    
    def _A_element_vec(self, ply: Dict[str, float]) -> np.ndarray:
        return self._element_vector(ply, ply['z2'] - ply['z1'])
    
    def _B_element_vec(self, ply: Dict[str, float]) -> np.ndarray:
        return 0.5 * self._element_vector(ply, ply['z2']**2 - ply['z1']**2)
    
    def _D_element_vec(self, ply: Dict[str, float]) -> np.ndarray:
        return (1.0/3.0) * self._element_vector(ply, ply['z2']**3 - ply['z1']**3)
    
    def _to_3x3(self, vec6: np.ndarray) -> np.ndarray:
        """Convert 6x1 vector to symmetric 3x3 matrix."""
        v = vec6.flatten()
        M = np.zeros((3, 3))
        M[0, 0] = v[0]
        M[1, 1] = v[1]
        M[0, 1] = M[1, 0] = v[2]
        M[2, 2] = v[3]
        M[0, 2] = M[2, 0] = v[4]
        M[1, 2] = M[2, 1] = v[5]
        return M
    
    def _evaluate_candidate(self, df: pd.DataFrame, bits: np.ndarray, 
                            non_core_indices: List[int]) -> Tuple[float, np.ndarray, np.ndarray]:
        """Evaluate a candidate solution."""
        n_half_vars = len(non_core_indices) // 2
        full_angles = self._decode_bits_to_full_angles(bits, n_half_vars)
        
        override = [float(a) for a in full_angles]
        calc_strains, _ = self._compute_strains(df, self.force_moment, override)
        
        calc = calc_strains.flatten()[:3]
        targ = self.target_strains.flatten()[:3]
        diff = calc - targ
        fitness_val = float(np.dot(self.fit_weights * diff, self.fit_weights * diff))
        fitness_val += 1e-8 * np.sum(bits.astype(float))
        
        return fitness_val, calc_strains, full_angles
    
    def run(self, df: pd.DataFrame, 
            progress_callback: Optional[Callable[[int, float, float], None]] = None) -> GAResult:
        """
        Run the genetic algorithm optimization.
        
        Args:
            df: DataFrame containing laminate ply data.
            progress_callback: Optional callback for progress updates.
                              Called with (generation, best_fitness, avg_fitness).
        
        Returns:
            GAResult containing the optimization results.
        
        Composite Engineering Note:
            The GA evolves the population through selection, crossover,
            and mutation to find the optimal fiber orientation angles
            that minimize the strain error objective.
        """
        self._stop_requested = False
        
        if self.random_seed is not None:
            np.random.seed(self.random_seed)
        
        non_core_indices = [i for i, row in df.iterrows() 
                           if str(row['material']).lower() != 'core']
        n_plies = len(non_core_indices)
        
        if n_plies == 0:
            raise ValueError("No optimizable plies found (all are 'core').")
        if n_plies % 2 != 0:
            raise ValueError("Number of non-core plies must be even for symmetric optimization.")
        
        n_half_vars = n_plies // 2
        pop = self._init_population(n_half_vars)
        cache = {}
        
        # Evaluate initial population
        fitness = []
        for bits in pop:
            key = tuple(bits.tolist())
            if key not in cache:
                fit, strains, angles = self._evaluate_candidate(df, bits, non_core_indices)
                cache[key] = (fit, strains, angles)
            fitness.append(cache[key][0])
        
        best_idx = int(np.argmin(fitness))
        best_bits = pop[best_idx].copy()
        best_fit = fitness[best_idx]
        best_strains = cache[tuple(best_bits.tolist())][1]
        best_full_angles = cache[tuple(best_bits.tolist())][2]
        
        avg_fit = np.mean(fitness)
        history = [(0, best_fit, avg_fit)]
        
        if progress_callback:
            progress_callback(0, best_fit, avg_fit)
        
        # Main GA loop
        for gen in range(1, self.n_generations + 1):
            if self._stop_requested:
                break
            
            elite_idxs = np.argsort(fitness)[:self.elitism]
            elites = [pop[i].copy() for i in elite_idxs]
            
            new_pop = []
            while len(new_pop) < self.pop_size - self.elitism:
                p1 = self._tournament_select(pop, fitness)
                p2 = self._tournament_select(pop, fitness)
                c1, c2 = self._crossover(p1, p2)
                c1 = self._mutate(c1)
                c2 = self._mutate(c2)
                new_pop.extend([c1, c2])
            
            new_pop = new_pop[:self.pop_size - self.elitism]
            new_pop.extend(elites)
            pop = new_pop
            
            fitness = []
            for bits in pop:
                key = tuple(bits.tolist())
                if key not in cache:
                    fit, strains, angles = self._evaluate_candidate(df, bits, non_core_indices)
                    cache[key] = (fit, strains, angles)
                fitness.append(cache[key][0])
            
            idx = int(np.argmin(fitness))
            if fitness[idx] < best_fit:
                best_fit = fitness[idx]
                best_bits = pop[idx].copy()
                best_strains = cache[tuple(best_bits.tolist())][1]
                best_full_angles = cache[tuple(best_bits.tolist())][2]
            
            avg_fit = np.mean(fitness)
            history.append((gen, best_fit, avg_fit))
            
            if progress_callback:
                progress_callback(gen, best_fit, avg_fit)
        
        final_solution = {
            'best_angles': list(best_full_angles),
            'best_fitness': best_fit,
            'best_strains': best_strains.flatten().tolist(),
            'total_thickness': float(df['thickness'].sum()),
            'generations_run': len(history) - 1,
            'was_stopped': self._stop_requested
        }
        
        return GAResult(
            best_bits=best_bits,
            best_fitness=best_fit,
            best_strains=best_strains,
            best_full_angles=best_full_angles,
            history=history,
            non_core_indices=non_core_indices,
            final_solution=final_solution
        )
