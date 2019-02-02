"""Open file paths at the current cursor position."""

import functools
import logging
import os
import re
from itertools import chain

import sublime
import sublime_plugin


log = logging.getLogger("OpenContextPath")


class OpenContextPathCommand(sublime_plugin.TextCommand):
    """Open file paths at the current cursor position."""

    # the regex to split a text into individual parts of a possible path
    file_parts_unix = re.compile(r"(\w+/*|\W)", re.IGNORECASE)
    file_parts_win = re.compile(r"([A-Z]:[/\\]+|\w+[/\\]*|\W)", re.IGNORECASE)

    file_parts = (file_parts_unix if sublime.platform() != "windows"
                  else file_parts_win)

    # the number of characters to analyze around the cursor
    context = 150

    def run(self, edit, event):
        """Run the command."""
        path = self.find_path(event)
        self.open_path(path)

    def is_visible(self, event):
        """Whether the context menu entry is visible."""
        return bool(self.find_path(event))

    def description(self, event):
        """Describe the context menu entry."""
        path = self.find_path(event)
        return "Open " + os.path.basename(os.path.normpath(path))

    def want_event(self):
        """Whether we need the event data."""
        return True

    def open_path(self, path):
        """Open a file in Sublime Text or a directory with the file manager."""
        window = self.view.window()

        # normalize the path to adjust it to the system
        path = os.path.normpath(path)

        if os.path.isdir(path):
            log.debug("Opening directory: %s", path)
            window.run_command("open_dir", {
                "dir": path
            })
        else:
            log.debug("Opening file: %s", path)
            window.run_command("open_file", {
                "file": path
            })

    def find_path(self, event):
        """Find a file path at the position where the command was called."""
        view = self.view

        # extract the text around the event's position
        pt = view.window_to_text((event["x"], event["y"]))
        line = view.line(pt)
        begin = max(line.a, pt - self.context)
        end = min(line.b, pt + self.context)

        text = view.substr(sublime.Region(begin, end))
        col = pt - begin

        return self.extract_path(text, col)

    @functools.lru_cache()
    def extract_path(self, text, cur):
        """Extract a file path around a cursor position within a text."""
        log.debug("Extracting from: %s^%s", text[:cur], text[cur:])

        # split the text into possible parts of a file path before and after
        # the cursor position
        before = []
        after = []
        for match in re.finditer(self.file_parts, text):
            part = text[match.start():match.end()]
            if match.start() <= cur:
                before.append(part)
            else:
                after.append(part)

        log.debug("Before cursor: %s", before)
        log.debug("After cursor: %s", after)

        # go through the parts before the cursor to find the ones that mark the
        # beginning of a file path
        path = ""
        for i, part in reversed(list(enumerate(before))):
            if self.path_exists(part):
                log.debug("Path: %s", part)
                existing_path = part

                # now find the longest path that can be constructed from all
                # the parts after this one
                new_path = existing_path
                for part in chain(before[i + 1:], after):
                    new_path += part
                    if self.path_exists(new_path):
                        log.debug("Path: %s", new_path)
                        existing_path = new_path

                # check if the cursor is actually inside the found path by
                # summing up the elements before and within the path
                len_before_path = len("".join(before[:i]))
                if len_before_path + len(existing_path) >= cur:
                    # keep the longest path
                    if len(existing_path) > len(path):
                        path = existing_path

        return path

    def path_exists(self, path):
        """Check if a path exists."""

        # absolute paths
        if os.path.isabs(path) and os.path.exists(path):
            return True

        return False
