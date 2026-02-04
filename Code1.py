# -*- coding: utf-8 -*-
"""
Symmetric 8-ply laminate optimizer using a binary-coded GA over discrete angles.
- Discrete angle set: [0, 45, -45, 90]
- Binary encoding: 2 bits per independent ply (4 choices)
- Only first 3 in-plane strains are used in fitness (εx, εy, γxy)
- Symmetry enforced: optimize half the plies and mirror them
- Stable ABD solve: np.linalg.solve with fallback to pseudo-inverse
"""

import math
import numpy as np
import pandas as pd

# -------------------- User settings --------------------
EXCEL_PATH = "layup.xlsx"

# Applied forces/moments vector: [Nx, Ny, Nxy, Mx, My, Mxy]
FORCE_MOMENT = np.array([2e6, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=float)

# Target strains (6x1): [εx, εy, γxy, κx, κy, κxy] (κ are optional)
TARGET_STRAINS = np.array([0.0287, -0.0085, 0.0, 0.0, 0.0, 0.0], dtype=float).reshape(6, 1)

# GA hyperparameters
POP_SIZE = 200
N_GENERATIONS = 300
TOURNEY_K = 3
CROSSOVER_RATE = 0.9   # probability to perform crossover
MUTATION_RATE = 0.08   # probability to flip each bit (per-bit mutation)
ELITISM = 2
EARLY_STOP_TOL = 0.0

# Angle discretization and binary encoding
ANGLE_SET = np.array([0.0, 45.0, -45.0, 90.0], dtype=float)
BITS_PER_VAR = int(np.ceil(np.log2(len(ANGLE_SET))))  # 2 bits for 4 choices

# Fitness weights for first 3 strains (εx, εy, γxy)
FIT_WEIGHTS = np.array([1.0, 1.0, 0], dtype=float)

# Random seed for reproducibility (set to None for non-deterministic runs)
RANDOM_SEED = 42

# -------------------- Composite classes and helpers --------------------
class Ply:
    """
    Ply mechanical properties holder and small helpers.
    All thickness units are meters (as requested).
    """
    def __init__(self, e_x, e_y, e_s, v_x, deg, thickness, z):
        self.ex = float(e_x)
        self.ey = float(e_y)
        self.es = float(e_s)
        self.vx = float(v_x)
        # orthotropic plane stress relations
        self.vy = self.vx * self.ey / self.ex
        self.m = 1.0 / (1.0 - (self.vx * self.vy))
        self.deg = float(deg)
        self.t = float(thickness)
        self.z1 = float(z)
        self.z2 = self.z1 + self.t
        self.zm = self.z1 + 0.5 * self.t

    def dz3(self): return (self.z2 ** 3) - (self.z1 ** 3)
    def dz2(self): return (self.z2 ** 2) - (self.z1 ** 2)
    def dz1(self): return self.z2 - self.z1

    def rotation_strain_positive(self):
        """Transform global strains to local fiber coordinates (strain transform)."""
        th = math.radians(self.deg)
        c = math.cos(th)
        s = math.sin(th)
        return np.array([
            [c*c,     s*s,     c*s],
            [s*s,     c*c,    -c*s],
            [-2*c*s,  2*c*s, (c*c - s*s)]
        ], dtype=float)

    def q_maker(self):
        """On-axis Q matrix (plane stress)"""
        q_xx = self.m * self.ex
        q_yy = self.m * self.ey
        q_xy = self.m * self.vy * self.ex
        q_ss = self.es
        return np.array([
            [q_xx, q_xy, 0.0],
            [q_xy, q_yy, 0.0],
            [0.0,  0.0,  q_ss]
        ], dtype=float)

    def q_calculator(self):
        q_xx = self.m * self.ex
        q_yy = self.m * self.ey
        q_xy = self.m * self.vy * self.ex
        q_ss = self.es
        return [q_xx, q_yy, q_xy, q_ss]

    @staticmethod
    def u_calculator(qm):
        q_xx, q_yy, q_xy, q_ss = qm
        u1 = 0.125 * (3*q_xx + 3*q_yy + 2*q_xy + 4*q_ss)
        u2 = 0.5   * (q_xx - q_yy)
        u3 = 0.125 * (q_xx + q_yy - 2*q_xy - 4*q_ss)
        u4 = 0.125 * (q_xx + q_yy + 6*q_xy - 4*q_ss)
        u5 = 0.125 * (q_xx + q_yy - 2*q_xy + 4*q_ss)
        return [u1, u2, u3, u4, u5]

    def _element_vector(self, dz_factor):
        um = Ply.u_calculator(self.q_calculator())
        th = math.radians(self.deg)
        c2 = math.cos(2*th)
        s2 = math.sin(2*th)
        c4 = math.cos(4*th)
        s4 = math.sin(4*th)
        aa1 = np.array([
            [um[0],  c2,  c4],
            [um[0], -c2,  c4],
            [um[3],  0.0, -c4],
            [um[4],  0.0, -c4],
            [0.0,  0.5*s2,  s4],
            [0.0,  0.5*s2, -s4]
        ], dtype=float)
        aa2 = np.array([[1.0], [um[1]], [um[2]]], dtype=float)
        return np.dot(aa1, aa2) * dz_factor

    def A_element_vec(self): return self._element_vector(self.dz1())
    def B_element_vec(self): return 0.5 * self._element_vector(self.dz2())
    def D_element_vec(self): return (1.0/3.0) * self._element_vector(self.dz3())


class ABDAssembler:
    """Helper to convert 6x1 vectors to 3x3 A, B, D matrices."""
    def __init__(self, D_vec, A_vec, B_vec):
        self.d = D_vec
        self.a = A_vec
        self.b = B_vec

    @staticmethod
    def _to_3x3(vec6):
        v = vec6.flatten()
        M = np.zeros((3,3), dtype=float)
        M[0,0] = v[0]
        M[1,1] = v[1]
        M[0,1] = v[2]
        M[1,0] = v[2]
        M[2,2] = v[3]
        M[0,2] = v[4]
        M[2,0] = v[4]
        M[1,2] = v[5]
        M[2,1] = v[5]
        return M

    def D_matrix(self): return ABDAssembler._to_3x3(self.d)
    def A_matrix(self): return ABDAssembler._to_3x3(self.a)
    def B_matrix(self): return ABDAssembler._to_3x3(self.b)


# -------------------- Strain computation --------------------
def compute_strains(df, force_vec, override_degrees=None):
    """
    Compute global mid-plane strains and curvatures and local ply stresses.
    - df: pandas DataFrame containing ply rows (columns: material,e_x,e_y,e_s,v_x,deg,thickness)
    - force_vec: 6x1 vector [Nx, Ny, Nxy, Mx, My, Mxy]
    - override_degrees: list of degrees for non-core plies (in df order)
    Returns:
      ans: 6x1 [εx, εy, γxy, κx, κy, κxy] with κ in 1/m
      ply_stress: n_plies x 3 array of local stresses (in MPa — because of *1e-6)
    """
    if override_degrees is not None:
        df = df.copy()
        deg_iter = iter(override_degrees)
        for i, row in df.iterrows():
            if str(row['material']).lower() != 'core':
                df.at[i, 'deg'] = float(next(deg_iter))

    h = float(df['thickness'].sum())   # total thickness in meters
    z = -0.5 * h

    D_vec = np.zeros((6,1), dtype=float)
    B_vec = np.zeros((6,1), dtype=float)
    A_vec = np.zeros((6,1), dtype=float)

    plies = []
    for _, row in df.iterrows():
        ply = Ply(row['e_x'], row['e_y'], row['e_s'], row['v_x'],
                  row['deg'], row['thickness'], z)
        plies.append(ply)
        if str(row['material']).lower() != 'core':
            D_vec += ply.D_element_vec()
            B_vec += ply.B_element_vec()
            A_vec += ply.A_element_vec()
        z += float(row['thickness'])

    abd = ABDAssembler(D_vec, A_vec, B_vec)
    A = abd.A_matrix()
    B = abd.B_matrix()
    D = abd.D_matrix()

    FM = np.block([[A, B],
                   [B, D]])
    f = np.array(force_vec, dtype=float).reshape(6,1)

    # Solve robustly: try solve, fallback to pseudo-inverse
    try:
        ans = np.linalg.solve(FM, f)
    except np.linalg.LinAlgError:
        ans = np.linalg.pinv(FM).dot(f)

    # NOTE: Do NOT change units on ans. κ are in 1/m and z in meters.
    ply_stress = []
    for ply in plies:
        ep_local = np.array([
            ans[0] + ans[3] * ply.zm,
            ans[1] + ans[4] * ply.zm,
            ans[2] + ans[5] * ply.zm
        ], dtype=float).reshape(3,1)

        T = ply.rotation_strain_positive()
        eps_12 = T @ ep_local
        Q = ply.q_maker()

        # Multiply by 1e-6 to express stress in MPa for readability (original code used this).
        sigma_12 = Q @ eps_12 * (10.0 ** -6)
        ply_stress.append(sigma_12.flatten())
    ply_stress = np.array(ply_stress)
    return ans, ply_stress


# -------------------- Symmetry and binary encoding helpers --------------------
def make_symmetric_full_angles(half_angles):
    """
    Given half_angles = [θ1, θ2, ..., θn_half], return symmetric full list:
      [θ1 ... θ_n_half, θ_n_half ... θ2, θ1]
    """
    return np.concatenate([half_angles, half_angles[::-1]])


def bits_to_angle_indices(bits, n_vars):
    """
    Convert a 1D bits array (length = n_vars * BITS_PER_VAR) to
    integer indices into ANGLE_SET for each variable.
    bits interpreted MSB -> LSB per variable chunk (leftmost bit is highest place).
    """
    bits = np.asarray(bits, dtype=int).flatten()
    if bits.size != n_vars * BITS_PER_VAR:
        raise ValueError(f"bits length must be {n_vars*BITS_PER_VAR}, got {bits.size}")
    resh = bits.reshape(n_vars, BITS_PER_VAR)
    # binary to integer (MSB first)
    powers = (2 ** np.arange(BITS_PER_VAR - 1, -1, -1))
    idxs = (resh * powers).sum(axis=1)
    # wrap or clip if index >= len(ANGLE_SET)
    idxs = np.mod(idxs, len(ANGLE_SET))
    return idxs.astype(int)


def indices_to_angles(idxs):
    return ANGLE_SET[idxs]


def decode_bits_to_full_angles(bits, n_half_vars):
    """
    Convert bits -> half angles -> full symmetric angles (length = 2*n_half_vars).
    """
    idxs = bits_to_angle_indices(bits, n_half_vars)
    half_angles = indices_to_angles(idxs)
    full = make_symmetric_full_angles(half_angles)
    return full


# -------------------- GA (binary) --------------------
def init_population_binary(n_half_vars):
    """Initialize population of binary chromosomes as 1D bit arrays."""
    pop = []
    total_bits = n_half_vars * BITS_PER_VAR
    for _ in range(POP_SIZE):
        bits = np.random.randint(0, 2, size=total_bits, dtype=int)
        pop.append(bits)
    return pop


def tournament_select(pop, fitness, k=TOURNEY_K):
    idxs = np.random.choice(len(pop), size=k, replace=False)
    best = min(idxs, key=lambda i: fitness[i])
    return pop[best].copy()


def single_point_crossover_bits(b1, b2):
    """Single-point crossover on bit arrays with CROSSOVER_RATE probability."""
    if np.random.rand() > CROSSOVER_RATE:
        return b1.copy(), b2.copy()
    total = b1.size
    p = np.random.randint(1, total)  # crossover point (1..total-1)
    c1 = np.concatenate([b1[:p], b2[p:]])
    c2 = np.concatenate([b2[:p], b1[p:]])
    return c1, c2


def mutate_bits(bits):
    """
    Bit-flip mutation: each bit has MUTATION_RATE probability to flip.
    Return a copy (not in-place).
    """
    b = bits.copy()
    flips = np.random.rand(b.size) < MUTATION_RATE
    b[flips] = 1 - b[flips]
    return b


def evaluate_bits_candidate(df, force_vec, bits, target_strains, non_core_indices):
    """
    Decode bits to symmetric full angles, apply to non_core_indices in df,
    compute strains, and return fitness (SSE on first 3 strain components) + strains.
    """
    n_half_vars = len(non_core_indices) // 2
    # decode to full angles for the half variables
    full_angles = decode_bits_to_full_angles(bits, n_half_vars)

    # build override list for all non-core plies (in df order)
    override = []
    # non_core_indices order must match the physical ply order in df
    for i in range(len(non_core_indices)):
        override.append(float(full_angles[i]))

    calc_strains, _ = compute_strains(df, force_vec, override_degrees=override)

    calc = calc_strains.flatten()[:3]
    targ = target_strains.flatten()[:3]
    diff = calc - targ
    fitness_val = float(np.dot(FIT_WEIGHTS * diff, FIT_WEIGHTS * diff))

    # tiny regularizer to avoid extreme bit patterns (optional)
    fitness_val += 1e-8 * np.sum(bits.astype(float))

    return fitness_val, calc_strains, full_angles


def run_binary_ga(df, force_vec, target_strains, random_seed=None):
    if random_seed is not None:
        np.random.seed(random_seed)

    non_core_indices = [i for i, row in df.iterrows() if str(row['material']).lower() != 'core']
    n_plies = len(non_core_indices)
    if n_plies == 0:
        raise ValueError("No optimizable plies found (all are 'core').")
    if n_plies % 2 != 0:
        raise ValueError("Number of non-core plies must be even for symmetric optimization.")
    # number of independent variables (half)
    n_half_vars = n_plies // 2

    pop = init_population_binary(n_half_vars)
    fitness = []
    cache = {}

    # evaluate initial population
    for bits in pop:
        key = tuple(bits.tolist())
        if key in cache:
            fit, strains, full_angles = cache[key]
        else:
            fit, strains, full_angles = evaluate_bits_candidate(df, force_vec, bits, target_strains, non_core_indices)
            cache[key] = (fit, strains, full_angles)
        fitness.append(fit)

    best_idx = int(np.argmin(fitness))
    best_bits = pop[best_idx].copy()
    best_fit = fitness[best_idx]
    best_strains = cache[tuple(best_bits.tolist())][1]
    best_full_angles = cache[tuple(best_bits.tolist())][2]
    history = [(0, best_fit)]

    # GA main loop
    for gen in range(1, N_GENERATIONS + 1):
        elite_idxs = np.argsort(fitness)[:ELITISM]
        elites = [pop[i].copy() for i in elite_idxs]

        new_pop = []
        while len(new_pop) < POP_SIZE - ELITISM:
            p1 = tournament_select(pop, fitness)
            p2 = tournament_select(pop, fitness)
            c1, c2 = single_point_crossover_bits(p1, p2)
            c1 = mutate_bits(c1)
            c2 = mutate_bits(c2)
            new_pop.extend([c1, c2])

        new_pop = new_pop[:POP_SIZE - ELITISM]
        new_pop.extend(elites)
        pop = new_pop

        # evaluate
        fitness = []
        for bits in pop:
            key = tuple(bits.tolist())
            if key in cache:
                fit, _, _ = cache[key]
            else:
                fit, strains, full_angles = evaluate_bits_candidate(df, force_vec, bits, target_strains, non_core_indices)
                cache[key] = (fit, strains, full_angles)
            fitness.append(fit)

        idx = int(np.argmin(fitness))
        if fitness[idx] < best_fit:
            best_fit = fitness[idx]
            best_bits = pop[idx].copy()
            best_strains = cache[tuple(best_bits.tolist())][1]
            best_full_angles = cache[tuple(best_bits.tolist())][2]

        history.append((gen, best_fit))

        if gen % 10 == 0 or gen == 1:
            print(f"Gen {gen:4d}  best_fit = {best_fit:.6e}")

        if EARLY_STOP_TOL > 0 and best_fit <= EARLY_STOP_TOL:
            print(f"Early stopping at generation {gen} with fitness {best_fit:.6e}")
            break

    return {
        "best_bits": best_bits,
        "best_fitness": best_fit,
        "best_strains": best_strains,
        "best_full_angles": best_full_angles,
        "history": history,
        "non_core_indices": non_core_indices
    }


# -------------------- Binary evaluator helper --------------------
def evaluate_binary_string(binary_input, df):
    """
    Accepts a binary string like '001110...' or a list/ndarray of 0/1 bits.
    Returns full symmetric angle list and computed strains.
    """
    bits_arr = np.asarray([int(c) for c in str(binary_input).strip()]) if isinstance(binary_input, str) else np.asarray(binary_input, dtype=int)
    non_core_indices = [i for i, row in df.iterrows() if str(row['material']).lower() != 'core']
    n_plies = len(non_core_indices)
    if n_plies % 2 != 0:
        raise ValueError("Number of non-core plies must be even for symmetric optimization.")
    n_half = n_plies // 2
    expected_len = n_half * BITS_PER_VAR
    if bits_arr.size != expected_len:
        raise ValueError(f"Binary input length must be {expected_len} (n_half * bits_per_var). Got {bits_arr.size}")
    full_angles = decode_bits_to_full_angles(bits_arr, n_half)
    # build override in order
    override = [float(a) for a in full_angles]
    ans, ply_stress = compute_strains(df, FORCE_MOMENT, override_degrees=override)
    return full_angles, ans, ply_stress


# -------------------- Main --------------------
def main():
    # read excel
    df = pd.read_excel(EXCEL_PATH)
    required_cs = {'material','e_x','e_y','e_s','v_x','deg','thickness'}
    if not required_cs.issubset(set(map(str.lower, df.columns))):
        raise ValueError(f"Expected columns {sorted(required_cs)} in {EXCEL_PATH}")

    # set RNG
    if RANDOM_SEED is not None:
        np.random.seed(RANDOM_SEED)

    # quick check: number of non-core plies must be even and match expected 8 in your case
    non_core_indices = [i for i, row in df.iterrows() if str(row['material']).lower() != 'core']
    n_plies = len(non_core_indices)
    print(f"Found {n_plies} non-core plies (must be even).")

    # initial strain with existing angles (for reference)
    current_strains, current_ply_stress = compute_strains(df, FORCE_MOMENT, override_degrees=None)
    print("Initial global strains (from file angles):")
    print(np.array_str(current_strains.flatten(), precision=6))

    # run GA optimizing half the plies (symmetric)
    print("\nStarting binary GA (symmetric encoding)...")
    result = run_binary_ga(df, FORCE_MOMENT, TARGET_STRAINS, random_seed=RANDOM_SEED)

    # decode best bits to full angles
    best_bits = result["best_bits"]
    n_half = n_plies // 2
    best_full_angles = decode_bits_to_full_angles(best_bits, n_half)

    # build array of full angles for all plies in df order (non-core replaced, core kept)
    full_angles_list = []
    bit_iter = iter(best_full_angles)
    for i, row in df.iterrows():
        if str(row['material']).lower() == 'core':
            full_angles_list.append(float(row['deg']))
        else:
            full_angles_list.append(float(next(bit_iter)))

    # compute final strains & ply stresses using best solution
    final_strains, final_ply_stress = compute_strains(df, FORCE_MOMENT, override_degrees=best_full_angles)

    print("\n=============== GA Result ===============")
    print(f"Best fitness: {result['best_fitness']:.6e}")
    print("Best full symmetric ply angles (deg):")
    print(list(best_full_angles))
    print("\nFull layup angles in dataframe order (deg):")
    print(full_angles_list)
    print("\nFinal global strains [εx, εy, γxy, κx, κy, κxy]:")
    print(np.array_str(final_strains.flatten(), precision=8))

    # Example: show how to evaluate a binary string directly
    # (uncomment to test, or call evaluate_binary_string externally)
    # example_bin = ''.join(str(b) for b in best_bits)
    # print(f"\nExample binary string for best solution: {example_bin}")

    return {
        "result": result,
        "best_full_angles": best_full_angles,
        "full_angles_list": full_angles_list,
        "final_strains": final_strains,
        "final_ply_stress": final_ply_stress
    }


if __name__ == "__main__":
    out = main()
