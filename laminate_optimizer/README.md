# Composite Laminate Optimizer

A professional desktop GUI application for optimizing composite laminate layup sequences using Genetic Algorithms (GA).

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![Framework](https://img.shields.io/badge/framework-PySide6-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

## 🎯 Overview

The Composite Laminate Optimizer is a tool designed for composite materials engineers to optimize fiber orientation angles in laminated composites. It uses a binary-coded Genetic Algorithm to find the optimal ply stacking sequence that achieves target strain objectives under specified loading conditions.

### Key Features

- **Excel-like Layup Editor**: Define and modify laminate ply properties with an intuitive spreadsheet interface
- **Genetic Algorithm Optimization**: Binary-coded GA with configurable parameters
- **Real-time Monitoring**: Live fitness plot showing optimization progress
- **Symmetric Laminate Support**: Automatic enforcement of symmetric layup constraints
- **Classical Laminate Theory**: Full CLT implementation for stiffness matrix computation
- **Dark Theme UI**: Modern, professional interface optimized for extended use
- **Thread-safe Execution**: Non-blocking UI during optimization

## 📋 Composite Engineering Background

### Composite Engineering Note

This application implements Classical Laminate Theory (CLT) for analyzing and optimizing fiber-reinforced composite laminates. Key concepts:

- **ABD Matrix**: The laminate stiffness matrix relating forces/moments to strains/curvatures
- **Symmetric Laminate**: Plies mirrored about the midplane to eliminate coupling (B-matrix = 0)
- **Balanced Laminate**: Equal numbers of +θ and -θ plies to eliminate extension-shear coupling
- **Ply Orientation**: Fiber angle relative to the laminate reference direction

The GA optimizes fiber orientations to minimize the difference between computed and target strains under applied mechanical loads.

## 🚀 Quick Start

### Installation

1. **Clone or download the repository**

2. **Create a virtual environment (recommended)**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**:
   ```bash
   cd laminate_optimizer
   pip install -r requirements.txt
   ```

### Running the Application

```bash
python main.py
```

The application will launch with demo data loaded (8-ply quasi-isotropic layup).

## 🖥️ Application Layout

### Page 1: Optimization & Monitoring

**Left Panel (GA Settings)**:
- Population size, generations, crossover/mutation rates
- Elitism count and selection method
- Composite constraints (thickness, symmetry, balance)
- Target strain values and applied loads
- Random seed for reproducibility

**Right Panel (Results)**:
- Live fitness plot (best and average fitness per generation)
- Progress bar with status
- Results history table
- Start/Stop controls

### Page 2: Layup Editor

- Excel-like editable table for ply data
- Add/Remove/Duplicate ply operations
- Material property database
- Import/Export Excel functionality
- Real-time constraint validation
- Summary statistics panel

## 🔧 Configuration

### GA Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Population Size | 200 | Number of individuals per generation |
| Generations | 300 | Maximum generations to evolve |
| Crossover Rate | 0.9 | Probability of crossover |
| Mutation Rate | 0.08 | Per-bit mutation probability |
| Elitism | 2 | Best individuals preserved |
| Selection | Tournament | Selection strategy |
| Tournament Size | 3 | Tournament participants |

### Composite Constraints

| Constraint | Default | Description |
|------------|---------|-------------|
| Max Thickness | 10 mm | Maximum total laminate thickness |
| Symmetry Required | True | Enforce symmetric layup |
| Balanced Required | False | Enforce balanced +θ/-θ pairs |

### Data Format

The layup data uses the following columns:

| Column | Type | Description |
|--------|------|-------------|
| material | string | Material designation (e.g., 'T300/5208') |
| deg | float | Fiber angle in degrees |
| thickness | float | Ply thickness in meters |
| e_x | float | Longitudinal modulus (Pa) |
| e_y | float | Transverse modulus (Pa) |
| e_s | float | Shear modulus (Pa) |
| v_x | float | Poisson's ratio |

## 🔌 GA Integration

### Using the Built-in GA

The application includes a complete GA implementation (`ga_demo.py`) that provides all optimization functionality out of the box.

### Connecting Custom GA Code

To integrate your own GA implementation:

1. **Create an adapter** in `ga_adapter.py` that interfaces with your GA code
2. **Expected GA API**:
   ```python
   def run_ga(config, layup_data, progress_callback, stop_flag):
       """
       Run the genetic algorithm optimization.
       
       Args:
           config: Dict with GA parameters
           layup_data: pandas DataFrame with ply data
           progress_callback: Callable(gen, best_fit, avg_fit)
           stop_flag: Callable that returns True to stop
       
       Returns:
           OptimizationResult with best solution
       """
       ...
   ```

3. **The existing Code1.py** in the parent directory is automatically detected and its logic is reflected in the demo GA

## ⚙️ Threading Model

The application uses Qt's threading system to ensure UI responsiveness:

```
┌─────────────────┐     ┌─────────────────┐
│   Main Thread   │     │  Worker Thread  │
│    (UI/Qt)      │     │     (GA)        │
├─────────────────┤     ├─────────────────┤
│                 │     │                 │
│  User Input     │────>│  Start GA       │
│                 │     │                 │
│  Update Plot  <─│─────│  generation_    │
│  Update Table   │     │  completed()    │
│                 │     │                 │
│  Show Results <─│─────│  finished()     │
│                 │     │                 │
│  Stop Request ──│────>│  aborted()      │
│                 │     │                 │
└─────────────────┘     └─────────────────┘
```

### Signals

- `generation_completed(gen, best_fitness, avg_fitness)`: Emitted after each generation
- `finished(result)`: Emitted when optimization completes
- `aborted()`: Emitted when stopped by user
- `error(message)`: Emitted on error

## 📁 Project Structure

```
laminate_optimizer/
├── main.py                 # Application entry point
├── ga_adapter.py           # Interface between GUI and GA
├── ga_demo.py              # Built-in GA implementation
├── demo_data.py            # Demo data and material database
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── models/
│   ├── __init__.py
│   └── laminate_model.py   # Data models and constraints
└── ui/
    ├── __init__.py
    ├── main_window.py      # Main application window
    ├── run_page.py         # Optimization page
    ├── layup_editor.py     # Layup editor page
    └── styles.py           # Dark theme styling
```

## 📦 Dependencies

- **PySide6** (≥6.5.0): Qt6 GUI framework
- **pyqtgraph** (≥0.13.0): Real-time plotting
- **pandas** (≥2.0.0): Data handling
- **numpy** (≥1.24.0): Numerical computing
- **openpyxl** (≥3.1.0): Excel file support
- **qdarktheme** (≥2.1.0): Dark theme (optional)

## 🎨 UI Design

The application follows these design principles:

- **Fixed window size**: 1400 × 750 for consistent layout
- **Dark theme**: Reduced eye strain for extended use
- **Font sizes**: Body 12pt, Titles 16-18pt
- **Padding**: Minimum 12px for comfortable spacing
- **Professional appearance**: Suitable for engineering applications

## 📘 Composite Engineering Notes

Throughout the code, you'll find "Composite Engineering Notes" that explain the engineering rationale behind design decisions:

1. **Symmetry**: Eliminates the B-matrix, preventing warping during cure
2. **Balance**: Eliminates extension-shear coupling for predictable behavior
3. **Discrete Angles**: Standard industry practice (0°, ±45°, 90°)
4. **Binary Encoding**: Efficient representation for discrete optimization

## 🐛 Troubleshooting

### Application won't start

1. Verify Python 3.10+ is installed: `python --version`
2. Install dependencies: `pip install -r requirements.txt`
3. Check for import errors by running: `python -c "from PySide6.QtWidgets import QApplication"`

### Optimization fails

1. Ensure layup data has valid values (no NaN or negative thicknesses)
2. Check that the number of plies is even for symmetric optimization
3. Verify target strains are achievable with the given material properties

### UI not responding

1. The GA runs in a separate thread - the UI should remain responsive
2. If stuck, use the Stop button to abort the optimization
3. Restart the application if issues persist

## 📄 License

This project is provided for educational and professional use.

## 🙏 Acknowledgments

- Classical Laminate Theory implementation based on standard composite mechanics texts
- UI design inspired by modern engineering software practices
- PySide6 and pyqtgraph communities for excellent documentation
