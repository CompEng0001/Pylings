"""
theme.py: Theme configuration loader and style mapper for Pylings.

This module handles:
- Loading theme configuration from `.pylings.toml` or built-in `themes.toml`.
- Supporting custom or named themes.
- Falling back to the default theme if required keys are missing or errors occur.
- Providing a style mapping for use in UI components.
"""

from __future__ import annotations

import logging
from pathlib import Path
import toml
from toml import TomlDecodeError

log = logging.getLogger(__name__)

BASE_DIR = Path.cwd()
PYLINGS_TOML = BASE_DIR / ".pylings.toml"
THEMES_TOML = Path(__file__).parent / "config" / "themes.toml"


def load_theme_config() -> dict:
    """
    Load the theme configuration for Pylings.

    The function attempts to:
    - Read `.pylings.toml` to determine the selected theme name.
    - If `name = "custom"`, use the theme values provided inline in `.pylings.toml`.
    - Otherwise, load the theme by name from `themes.toml`.
    - Fallback to the default theme if the named theme is not found or an error occurs.

    Returns:
        dict: A dictionary containing the theme color values.
    """
    theme_name = "default"
    theme_config: dict = {}

    if PYLINGS_TOML.exists():
        try:
            config = toml.load(PYLINGS_TOML)
            theme_section = config.get("theme", {}) or {}
            theme_name = str(theme_section.get("name", "default"))
            if theme_name == "custom":
                theme_config = theme_section
                log.debug("theme_name: %s", theme_name)
        except (TomlDecodeError, PermissionError, OSError) as e:
            # Syntax errors in TOML or I/O/permission issues
            log.warning("Failed to load .pylings.toml: %s", e)

    if theme_name != "custom":
        try:
            themes = toml.load(THEMES_TOML)
            # fall back to 'default' key if named theme is absent
            theme_config = themes.get(theme_name, themes.get("default", {}))
        except (TomlDecodeError, FileNotFoundError, PermissionError, OSError) as e:
            log.error("Failed to load themes.toml: %s", e)
            theme_config = {}

    log.debug("theme_config: %s", theme_config)
    return theme_config


def apply_theme_styles(theme_config: dict) -> dict:
    """
    Generate style strings and values from the theme configuration.

    The function:
    - Validates the presence of required keys in the theme config.
    - Falls back to the default theme if keys are missing.
    - Returns a dictionary of style values for use in markup or UI rendering.

    Args:
        theme_config (dict): The theme configuration dictionary.

    Returns:
        dict: A dictionary mapping style names (e.g. 'GREEN', 'RED') to string values.
    """
    required_keys = ["GREEN", "RED", "ORANGE", "LIGHT_BLUE", "BACKGROUND"]

    missing_keys = [key for key in required_keys if key not in theme_config]
    if missing_keys:
        log.warning(
            "Theme config missing keys: %s. Falling back to default theme.",
            missing_keys,
        )
        try:
            themes = toml.load(THEMES_TOML)
            theme_config = themes.get("default", {})
        except (TomlDecodeError, FileNotFoundError, PermissionError, OSError) as e:
            log.error("Failed to load default theme from themes.toml: %s", e)
            theme_config = {}

    return {
        "GREEN": f"{theme_config.get('GREEN', '#c9d05c')}",
        "RED": f"{theme_config.get('RED', '#f43753')}",
        "ORANGE": f"{theme_config.get('ORANGE', '#dc9656')}",
        "LIGHT_BLUE": f"{theme_config.get('LIGHT_BLUE', '#b3deef')}",
        "BACKGROUND": theme_config.get("BACKGROUND", "#1e1e2e"),
    }
