# AlphaEvolve HCLS Demo: HP Protein Folding

This repository demonstrates the capabilities of **AlphaEvolve** (Google DeepMind's evolutionary coding agent) for Healthcare and Life Sciences (HCLS) use cases.

Specifically, it implements the **HP (Hydrophobic-Polar) Protein Folding model** on a 2D square lattice, which is a classic NP-complete optimization problem in computational biology.

AlphaEvolve is used to evolve a python function `fold_protein` to find a conformation that maximizes H-H contacts (minimizes energy) for a benchmark sequence.

## Repository Structure

*   `src/`: Contains the evolution runner and configuration files.
    *   `src/run.py`: The entry point script.
    *   `src/alpha_evolve_runner.py`: The runner implementation that integrates with the official AlphaEvolve SDK.
    *   `src/gcp_setup.py`: Utility to automatically provision Discovery Engine resources.
    *   `src/data/initial_programs/protein_folding.py`: The initial heuristic (straight line fold) and evaluation logic.
    *   `src/data/problem_config/protein_folding.yaml`: Config file guiding the LLM and setting budget.
*   `visualize_results.ipynb`: Jupyter notebook to visualize the optimization progress and the best found structure.
*   `src/evolution_log_demo.jsonl`: Pre-run log file showing a successful demo run (used by the notebook as a fallback).

## Setup Instructions

1.  **Install the Official AlphaEvolve SDK:**
    This project requires the official `alpha_evolve` Python library. Install it in your environment (typically from the official Google Cloud repository).

2.  **Create a Virtual Environment & Install Dependencies:**
    We recommend using Python 3.13 (or 3.11+).
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --index-url https://pypi.org/simple -r src/requirements.txt
    # Also install matplotlib and jupyter for the visualization notebook
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

## Running the Demo

The entry point for running the evolution is `src/run.py`.

### What `run.py` does:
1.  **Auto-Provisions GCP Resources**: It uses `gcp_setup.py` to check for and automatically create the required Discovery Engine instance and conversational Assistant in your GCP project.
2.  **Loads Configuration**: It reads the YAML configuration file (e.g., `src/data/problem_config/protein_folding.yaml`).
3.  **Initializes AlphaEvolve Client**: It connects to the Google Cloud AlphaEvolve service using the specified project and engine.
4.  **Runs Evolution Loop**: It starts the evolutionary process using `run_controller_loop` from the official SDK, where mutated programs are evaluated in parallel.
5.  **Local Evaluation**: Each generated code variant is executed locally via `LocalEvaluator` to count H-H contacts.
6.  **Thread-Safe Logging**: Logs steps (code, scores) to `src/evolution_log.jsonl` using a thread lock to support parallel evaluation.

To run the evolution loop:

```bash
cd src
../venv/bin/python run.py \
  --problem_config ./data/problem_config/protein_folding.yaml \
  --project YOUR_GCP_PROJECT_ID \
  --engine alpha-evolve-protein-folding
```

Options:
*   `--problem_config`: Path to the config file (required).
*   `--project`: GCP Project ID. Defaults to your active `gcloud` project.
*   `--engine`: Discovery Engine ID. Defaults to `alpha-evolve-protein-folding`.

This will run for the configured number of steps (default 50) and output progress to the console and to `src/evolution_log.jsonl`.

## Visualizing Results

Start Jupyter Notebook:

```bash
jupyter notebook visualize_results.ipynb
```

Open the notebook and run the cells.
*   If you haven't run the evolution yet, the notebook will automatically load the pre-run `evolution_log_demo.jsonl` so you can see the results immediately.
*   Once you run the evolution, the notebook will load your live results from `evolution_log.jsonl`.

The notebook will show:
1.  **Optimization Progress:** A plot showing how the number of H-H contacts improves over successive LLM calls.
2.  **Best Fold Visualization:** A 2D plot of the folded protein, showing H (blue) and P (red) monomers, and highlighting the discovered H-H contacts (green dashed lines).
