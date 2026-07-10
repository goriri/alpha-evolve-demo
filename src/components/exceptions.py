"""Custom exceptions for AlphaEvolve components."""


class AlphaEvolveError(Exception):
  """Base exception for recoverable AlphaEvolve errors."""


class CodeExecutionError(AlphaEvolveError):
  """Raised when code execution in the sandbox fails."""


class LLMInferenceError(AlphaEvolveError):
  """Raised when LLM generation fails."""


class DiffParsingError(AlphaEvolveError):
  """Raised when parsing or applying diffs from the LLM output fails."""
