# EVOLVE-BLOCK-START
"""HP model protein folding heuristic."""
import numpy as np

def fold_protein(sequence):
  """Fold a protein sequence on a 2D lattice.

  The goal is to maximize the number of H-H contacts (non-consecutive H monomers
  that are adjacent on the lattice).

  Args:
      sequence: String of 'H' and 'P' monomers.

  Returns:
      List of (x, y) coordinates for each monomer.
  """
  n = len(sequence)
  # Initial heuristic: just lay it out in a straight line
  coordinates = []
  for i in range(n):
    coordinates.append((i, 0))
  return coordinates
# EVOLVE-BLOCK-END

def _is_valid_fold(coordinates):
  """Check if the fold is a valid self-avoiding walk."""
  n = len(coordinates)
  if len(set(coordinates)) != n:
    return False # Self-intersecting
  
  for i in range(n - 1):
    p1 = coordinates[i]
    p2 = coordinates[i + 1]
    dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
    if dist != 1:
      return False # Not adjacent on lattice
  return True

def _calculate_hh_contacts(sequence, coordinates):
  """Calculate the number of H-H contacts."""
  n = len(sequence)
  contacts = 0
  for i in range(n):
    if sequence[i] == 'H':
      for j in range(i + 2, n): # Non-consecutive
        if sequence[j] == 'H':
          p1 = coordinates[i]
          p2 = coordinates[j]
          dist = abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])
          if dist == 1:
            contacts += 1
  return contacts

def evaluate() -> dict[str, float]:
  """Evaluate the folding heuristic."""
  sequence = "HPHPPHHPHPPHHPPHPHHP"
  try:
    coordinates = fold_protein(sequence)
  except Exception:
    return {'scores_to_maximize': {'hh_contacts': -1e9}}

  if not isinstance(coordinates, list) or len(coordinates) != len(sequence):
     return {'scores_to_maximize': {'hh_contacts': -1e9}}
     
  # Convert to tuple of ints if they are not
  try:
    coordinates = [(int(x), int(y)) for x, y in coordinates]
  except Exception:
     return {'scores_to_maximize': {'hh_contacts': -1e9}}

  if not _is_valid_fold(coordinates):
    return {'scores_to_maximize': {'hh_contacts': -1e9}}

  contacts = _calculate_hh_contacts(sequence, coordinates)
  return {'scores_to_maximize': {'hh_contacts': float(contacts)}}
