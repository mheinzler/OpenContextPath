"""Logging module."""

import logging

import sublime


log = logging.getLogger("OpenContextPath")


def update_logger():
    """Update the logger based on the current settings."""
    settings = sublime.load_settings("OpenContextPath.sublime-settings")

    # set the verbosity level
    if settings.get("debug", False):
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.INFO)


def plugin_loaded():
    """Initialize the logger."""
    update_logger()

    # track any changes to the settings
    settings = sublime.load_settings("OpenContextPath.sublime-settings")
    settings.add_on_change("logging", update_logger)


def plugin_unloaded():
    """Clean up."""

    # remove our settings handler
    settings = sublime.load_settings("OpenContextPath.sublime-settings")
    settings.clear_on_change("logging")
