"""Simple dark/light theme support for Niobium CLI output."""

_STYLES = {
    "dark": {
        "accent": "cyan",
        "accent_bold": "bold cyan",
        "accent2": "yellow",
        "accent2_bold": "bold yellow",
        "success": "green",
        "success_bold": "bold green",
        "error": "bold red",
        "warn": "yellow",
        "muted": "dim",
        "muted_italic": "dim italic",
        "highlight": "bold",
        "banner_tagline": "white bold",
        "banner_subtitle": "dim light_steel_blue1 italic",
    },
    "light": {
        "accent": "dark_cyan",
        "accent_bold": "bold dark_cyan",
        "accent2": "dark_orange3",
        "accent2_bold": "bold dark_orange3",
        "success": "green4",
        "success_bold": "bold green4",
        "error": "bold red",
        "warn": "dark_orange3",
        "muted": "grey50",
        "muted_italic": "grey50 italic",
        "highlight": "bold",
        "banner_tagline": "bold",
        "banner_subtitle": "grey50 italic",
    },
}

_ANSI = {
    "dark": {
        "accent": "\033[33m",   # yellow
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    },
    "light": {
        "accent": "\033[34m",   # blue
        "bold": "\033[1m",
        "dim": "\033[90m",      # dark gray
        "reset": "\033[0m",
    },
}


class S:
    """Current theme styles. Access as S.accent, S.warn, etc."""
    pass


def set_theme(name):
    """Apply a theme by name. Unknown names fall back to 'dark'."""
    styles = _STYLES.get(name, _STYLES["dark"])
    for k, v in styles.items():
        setattr(S, k, v)
    S._name = name if name in _STYLES else "dark"


def ansi():
    """Get ANSI escape codes for the current theme (used by _pick)."""
    return _ANSI.get(getattr(S, "_name", "dark"), _ANSI["dark"])


# Initialize with dark theme as default
set_theme("dark")
