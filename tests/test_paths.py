"""Test path detection."""

import ntpath
import os
import posixpath
import re

from itertools import accumulate
from unittest import mock, TestCase

from OpenContextPath.open_context_path import OpenContextPathCommand


class BaseTestCase(TestCase):
    """Base test case for path detection."""

    def setUp(self):
        """Set up the test environment."""

        # mock a virtual view
        view = mock.Mock(**{
            # make the command use only the global settings
            "settings.return_value": {}
        })

        self.command = OpenContextPathCommand(view)

    def extract_paths(self, tests):
        """Run the command's extract_path on multiples texts."""

        # replace the whole os.path module
        with mock.patch.object(os, 'path', self.path_module):
            # test the paths with our own os.path.exists
            with mock.patch("os.path.exists", self.path_exists):
                for text, path, *tail in tests:
                    info = tail[0] if tail else {}

                    # extract the cursor position
                    cur = text.index("^")
                    text = text.replace("^", "")

                    # extract a path and parse the info
                    extract, scope = self.command.extract_path(
                        text, cur, self.directories)
                    matched_info = self.command.match_patterns(
                        text[scope[1]:]) if scope else {}

                    self.assertEqual(extract, path,
                                     "text={} with cur={}".format(text, cur))
                    if scope:
                        self.assertEqual(matched_info, info,
                                         "text={}".format(text[scope[1]:]))

    def path_exists(self, path):
        """Check whether some virtual path exist."""
        return os.path.normpath(path) in self.paths


class TestPathsUnix(BaseTestCase):
    """Test path detection on Unix."""

    # the path module we need for these tests
    path_module = posixpath

    # a list of files for which we pretend that they exist
    virtual_files = [
        "/root/dir1/file1.txt",
        "/root/dir2/sub/file2.txt",

        "/root/dir1/root/dir1/file1.txt"
    ]

    # create a list of possible paths from all virtual files
    paths = set([
        path for file in virtual_files for path in accumulate(
            comp for comp in re.split(r"(/)", file) if comp != ""
        )
    ])

    # search paths
    directories = ("/root", "/root/dir2/", "/root/dir2/sub")

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        self.command.file_parts = self.command.file_parts_unix

    def test_absolute_paths(self):
        """Testing absolute paths."""
        self.extract_paths([
            ("^/root/dir1/file1.txt", "/root/dir1/file1.txt"),
            ("/^root/dir1/file1.txt", "/root/dir1/file1.txt"),
            ("/root/dir1/file^1.txt", "/root/dir1/file1.txt"),
            ("/root/dir1/file1.txt^", "/root/dir1/file1.txt"),
            ("^/root/dir1/", "/root/dir1/"),
            ("^/root/dir1", "/root/dir1"),
            ("/root/dir2/su^b/file2.txt", "/root/dir2/sub/file2.txt"),

            ("/root/dir1/file1.txt^:42:10", "/root/dir1/file1.txt",
             {"line": "42", "col": "10"}),
            ("/root/dir1/file1.txt^:42", "/root/dir1/file1.txt",
             {"line": "42", "col": None}),
            ("File '/root/dir1/^file1.txt', line 42", "/root/dir1/file1.txt",
             {"line": "42"}),

            # the whole path must be found
            ("/root/dir1/root/dir1/file^1.txt", "/root/dir1/root/dir1/file1.txt"),  # noqa: E501

            # Windows drive letters and backslashes have no special meaning
            ("C:/root/dir1/file1.txt^", "/root/dir1/file1.txt"),
            ("/root/dir1/file1.txt^\\", "/root/dir1/file1.txt"),

            ("/root/dir1/file1.txt ^", None),
            ("/root/dir1/file1^", None),
            ("/root/dir1/no^file", None),
            ("/root/nodir/file^1.txt", None),
            ("\\root\\dir1\\file1.^txt", None)
        ])

    def test_relative_paths(self):
        """Testing relative paths."""
        self.extract_paths([
            ("./^", "/root/./"),
            ("../^", "/root/../"),
            ("dir1/file^1.txt", "/root/dir1/file1.txt"),
            ("/dir1/file^1.txt", "/root/dir1/file1.txt"),
            ("sub/file^2.txt", "/root/dir2/sub/file2.txt"),

            ("../root/dir^1/", "/root/../root/dir1/"),
            (".^./dir1/file1.txt", "/root/dir2/../dir1/file1.txt"),

            ("file^2.txt", "/root/dir2/sub/file2.txt"),
            ("/root/dir1/file^2.txt", "/root/dir2/sub/file2.txt"),

            ("^", None),

            # we don't want to detect dots without a path separator
            (".^", None),
            ("..^", None)
        ])


class TestPathsWindows(BaseTestCase):
    """Test path detection on Windows."""

    # the path module we need for these tests
    path_module = ntpath

    # a list of files for which we pretend that they exist
    virtual_files = [
        "C:\\dir1\\file1.txt",
        "C:\\dir2\\sub\\file2.txt"
    ]

    # create a list of possible paths from all virtual files
    paths = set([
        path for file in virtual_files for path in accumulate(
            comp for comp in re.split(r"(\\)", file) if comp != ""
        )
    ])

    # search paths
    directories = ("C:\\dir2", "C:\\", "C:\\dir2\\sub")

    def setUp(self):
        """Set up the test environment."""
        super().setUp()
        self.command.file_parts = self.command.file_parts_win

    def test_absolute_paths(self):
        """Testing absolute paths."""
        self.extract_paths([
            ("^C:\\dir1\\file1.txt", "C:\\dir1\\file1.txt"),
            ("C^:\\dir1\\file1.txt", "C:\\dir1\\file1.txt"),
            ("C:\\dir1\\file^1.txt", "C:\\dir1\\file1.txt"),
            ("C:\\dir1\\file1.txt^", "C:\\dir1\\file1.txt"),
            ("^C:\\dir1\\", "C:\\dir1\\"),
            ("^C:\\dir1", "C:\\dir1"),
            ("C:\\dir2\\su^b\\file2.txt", "C:\\dir2\\sub\\file2.txt"),

            ("C:\\dir1/file^1.txt:42:10", "C:\\dir1/file1.txt",
             {"line": "42", "col": "10"}),
            ("C:\\dir1/file^1.txt:42", "C:\\dir1/file1.txt",
             {"line": "42", "col": None}),
            ("File '^C:/dir1\\file1.txt', line 42", "C:/dir1\\file1.txt",
             {"line": "42"}),

            ("C:\\dir1\\file1.txt ^", None),
            ("C:\\dir1\\file1^", None),
            ("C:\\dir1\\no^file", None),
            ("C:\\nodir\\file^1.txt", None)
        ])

    def test_relative_paths(self):
        """Testing relative paths."""
        self.extract_paths([
            (".\\^", "C:\\dir2\\.\\"),
            ("../^", "C:\\dir2\\../"),
            ("dir1\\file^1.txt", "C:\\dir1\\file1.txt"),
            ("\\dir1\\file^1.txt", "C:\\dir1\\file1.txt"),
            ("sub/file^2.txt", "C:\\dir2\\sub/file2.txt"),

            ("..\\dir^2\\", "C:\\dir2\\..\\dir2\\"),
            (".^.\\dir1\\file1.txt", "C:\\dir2\\..\\dir1\\file1.txt"),

            ("file^2.txt", "C:\\dir2\\sub\\file2.txt"),
            ("C:\\dir1\\file^2.txt", "C:\\dir2\\sub\\file2.txt"),

            ("^", None),

            # we don't want to detect dots without a path separator
            (".^", None),
            ("..^", None)
        ])
