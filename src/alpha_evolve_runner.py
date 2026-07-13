"""AlphaEvolve implementation using the official Google Cloud API."""

import asyncio
import json
import logging
import os
import threading
from typing import Any, Mapping

import nest_asyncio
from alpha_evolve.client import AlphaEvolveClient
from alpha_evolve.controller import run_controller_loop
from alpha_evolve.experiment import AlphaEvolveExperiment
from alpha_evolve.models import (
    AlphaEvolveEvaluationScore,
    AlphaEvolveEvaluationScores,
    AlphaEvolveProgramEvaluation,
)

from components import configuration
from components.evaluator_client import LocalEvaluator

logger = logging.getLogger(__name__)

# Thread-safe logging setup
_log_lock = threading.Lock()
_step_counter = 0
_best_score = -1e9
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOG_FILE = os.path.join(_PROJECT_ROOT, "src", "evolution_log.jsonl")


def protein_folding_evaluation(program_candidate) -> dict:
  """Evaluator callback for AlphaEvolve Cloud API."""
  global _step_counter, _best_score
  
  logger.info(
      "Starting evaluation of program: %s", program_candidate.get("name")
  )
  
  with _log_lock:
    _step_counter += 1
    step = _step_counter

  files = program_candidate.get("content", {}).get("files", [])
  if not files:
    err_msg = "No files in program candidate."
    logger.error(err_msg)
    _write_log_failure(step, "InvalidProgramError", err_msg)
    return _failed_evaluation(err_msg)

  code = files[0].get("content")
  if not code:
    err_msg = "Empty content in program candidate file."
    logger.error(err_msg)
    _write_log_failure(step, "InvalidProgramError", err_msg)
    return _failed_evaluation(err_msg)

  evaluator = LocalEvaluator()
  try:
    scores_dict, _ = evaluator.run(code)
    score_value = scores_dict.get("hh_contacts")
    if score_value is None:
      err_msg = "hh_contacts not found in scores."
      logger.error("%s: %s", err_msg, scores_dict)
      _write_log_failure(step, "InvalidResultError", err_msg)
      return _failed_evaluation(err_msg)

    logger.info("Evaluation succeeded. Score: %s", score_value)
    
    with _log_lock:
      if score_value > _best_score:
        _best_score = score_value
      best_score_to_log = _best_score

    _write_log_success(step, score_value, best_score_to_log, code)

    scores = [
        AlphaEvolveEvaluationScore(
            metric="hh_contacts", score=float(score_value)
        )
    ]
    program_evaluation = AlphaEvolveProgramEvaluation(
        scores=AlphaEvolveEvaluationScores(scores=scores)
    )
    return program_evaluation.model_dump()

  except Exception as e:
    logger.exception("Evaluation failed with exception: %s", e)
    _write_log_failure(step, type(e).__name__, str(e))
    return _failed_evaluation(f"Evaluation failed: {e}")


def _failed_evaluation(reason: str) -> dict:
  scores = [
      AlphaEvolveEvaluationScore(metric="hh_contacts", score=-1e9)
  ]
  program_evaluation = AlphaEvolveProgramEvaluation(
      scores=AlphaEvolveEvaluationScores(scores=scores)
  )
  return program_evaluation.model_dump()


def _write_log_success(step, score, best_score, program_code):
  log_entry = {
      "step": step,
      "status": "success",
      "scores": {"hh_contacts": float(score)},
      "best_scores": {"scores_to_optimize/hh_contacts": float(best_score)},
      "program": program_code,
  }
  with _log_lock:
    with open(_LOG_FILE, "a") as f:
      f.write(json.dumps(log_entry) + "\n")


def _write_log_failure(step, error_type, error_message):
  global _best_score
  with _log_lock:
    best_score_to_log = _best_score
  log_entry = {
      "step": step,
      "status": "error",
      "error_type": error_type,
      "error_message": error_message,
      "best_scores": {"scores_to_optimize/hh_contacts": float(best_score_to_log)},
  }
  with _log_lock:
    with open(_LOG_FILE, "a") as f:
      f.write(json.dumps(log_entry) + "\n")


async def async_run(
    config: configuration.Configuration,
    project_id: str,
    engine_id: str,
) -> dict:
  """Runs AlphaEvolve using the official Cloud API."""
  global _step_counter, _best_score
  
  # Clear and initialize log file
  with open(_LOG_FILE, "w") as f:
    pass
    
  with _log_lock:
    _step_counter = 0
    _best_score = -1e9

  client = AlphaEvolveClient(
      project_id=project_id,
      location="global",
      collection="default_collection",
      engine=engine_id,
      assistant="default_assistant",
  )

  max_programs_evaluated = config.budget.num_llm_calls

  experiment = AlphaEvolveExperiment(
      client,
      protein_folding_evaluation,
      max_programs_evaluated,
      parallel_evaluation=True,
  )

  # Use default model for generation
  generation_models = [{"name": "gemini-3.5-flash", "weight": 1.0}]

  exp_config = {
      "title": "Protein Folding",
      "problem_description": config.problem_spec.problem_description,
      "program_language": "python",
      "run_settings": {
          "max_programs": config.budget.num_llm_calls,
          "concurrency": config.budget.num_coroutines,
      },
      "generation_settings": {
          "models": generation_models,
      },
  }

  logger.info("Creating experiment...")
  experiment.create_experiment(exp_config)

  # Evaluate initial program locally to get starting score
  evaluator = LocalEvaluator()
  try:
    initial_scores_dict, _ = evaluator.run(config.problem_spec.initial_program)
    initial_score = initial_scores_dict.get("hh_contacts", -1e9)
  except Exception:
    logger.exception("Failed to evaluate initial program locally.")
    initial_score = -1e9

  initial_program = {
      "content": {
          "files": [
              {
                  "path": "protein_folding.py",
                  "content": config.problem_spec.initial_program,
              }
          ]
      },
      "evaluation": {
          "scores": {
              "scores": [
                  {"metric": "hh_contacts", "score": float(initial_score)}
              ]
          }
      },
  }

  experiment.create_initial_program(initial_program)
  experiment.start_experiment()

  # run_controller_loop uses asyncio, we need to allow nesting if run in notebook
  nest_asyncio.apply()

  # Run the controller loop
  await run_controller_loop(
      experiment, num_evaluators=config.budget.num_coroutines
  )

  # Retrieve results
  list_params = {"order_by": "hh_contacts desc"}
  response = experiment.list_programs(params=list_params)

  best_prog_dict = {}
  if response and "alphaEvolvePrograms" in response:
    programs = response["alphaEvolvePrograms"]
    if programs:
      from alpha_evolve.visualization import get_score

      programs.sort(key=lambda p: get_score(p, "hh_contacts"), reverse=True)
      best_prog_dict = programs[0]

  return best_prog_dict
