<!-- python_development Version: 0.8.0 -->

# File Format
Adhere to these principles when writing files.

- Line endings for new content should match the line endings in the rest of the file. When creating a new file, match the convention for the other files in the repository.

# Architectural Principles
Adhere to these architectural principles when planning and writing code.

- Don't Repeat Yourself (DRY)
- SOLID design principles
- Generate the least amount of code possible
- Never modify code associated with the system under test when writing tests.

# Documentation
Adhere to these principles when generating code comments or documentation.

- Do not introduce documentation for code that is common or easily understood.
- Explain why code was introduced, not what the code is doing.
- Generate short, crisp documentation rather than verbose prose.

# Static Analysis/Linting Errors
Do not suppress static analysis/linting-style errors; attempt to address the problem instead. Consult the human if the problem cannot be properly addressed.

# Python Development
Adhere to these conventions when writing python code.

## General
Run `python`-related tasks using `uv`.

## Naming
Use these conventions when writing python code:

- Class names use `PascalCase`.
- Function and method names use `PascalCase`.
- Variables use `snake_case`.
- Filenames use `snake_case` (but this is not required).

## Type Annotations
Adhere to these conventions when adding type annotations to python code.

- Do not use `Any` in production code; use `object` instead.
- Never introduce `from __future__ import annotations`.

## Dependencies
Use these conventions when managing python dependencies:

- Add dependencies via `uv add <package name>`; do not specify an explicit version so that the latest version of the package is applied.
- Add development-only dependencies via `uv add --dev <package name>`.
- Upgrade an existing dependency via `uv add --upgrade <package name>`.

## Testing
Use these conventions when writing or exercising tests:

- Run tests on the command line via `uv run pytest`; do not attempt to change the directory before running the tests.
- Never write tests for private functionality or class members (these are entities whose name begins with `_`).
- All tests must assert functionality.
- Never remove code to make tests pass.
- Compare entire strings when asserting that strings are equal.
- Use `textwrap.dedent` to compare strings with multiple lines.

## Imports
Order imports according to this example:

1. Python library module imports (if any).
2. Python library from imports (if any).
3. 3rd party module imports (if any).
4. 3rd party from imports (if any).
5. Package imports (if any).

Separate each section with a blank line.

```python
import os
import sys

from pathlib import Path

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager
from dbrownell_Common import TextwrapEx

from MyPackage import my_functionality
```

## Documentation
Use these conventions when generating code comments or documentation.

- Generate short docstrings.