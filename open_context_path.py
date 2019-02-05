"""Open file paths at the current cursor position."""

import functools
import logging
import os
import re
from itertools import chain

import sublime
import sublime_plugin


platform = sublime.platform()
log = logging.getLogger("OpenContextPath")


class OpenContextPathCommand(sublime_plugin.TextCommand):
    """Open file paths at the current cursor position."""

    # the regex to split a text into individual parts of a possible path
    file_parts_unix = re.compile(
        r"((\w+|\.\.?)/*|\W)", re.IGNORECASE)
    file_parts_win = re.compile(
        r"([A-Z]:[/\\]+|(\w+|\.\.?)[/\\]*|\W)", re.IGNORECASE)

    file_parts = (file_parts_unix if platform != "windows" else file_parts_win)

    # the number of characters to analyze around the cursor
    context = 150

    def run(self, edit, event=None):
        """Run the command."""
        path = self.find_path(event)
        if path:
            self.open_path(path)

    def is_enabled(self, event=None):
        """Whether the command is enabled."""
        return bool(self.find_path(event))

    def is_visible(self, event=None):
        """Whether the context menu entry is visible."""
        return bool(self.find_path(event))

    def description(self, event=None):
        """Describe the context menu entry."""
        path = self.find_path(event)
        if path:
            return "Open " + os.path.basename(os.path.normpath(path))

        return ""

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
            if platform == "windows":
                # Sublime Text has trouble opening Windows paths without a
                # drive letter. We use abspath to fix that.
                drive, tail = os.path.splitdrive(path)
                if not drive:
                    path = os.path.abspath(path)

            log.debug("Opening file: %s", path)
            window.run_command("open_file", {
                "file": path
            })

    def get_directories(self):
        """Collect the current list of directories from the settings."""
        settings = sublime.load_settings("OpenContextPath.sublime-settings")
        view_settings = self.view.settings().get("open_context_path", {})

        # give the view settings precedence over the global settings
        dirs = view_settings.get("directories", [])
        dirs += settings.get("directories", [])

        # return a tuple because lists are not hashable and don't work with the
        # cache
        return tuple(dirs)

    def find_path(self, event=None):
        """Find a file path at the position where the command was called."""
        view = self.view

        if event:
            # extract the text around the event's position
            pt = view.window_to_text((event["x"], event["y"]))
        else:
            # extract the text around the cursor's position
            pt = view.sel()[0].a

        line = view.line(pt)
        begin = max(line.a, pt - self.context)
        end = min(line.b, pt + self.context)

        text = view.substr(sublime.Region(begin, end))
        col = pt - begin

        # get the current list of directories
        dirs = self.get_directories()

        return self.extract_path(text, col, dirs)

    @functools.lru_cache()
    def extract_path(self, text, cur, dirs):
        """Extract a file path around a cursor position within a text."""
        log.debug("Extracting from: %s^%s", text[:cur], text[cur:])
        log.debug("Directories: %s", dirs)

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
            # in case we haven't found the beginning of a path yet, it could be
            # that there is a file consisting of multiple parts in which case
            # we just need to blindly start testing for this possibility
            if path == "" or self.search_path(part, dirs):
                log.debug("Path: %s", part)
                existing_path = part

                # now find the longest path that can be constructed from all
                # the parts after this one
                new_path = existing_path
                for part in chain(before[i + 1:], after):
                    new_path += part
                    if self.search_path(new_path, dirs):
                        log.debug("Path: %s", new_path)
                        existing_path = new_path

                # we need to test this path again if we skipped that above
                if path != "" or self.search_path(existing_path, dirs):
                    log.debug("Found path: %s", existing_path)

                    # check if the cursor is actually inside the found path by
                    # summing up the elements before and within the path
                    len_before_path = len("".join(before[:i]))
                    if len_before_path + len(existing_path) >= cur:
                        # keep the longest path
                        if len(existing_path) > len(path):
                            log.debug("Best path: %s", existing_path)
                            path = existing_path

        if path:
            # search again to return the full path for relative paths
            return self.search_path(path, dirs)

        return None

    def search_path(self, path, dirs):
        """Search for an existing path (possibly relative to dirs)."""

        # ignore special directories with no separator
        if path in [".", ".."]:
            return None

        if platform == "windows":
            # disable UNC paths on Windows
            if path.startswith("\\\\"):
                return None

            # ignore spaces at the end of a path
            if path.endswith(" "):
                return None

        if os.path.isabs(path):  # absolute paths
            if os.path.exists(path):
                return path
        else:  # relative paths
            for dir in dirs:
                full_path = os.path.join(dir, path)
                if os.path.exists(full_path):
                    return full_path

        return None
