# OpenContextPath

This Sublime Text package allows you to quickly open files and folders from
anywhere within a text (e.g. a file, the build panel, etc.) by simply using the
context menu or a keyboard shortcut.

For example:

![Example usage][example]

## Installation

### Package Control

The easiest way to install is using Sublime Text's
[Package Control][package-control]:

- Open the `Command Palette` using the menu item `Tools` → `Command Palette…`
- Choose `Package Control: Install Package`
- Install `OpenContextPath`

### Download

- Download a [release][releases]
- Extract the package and rename it to `OpenContextPath`
- Copy the package into your `Packages` directory. You can find this using the
    menu item `Preferences` → `Browse Packages…`.

## Usage

There are multiple ways to open paths:

- Open the context menu on a path and choose "Open *file*"
- Position the cursor within a path and press
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd> (macOS:
    <kbd>⌘</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd>)
    - With this it is also possible to open many paths at the same time by using
        multiple selections
- Press <kbd>Ctrl</kbd>+<kbd>Shift</kbd> and double click a path

This works for both absolute and relative paths. See the "directories"
configuration option to specify which directories to search for relative paths.

## Configuration

To overwrite any of the default settings use the menu item `Preferences` →
`Package Settings` → `OpenContextPath`. There you can also find the default
keyboard and mouse bindings.

It is also possible to use project-specific settings which take precedence over
the global settings. For that, you must add "open_context_path" to the
"settings" key. Your project file should look similar to the following example:

```json
{
    "settings": {
        "open_context_path": {
            "directories": [
                "project-specific-directory"
            ]
        }
    }
}
```

### Settings

**directories**

This is a list of directories to search when processing relative paths. If you
want to be able to open files from a text that only includes their names or a
part of their path, add the directory that contains them here.

Specifying too many directories here can possibly lead to noticeable delays.

**patterns**

These regex patterns are used to match line and column numbers in the text
after a path to make it possible to open a file at the specified position. They
must be matched by the named groups *line* and *col* respectively.

For example, the default patterns match the line and column numbers in the text
*path:line:column* with the following regex (the column number is optional):

```
":(?P<line>\\d+)(?::(?P<col>\\d+))?"
```

**context**

This is the number of characters that will be searched in both directions
around the cursor to find a path. Increasing this number makes it possible to
find longer paths but will also significantly increase the amount of time it
takes to find a path.

The default value should be good enough to detect most paths and not produce
any noticeable delays.

[example]: https://raw.githubusercontent.com/mheinzler/OpenContextPath/master/docs/example.png
[package-control]: https://packagecontrol.io/installation
[releases]: https://github.com/mheinzler/OpenContextPath/releases
