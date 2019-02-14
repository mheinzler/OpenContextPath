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

    def run(self, edit, event=None):
        """Run the command."""
        paths = self.find_paths(event)
        for path, info in paths:
            self.open_path(path, info)

    def is_enabled(self, event=None):
        """Whether the command is enabled."""
        paths = self.find_paths(event)
        return len(paths) > 0

    def is_visible(self, event=None):
        """Whether the context menu entry is visible."""
        paths = self.find_paths(event)
        return len(paths) > 0

    def description(self, event=None):
        """Describe the context menu entry."""
        paths = self.find_paths(event)
        if paths:
            # only show the name of the first found path
            path, info = paths[0]
            desc = "Open " + os.path.basename(os.path.normpath(path))
            if info.get("line"):
                desc += " at line {}".format(info["line"])

            return desc

        return ""

    def want_event(self):
        """Whether we need the event data."""
        return True

    def open_path(self, path, info):
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

            # encode line and column numbers into the file path
            if info.get("line"):
                path += ":{}".format(info["line"])
                if info.get("col"):
                    path += ":{}".format(info["col"])

            log.debug("Opening file: %s", path)
            window.open_file(path, sublime.ENCODED_POSITION)

    def get_context(self):
        """Return the current context setting."""
        settings = sublime.load_settings("OpenContextPath.sublime-settings")
        view_settings = self.view.settings().get("open_context_path", {})

        # give the view settings precedence over the global settings
        context = view_settings.get("context", None)
        if not context:
            context = settings.get("context", 100)

        return context

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

    def get_patterns(self):
        """Collect the current list of patterns from the settings."""
        settings = sublime.load_settings("OpenContextPath.sublime-settings")
        view_settings = self.view.settings().get("open_context_path", {})

        # give the view settings precedence over the global settings
        patterns = view_settings.get("patterns", [])
        patterns += settings.get("patterns", [])

        return patterns

    def find_paths(self, event=None):
        """Find file paths at the position where the command was called."""
        view = self.view

        if event:
            # search the text around the event's position
            points = [view.window_to_text((event["x"], event["y"]))]
        else:
            # search the texts around all selections
            points = [sel.a for sel in view.sel()]

        return self.find_paths_at(points)

    def find_paths_at(self, points):
        """Find file paths at the given text positions."""
        view = self.view
        context = self.get_context()

        # get the current list of directories to search
        dirs = self.get_directories()

        # search for a path around each of the points
        paths = []
        for pt in points:
            # clip the text to the specified context
            line = view.line(pt)
            begin = max(line.a, pt - context)
            end = min(line.b, pt + context)

            text = view.substr(sublime.Region(begin, end))
            col = pt - begin

            # try to extract a path and match the text after for additional
            # information
            path, scope = self.extract_path(text, col, dirs)
            if path:
                info = self.match_patterns(text[scope[1]:])
                paths.append((path, info))

        return paths

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
        begin, end = 0, 0
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
                    len_existing_path = len(existing_path)
                    if len_before_path + len_existing_path >= cur:
                        # keep the longest path
                        if len_existing_path > len(path):
                            log.debug("Best path: %s", existing_path)
                            path = existing_path
                            begin = len_before_path
                            end = begin + len_existing_path

        if path:
            # search again to return the full path for relative paths
            return self.search_path(path, dirs), (begin, end)

        return None, None

    def match_patterns(self, text):
        """Match some text for additional information about a path."""
        log.debug("Matching patterns to: %s", text)

        # find the first matching pattern and return all named groups
        for pattern in self.get_patterns():
            match = re.match(pattern, text)
            if match:
                log.debug("Found groups: %s", match.groupdict())
                return match.groupdict()

        return {}

    def search_path(self, path, dirs):
        """Search for an existing path (possibly relative to dirs)."""

        # ignore special directories with no separator
        if path in [".", ".."]:
            return None

        if platform == "windows":
            # disable UNC paths on Windows
            if path.startswith("\\\\") or path.startswith("//"):
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
