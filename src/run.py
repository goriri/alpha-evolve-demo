"""Run AlphaEvolve with official Cloud API."""

import argparse
import asyncio
from collections.abc import Sequence
import logging
import os
import subprocess
import sys

import alpha_evolve_runner
import gcp_setup
from alpha_evolve.visualization import get_score
from components import configuration



def get_default_project():
  try:
    result = subprocess.run(
        ["gcloud", "config", "get", "project"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
  except Exception:
    return None


def main(argv: Sequence[str]) -> None:
  parser = argparse.ArgumentParser(description="Run AlphaEvolve.")
  parser.add_argument(
      "--problem_config",
      type=str,
      required=True,
      help="Path to the .yaml problem config file.",
  )
  parser.add_argument(
      "--project",
      type=str,
      default=get_default_project(),
      help="GCP Project ID. Defaults to active gcloud project.",
  )
  parser.add_argument(
      "--engine",
      type=str,
      default="alpha-evolve-protein-folding",
      help="Discovery Engine ID.",
  )
  args = parser.parse_args(argv[1:])

  # Configure basic logging
  logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

  problem_config_path = args.problem_config
  if not os.path.exists(problem_config_path):
    logging.error("Problem config file not found: %s", problem_config_path)
    sys.exit(1)

  if not args.project:
    logging.error(
        "GCP Project ID not specified and could not be auto-detected."
    )
    sys.exit(1)

  with open(problem_config_path, "r") as f:
    problem_config_yaml = f.read()
  config = configuration.from_yaml(problem_config_yaml)

  logging.info("Using project: %s", args.project)
  logging.info("Using engine: %s", args.engine)

  # Ensure GCP resources exist before running
  try:
    gcp_setup.ensure_engine_and_assistant(args.project, args.engine)
  except Exception as e:
    logging.error("Failed to ensure GCP resources: %s", e)
    sys.exit(1)

  best_program = asyncio.run(
      alpha_evolve_runner.async_run(
          config, project_id=args.project, engine_id=args.engine
      )
  )

  if best_program:
    code = (
        best_program.get("content", {}).get("files", [{}])[0].get("content")
    )
    metric_name = config.problem_spec.main_metric_name
    score = get_score(best_program, metric_name)
    logging.info("Best program:\n%s", code)
    logging.info("Best score (%s): %s", metric_name, score)
    
    # Save the best program to a file for visualization notebook to read if needed.
    # Currently the notebook might read from evolution_log.jsonl which we are not writing anymore.
    # Wait! The notebook visualizes results.
    # If we don't write log files, how will the notebook work?
    # The notebook might need to call the API to list programs, or we need to save them.
    # Let's check how the notebook works.
  else:
    logging.error("No programs found.")


if __name__ == "__main__":
  main(sys.argv)
