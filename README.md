# AlphaEvolve HCLS Demo: HP Protein Folding

This repository demonstrates the capabilities of **AlphaEvolve** (Google DeepMind's evolutionary coding agent) for Healthcare and Life Sciences (HCLS) use cases.

Specifically, it implements the **HP (Hydrophobic-Polar) Protein Folding model** on a 2D square lattice, which is a classic NP-complete optimization problem in computational biology.

AlphaEvolve is used to evolve a python function `fold_protein` to find a conformation that maximizes H-H contacts (minimizes energy) for a benchmark sequence.

## Repository Structure

*   `src/`: Contains the AlphaEvolve core engine (minimal implementation with local evaluation).
    *   `src/data/initial_programs/protein_folding.py`: The initial heuristic (straight line fold) and evaluation logic.
    *   `src/data/problem_config/protein_folding.yaml`: Config file guiding the LLM and setting budget.
*   `visualize_results.ipynb`: Jupyter notebook to visualize the optimization progress and the best found structure.
*   `src/evolution_log_demo.jsonl`: Pre-run log file showing a successful demo run (used by the notebook as a fallback).

## Setup Instructions

1.  **Create a Virtual Environment & Install Dependencies:**
    We recommend using Python 3.13 (or 3.11+).
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --index-url https://pypi.org/simple -r src/requirements.txt
    # Also install matplotlib and jupyter for the visualization notebook
    pip install --index-url https://pypi.org/simple matplotlib jupyter
    ```
    *Note: We modified the requirements to use `LocalEvaluator` by default, which runs the code in local subprocesses, avoiding the need for Docker permissions.*

2.  **Set up Application Default Credentials (ADC):**
    AlphaEvolve uses Vertex AI and requires ADC for authentication.
    Ensure you have the Google Cloud SDK installed and run:
    ```bash
    gcloud auth application-default login
    ```
    This will configure your local environment to use your Google Cloud credentials.

## Running the Demo

The entry point for running the evolution is `src/run.py`.

### What `run.py` does:
1.  **Loads Configuration**: It reads the YAML configuration file (e.g., `src/data/problem_config/protein_folding.yaml`) which defines the problem, LLM budget, and modules to use.
2.  **Initializes AlphaEvolve**: It sets up the database, LLM client (using Vertex AI), and evaluator.
3.  **Runs Evolution Loop**: It starts the evolutionary process, where the LLM is repeatedly prompted to improve the protein folding code.
4.  **Local Evaluation**: Each LLM-generated code variant is executed locally to evaluate its performance (number of H-H contacts).
5.  **Logging**: It logs every step (including code, scores, and LLM prompts) to `src/evolution_log.jsonl`.

To run the evolution loop:

```bash
cd src
../venv/bin/python run.py --problem_config=./data/problem_config/protein_folding.yaml
```

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
