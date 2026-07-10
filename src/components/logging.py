"""Logging utils for AlphaEvolve."""

import abc
import collections
from collections.abc import Mapping
import textwrap
from typing import Any

from components import evolution_database


class BaseLogger(abc.ABC):
  """Base class for logging programs and scores."""

  def __init__(self):
    self._step_stats = collections.defaultdict(int)
    self._error_stats = collections.defaultdict(int)
    self._best_scores = collections.defaultdict(lambda: float('-inf'))

  @property
  def total_steps(self) -> int:
    return sum(self._step_stats.values())

  @property
  def step_stats(self) -> Mapping[str, int]:
    return dict(self._step_stats)

  @property
  def error_stats(self) -> Mapping[str, int]:
    return dict(self._error_stats)

  def log_step(
      self,
      program: evolution_database.Program,
      prompt: str | None,
      llm_sample: str | None,
  ):
    """Logs a step and updates the best scores."""
    del prompt, llm_sample  # Unused.
    self._step_stats['successful_steps'] += 1
    # Update best scores:
    for metric, score in program.scores.items():
      metric_key = f'scores_to_optimize/{metric}'
      if score is not None and score > self._best_scores[metric_key]:
        self._best_scores[metric_key] = score

  def log_error(
      self,
      program: str | None,
      error: Exception,
      traceback: str | None,
      prompt: str | None,
      llm_sample: str | None,
  ):
    """Logs an error and updates the best scores."""
    del program, traceback, prompt, llm_sample  # Unused.
    self._step_stats['failed_steps'] += 1
    self._error_stats[type(error).__name__] += 1

  def close(self) -> None:
    """Closes the logger and flushes the logs."""
    # No action needed by default.
    pass

  def get_state(self) -> Mapping[str, Any]:
    return {
        'step_stats': dict(self._step_stats),
        'error_stats': dict(self._error_stats),
        'best_scores': dict(self._best_scores),
    }

  def set_state(self, state: Mapping[str, Any]) -> None:
    self._step_stats.update(state['step_stats'])
    self._error_stats.update(state['error_stats'])
    self._best_scores.update(state['best_scores'])


class LocalLogger(BaseLogger):
  """Logs programs and scores to the console."""

  def log_step(
      self,
      program: evolution_database.Program,
      prompt: str | None,
      llm_sample: str | None,
  ):
    """Logs a step and updates the best scores."""
    super().log_step(program, prompt, llm_sample)
    output = program.output
    output_str = (
        str(output) if len(str(output)) < 100 else f'{str(output)[:100]}...'
    )
    print(textwrap.dedent(f"""\
        --------------------------------------------------
        Step:        {self.total_steps}
        Program:     \n{textwrap.indent(str(program.text), ' ' * 8)}
        Output:      {output_str}
        Scores:      {program.scores}
        Best Scores: {dict(self._best_scores)}
        --------------------------------------------------
        """))

  def log_error(
      self,
      program: str | None,
      error: Exception,
      traceback: str | None,
      prompt: str | None,
      llm_sample: str | None,
  ):
    """Logs an error and updates the best scores."""
    super().log_error(program, error, traceback, prompt, llm_sample)
    print(f'step: {self.total_steps}\nerror: {error!r}\ntraceback: {traceback}')


class JSONLogger(LocalLogger):
  """Logs programs and scores to the console and to a JSONL file."""

  def __init__(self, log_path: str = 'evolution_log.jsonl'):
    super().__init__()
    self._log_path = log_path
    # Clear the file if it exists
    with open(self._log_path, 'w') as f:
      pass

  def log_step(
      self,
      program: evolution_database.Program,
      prompt: str | None,
      llm_sample: str | None,
  ):
    super().log_step(program, prompt, llm_sample)
    import json
    log_entry = {
        'step': self.total_steps,
        'status': 'success',
        'scores': program.scores,
        'best_scores': dict(self._best_scores),
        'program': program.text,
    }
    with open(self._log_path, 'a') as f:
      f.write(json.dumps(log_entry) + '\n')

  def log_error(
      self,
      program: str | None,
      error: Exception,
      traceback: str | None,
      prompt: str | None,
      llm_sample: str | None,
  ):
    super().log_error(program, error, traceback, prompt, llm_sample)
    import json
    log_entry = {
        'step': self.total_steps,
        'status': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'best_scores': dict(self._best_scores),
    }
    with open(self._log_path, 'a') as f:
      f.write(json.dumps(log_entry) + '\n')
