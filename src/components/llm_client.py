"""LLM proxy for self-hosted models."""

import abc
import asyncio
from collections.abc import Mapping, Sequence
import concurrent.futures

import random
from typing import Any

from components import exceptions
from google import genai
from google.genai import types as genai_types
from typing_extensions import override


class BaseLLMClient(abc.ABC):
  """Base class for LLM clients."""

  @abc.abstractmethod
  def generate(
      self,
      prompt: str,
      model_name: str | None = None,
      system_instruction: str | None = None,
  ) -> str:
    """Generates a response from the LLM."""

  async def generate_async(
      self,
      prompt: str,
      model_name: str | None = None,
      system_instruction: str | None = None,
  ) -> str:
    """Generates a response from the LLM asynchronously."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
      future = asyncio.get_running_loop().run_in_executor(
          executor,
          self.generate,
          prompt,
          model_name,
          system_instruction,
      )
      return await future

  def get_state(self) -> Mapping[str, Any]:
    return {}

  def set_state(self, state: Mapping[str, Any]) -> None:
    del state  # Unused.


class GenAILLMClient(BaseLLMClient):
  """LLM generator using google.genai with Gemini."""

  def __init__(
      self,
      model_weights: Sequence[tuple[str, float]] = (
          ('gemini-2.5-flash', 0.8),
          ('gemini-2.5-pro', 0.2),
      ),
  ):
    # Initialize client for Vertex AI using Application Default Credentials (ADC)
    self._client = genai.Client(vertexai=True)
    self._model_weights = model_weights

  @override
  def generate(
      self,
      prompt: str,
      model_name: str | None = None,
      system_instruction: str | None = None,
  ) -> str:
    """Generates a response from the LLM."""
    if model_name is None:
      # Sample a model name based on weights.
      models, weights = zip(*self._model_weights)
      model_name = random.choices(models, weights=weights, k=1)[0]

    config = None
    if system_instruction is not None:
      config = genai_types.GenerateContentConfig(
          system_instruction=system_instruction,
      )

    try:
      response = self._client.models.generate_content(
          model=model_name,
          contents=prompt,
          config=config,
      )
      return response.text
    except exceptions.LLMInferenceError:
      raise
    except (genai.errors.APIError, ValueError) as e:
      raise exceptions.LLMInferenceError(
          f'LLM inference failed for model {model_name}: {e}'
      ) from e
