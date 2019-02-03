"""Test path detection."""

import re

from itertools import accumulate
from unittest import mock, TestCase

from OpenContextPath.open_context_path import OpenContextPathCommand


class BaseTestCase(TestCase):
    """Base test case for path detection."""

    def setUp(self):
        """Set up the test environment."""
        self.command = OpenContextPathCommand(None)

    def extract_paths(self, tests):
        """Run the command's extract_path on multiples texts."""

        # test the paths with our own os.path.exists
        with mock.patch("os.path.exists",
                        side_effect=self.path_exists):
            for text, path in tests:
                # extract the cursor position
                cur = text.index("^")
                text = text.replace("^", "")

                extract = self.command.extract_path(text, cur, ())
                self.assertEqual(extract, path,
                                 "text={} with cur={}".format(text, cur))

    def path_exists(self, path):
        """Check whether some virtual path exist."""
        return path in self.paths


class TestPathsUnix(BaseTestCase):
    """Test path detection on Unix."""

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

            ("/root/dir1/file1.txt^:42:10", "/root/dir1/file1.txt"),
            ("File '/root/dir1/^file1.txt', line 42", "/root/dir1/file1.txt"),  # noqa: E501

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


class TestPathsWindows(BaseTestCase):
    """Test path detection on Windows."""

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

            ("C:\\dir1/file^1.txt:42:10", "C:\\dir1/file1.txt"),
            ("File '^C:/dir1\\file1.txt', line 42", "C:/dir1\\file1.txt"),

            ("C:\\dir1\\file1.txt ^", None),
            ("C:\\dir1\\file1^", None),
            ("C:\\dir1\\no^file", None),
            ("C:\\nodir\\file^1.txt", None)
        ])

    def path_exists(self, path):
        """Check whether some virtual path exist."""

        # Windows allows slashes and backslashes
        path = path.replace("/", "\\")

        return path in self.paths
