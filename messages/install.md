# OpenContextPath

This Sublime Text package allows you to quickly open files and folders from
anywhere within a text (e.g. a file, the build panel, etc.) by simply using the
context menu or a keyboard shortcut.

## Usage

There are multiple ways to open paths:

- Open the context menu on a path and choose "Open *file*"
- Position the cursor within a path and press
    <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd> (macOS:
    <kbd>⌘</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd>)
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
