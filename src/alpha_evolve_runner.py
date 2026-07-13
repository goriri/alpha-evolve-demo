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


class AlphaEvolveRunner:
    """Generic runner for AlphaEvolve experiments."""

    def __init__(
        self,
        config: configuration.Configuration,
        project_id: str,
        engine_id: str,
    ):
        self.config = config
        self.project_id = project_id
        self.engine_id = engine_id
        self.metric_name = config.problem_spec.main_metric_name
        self.step_counter = 0
        self.best_score = -1e9
        self.log_lock = threading.Lock()

        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        self.log_file = os.path.join(project_root, "src", "evolution_log.jsonl")

    def _write_log_success(self, step, score, best_score, program_code):
        log_entry = {
            "step": step,
            "status": "success",
            "scores": {self.metric_name: float(score)},
            "best_scores": {
                f"scores_to_optimize/{self.metric_name}": float(best_score)
            },
            "program": program_code,
        }
        with self.log_lock:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

    def _write_log_failure(self, step, error_type, error_message):
        with self.log_lock:
            best_score_to_log = self.best_score
        log_entry = {
            "step": step,
            "status": "error",
            "error_type": error_type,
            "error_message": error_message,
            "best_scores": {
                f"scores_to_optimize/{self.metric_name}": float(
                    best_score_to_log
                )
            },
        }
        with self.log_lock:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")

    def _failed_evaluation(self) -> dict:
        scores = [
            AlphaEvolveEvaluationScore(metric=self.metric_name, score=-1e9)
        ]
        program_evaluation = AlphaEvolveProgramEvaluation(
            scores=AlphaEvolveEvaluationScores(scores=scores)
        )
        return program_evaluation.model_dump()

    def evaluate_candidate(self, program_candidate) -> dict:
        """Evaluator callback for AlphaEvolve Cloud API."""
        logger.info(
            "Starting evaluation of program: %s", program_candidate.get("name")
        )

        with self.log_lock:
            self.step_counter += 1
            step = self.step_counter

        files = program_candidate.get("content", {}).get("files", [])
        if not files:
            err_msg = "No files in program candidate."
            logger.error(err_msg)
            self._write_log_failure(step, "InvalidProgramError", err_msg)
            return self._failed_evaluation()

        code = files[0].get("content")
        if not code:
            err_msg = "Empty content in program candidate file."
            logger.error(err_msg)
            self._write_log_failure(step, "InvalidProgramError", err_msg)
            return self._failed_evaluation()

        evaluator = LocalEvaluator()
        try:
            scores_dict, _ = evaluator.run(code)
            score_value = scores_dict.get(self.metric_name)
            if score_value is None:
                err_msg = f"{self.metric_name} not found in scores."
                logger.error("%s: %s", err_msg, scores_dict)
                self._write_log_failure(step, "InvalidResultError", err_msg)
                return self._failed_evaluation()

            logger.info("Evaluation succeeded. Score: %s", score_value)

            with self.log_lock:
                if score_value > self.best_score:
                    self.best_score = score_value
                best_score_to_log = self.best_score

            self._write_log_success(step, score_value, best_score_to_log, code)

            scores = [
                AlphaEvolveEvaluationScore(
                    metric=self.metric_name, score=float(score_value)
                )
            ]
            program_evaluation = AlphaEvolveProgramEvaluation(
                scores=AlphaEvolveEvaluationScores(scores=scores)
            )
            return program_evaluation.model_dump()

        except Exception as e:
            logger.exception("Evaluation failed with exception: %s", e)
            self._write_log_failure(step, type(e).__name__, str(e))
            return self._failed_evaluation()

    async def run(self) -> dict:
        # Clear and initialize log file
        with open(self.log_file, "w") as f:
            pass

        with self.log_lock:
            self.step_counter = 0
            self.best_score = -1e9

        client = AlphaEvolveClient(
            project_id=self.project_id,
            location="global",
            collection="default_collection",
            engine=self.engine_id,
            assistant="default_assistant",
        )

        max_programs_evaluated = self.config.budget.num_llm_calls

        experiment = AlphaEvolveExperiment(
            client,
            self.evaluate_candidate,
            max_programs_evaluated,
            parallel_evaluation=True,
        )

        # Use default model for generation
        generation_models = [{"name": "gemini-3.5-flash", "weight": 1.0}]

        exp_config = {
            "title": self.config.name,
            "problem_description": self.config.problem_spec.problem_description,
            "program_language": "python",
            "run_settings": {
                "max_programs": self.config.budget.num_llm_calls,
                "concurrency": self.config.budget.num_coroutines,
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
            initial_scores_dict, _ = evaluator.run(
                self.config.problem_spec.initial_program
            )
            initial_score = initial_scores_dict.get(self.metric_name, -1e9)
        except Exception:
            logger.exception("Failed to evaluate initial program locally.")
            initial_score = -1e9

        initial_program = {
            "content": {
                "files": [
                    {
                        "path": f"{self.config.name}.py",
                        "content": self.config.problem_spec.initial_program,
                    }
                ]
            },
            "evaluation": {
                "scores": {
                    "scores": [
                        {
                            "metric": self.metric_name,
                            "score": float(initial_score),
                        }
                    ]
                }
            },
        }

        experiment.create_initial_program(initial_program)
        experiment.start_experiment()

        nest_asyncio.apply()

        await run_controller_loop(
            experiment, num_evaluators=self.config.budget.num_coroutines
        )

        # Retrieve results
        list_params = {"order_by": f"{self.metric_name} desc"}
        response = experiment.list_programs(params=list_params)

        best_prog_dict = {}
        if response and "alphaEvolvePrograms" in response:
            programs = response["alphaEvolvePrograms"]
            if programs:
                from alpha_evolve.visualization import get_score

                programs.sort(
                    key=lambda p: get_score(p, self.metric_name), reverse=True
                )
                best_prog_dict = programs[0]

        return best_prog_dict


async def async_run(
    config: configuration.Configuration,
    project_id: str,
    engine_id: str,
) -> dict:
    runner = AlphaEvolveRunner(config, project_id, engine_id)
    return await runner.run()
