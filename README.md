# AlphaEvolve HCLS Demos

This repository demonstrates the capabilities of **AlphaEvolve** (Google DeepMind's evolutionary coding agent) for Healthcare and Life Sciences (HCLS) use cases. It includes two optimization problems:

1.  **HP Protein Folding**: A classic NP-complete optimization problem where we evolve a heuristic to fold a Hydrophobic-Polar protein sequence on a 2D lattice to maximize stabilizing H-H contacts.
2.  **Fast DNA Sequence Alignment**: A code-wise more complex problem with a larger LLM budget, where we evolve a heuristic local alignment algorithm that approximates the optimal Smith-Waterman score in sub-quadratic time (e.g. via adaptive banding or seed-and-extend).

---

## Repository Structure

*   `src/`: Contains the evolution runner and configuration files.
    *   `src/run.py`: The entry point script.
    *   `src/alpha_evolve_runner.py`: The generic runner implementation that integrates with the official AlphaEvolve SDK.
    *   `src/gcp_setup.py`: Utility to automatically provision Discovery Engine resources.
    *   `src/data/initial_programs/`:
        *   `protein_folding.py`: Initial straight-line fold heuristic and lattice evaluator.
        *   `sequence_alignment.py`: Initial narrow banded SW heuristic and benchmark evaluator.
    *   `src/data/problem_config/`:
        *   `protein_folding.yaml`: Budget (50 calls) and config for protein folding.
        *   `sequence_alignment.yaml`: Higher budget (100 calls) and config for sequence alignment.
*   `visualize_results.ipynb`: Jupyter notebook to visualize Protein Folding results.
*   `visualize_alignment.ipynb`: Jupyter notebook to visualize Sequence Alignment results.

---

## Setup Instructions

1.  **Install the Official AlphaEvolve SDK:**
    This project requires the official `alpha_evolve` Python library. Install it in your environment (typically from the official Google Cloud repository).

2.  **Create a Virtual Environment & Install Dependencies:**
    We recommend using Python 3.13 (or 3.11+).
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --index-url https://pypi.org/simple -r src/requirements.txt
    # Also install matplotlib and jupyter for the visualization notebooks
    pip install --index-url https://pypi.org/simple matplotlib jupyter
    ```
    *Note: We use `LocalEvaluator` by default, which runs the code in local subprocesses, avoiding the need for Docker permissions.*

3.  **Set up Application Default Credentials (ADC):**
    AlphaEvolve uses Vertex AI and requires ADC for GCP authentication.
    Ensure you have the Google Cloud SDK installed and run:
    ```bash
    gcloud auth application-default login
    ```
    This will configure your local environment to use your Google Cloud credentials.

---

## Running the Demos

The entry point for running the evolution is `src/run.py`.

### Option 1: Run HP Protein Folding (Default Budget)
This runs the evolution with a budget of 50 LLM calls.

```bash
cd src
../venv/bin/python run.py \
  --problem_config ./data/problem_config/protein_folding.yaml \
  --project YOUR_GCP_PROJECT_ID \
  --engine alpha-evolve-protein-folding
```

### Option 2: Run Fast DNA Sequence Alignment (Higher Budget)
This runs the evolution with a higher budget of 100 LLM calls and concurrency of 4.

```bash
cd src
../venv/bin/python run.py \
  --problem_config ./data/problem_config/sequence_alignment.yaml \
  --project YOUR_GCP_PROJECT_ID \
  --engine alpha-evolve-sequence-alignment
```

### Options:
*   `--problem_config`: Path to the config file (required).
*   `--project`: GCP Project ID. Defaults to your active `gcloud` project.
*   `--engine`: Discovery Engine ID. Dedicated engine name is recommended for each problem.

---

## Visualizing Results

Start Jupyter Notebook:

```bash
jupyter notebook
```

### 1. Visualizing Protein Folding
Open `visualize_results.ipynb`. The notebook will show:
*   **Optimization Progress:** A plot showing how the number of H-H contacts improves.
*   **Best Fold Visualization:** A 2D plot of the folded protein showing H (blue) and P (red) monomers and H-H contacts (green dashed lines).
*   **Code Diff:** A git-style colored diff comparing the evolved code to the baseline.

### 2. Visualizing Sequence Alignment
Open `visualize_alignment.ipynb`. The notebook will show:
*   **Optimization Progress:** A plot showing how the alignment efficiency score (combining accuracy and speedup) improves.
*   **Code Diff:** A git-style colored diff showing the heuristic improvements (e.g. adaptive banding, seed hashing).

---

## Evolved Algorithmic Optimizations

AlphaEvolve does not just find a static path; it evolves a **heuristic search algorithm** to solve these problems.

### HP Protein Folding Optimizations
Key optimizations typically discovered and implemented by the agent include:
*   **Depth-First Search (DFS) Backtracking**: Transitioning from static layouts to systematic tree search.
*   **Branch-and-Bound Pruning**: Precomputing remaining Hydrophobic (H) monomers to establish an upper bound on potential contacts. Branches that cannot beat the current best score are pruned immediately.
*   **Symmetry Breaking**: Restricting search directions at early steps to avoid exploring redundant mirror-image conformations.

### Fast DNA Sequence Alignment Optimizations
Key optimizations typically discovered and implemented by the agent include:
*   **Adaptive Banding**: Dynamically shifting or widening the DP band based on sequence similarity or path scores.
*   **Seed-and-Extend (BLAST-like)**: Indexing matching k-mers (seeds) first and performing dynamic programming only around these seeds.
*   **Data Structure Optimization**: Replacing slow Python dictionaries with pre-allocated flat arrays or numpy arrays to speed up table lookups.
