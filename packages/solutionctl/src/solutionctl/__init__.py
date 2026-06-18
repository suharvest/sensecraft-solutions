"""solutionctl — thin public-side client for the SenseCraft Solution engine.

Contains zero engine code; only locates the engine binary and drives it.
"""

from .engine_locator import EngineNotFoundError, locate_engine

__all__ = ["locate_engine", "EngineNotFoundError"]
__version__ = "0.1.0"
