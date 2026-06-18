"""SenseCraft Solution Spec — markdown parsing primitives for solution guides.

Extracted from the provisioning station engine as the first step of the
open-source split. Provides:

* ``markdown_parser`` — multilingual guide.md parser (structure validation,
  preset/step/target extraction, HTML rendering).
* ``md_ast`` — thin mistune-AST wrapper for structure-aware heading splitting.
* ``localized`` — the language-agnostic ``Localized`` container.
"""

from .localized import Localized

__all__ = ["Localized"]
