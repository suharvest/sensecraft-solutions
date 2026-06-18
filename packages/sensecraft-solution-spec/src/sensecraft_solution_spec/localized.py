"""
Language-agnostic localization container.

This module provides the Localized[T] type for storing values in multiple languages
without hardcoding specific language pairs like en/zh.
"""

from typing import Dict, Generic, List, Optional, TypeVar

T = TypeVar("T")


class Localized(Generic[T]):
    """Language-agnostic localization container.

    Stores values for multiple languages without hardcoding specific language pairs.
    Supports any number of languages and provides fallback behavior.

    Usage:
        title = Localized({"en": "Hello", "zh": "你好", "ja": "こんにちは"})
        title.get("zh")  # "你好"
        title.get("ja", fallback="en")  # "こんにちは"
        title.get("fr", fallback="en")  # "Hello" (fallback)

    Type parameter:
        T: The type of value stored (e.g., str, list[str], etc.)
    """

    def __init__(self, values: Optional[Dict[str, T]] = None):
        """Initialize with optional pre-populated values.

        Args:
            values: Dict mapping language codes to values
        """
        self._values: Dict[str, T] = values.copy() if values else {}

    def get(self, lang: str, fallback: str = "en") -> Optional[T]:
        """Get value for specified language with fallback.

        Args:
            lang: Target language code (e.g., "en", "zh", "ja")
            fallback: Fallback language if target not found (default: "en")

        Returns:
            The value for the target language, or fallback language, or None
        """
        value = self._values.get(lang)
        if value is not None:
            return value
        # Try fallback language
        return self._values.get(fallback)

    def set(self, lang: str, value: T) -> None:
        """Set value for a specific language.

        Args:
            lang: Language code
            value: The value to store
        """
        self._values[lang] = value

    def has(self, lang: str) -> bool:
        """Check if a value exists for the specified language.

        Args:
            lang: Language code to check

        Returns:
            True if a non-None value exists for this language
        """
        return lang in self._values and self._values[lang] is not None

    @property
    def languages(self) -> List[str]:
        """Return list of available language codes."""
        return list(self._values.keys())

    def to_dict(self) -> Dict[str, T]:
        """Serialize to a plain dictionary.

        Returns:
            Copy of the internal values dict
        """
        return self._values.copy()

    @classmethod
    def from_dict(cls, data: Dict[str, T]) -> "Localized[T]":
        """Create a Localized instance from a dictionary.

        Args:
            data: Dict mapping language codes to values

        Returns:
            New Localized instance
        """
        return cls(data)

    @classmethod
    def from_value(cls, value: T, lang: str = "en") -> "Localized[T]":
        """Create a Localized instance with a single language value.

        Args:
            value: The value to store
            lang: The language code (default: "en")

        Returns:
            New Localized instance with one language
        """
        return cls({lang: value})

    # Compatibility properties for gradual migration
    @property
    def en(self) -> Optional[T]:
        """Get English value (compatibility property)."""
        return self._values.get("en")

    @property
    def zh(self) -> Optional[T]:
        """Get Chinese value (compatibility property)."""
        return self._values.get("zh")

    def __repr__(self) -> str:
        return f"Localized({self._values})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Localized):
            return self._values == other._values
        return False

    def __bool__(self) -> bool:
        """Return True if any language has a value."""
        return any(v is not None for v in self._values.values())
