**Project:**
[![License](https://img.shields.io/github/license/davidbrownell/AllGitStatus?color=dark-green)](https://github.com/davidbrownell/AllGitStatus/blob/master/LICENSE)

**Package:**
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/AllGitStatus?color=dark-green)](https://pypi.org/project/AllGitStatus/)
[![PyPI - Version](https://img.shields.io/pypi/v/AllGitStatus?color=dark-green)](https://pypi.org/project/AllGitStatus/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/AllGitStatus)](https://pypistats.org/packages/allgitstatus)

**Development:**
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![CI](https://github.com/davidbrownell/AllGitStatus/actions/workflows/CICD.yml/badge.svg)](https://github.com/davidbrownell/AllGitStatus/actions/workflows/CICD.yml)
[![Code Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/davidbrownell/f15146b1b8fdc0a5d45ac0eb786a84f7/raw/AllGitStatus_code_coverage.json)](https://github.com/davidbrownell/AllGitStatus/actions)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/davidbrownell/AllGitStatus?color=dark-green)](https://github.com/davidbrownell/AllGitStatus/commits/main/)

<!-- Content above this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Contents
- [Overview](#overview)
- [Installation](#installation)
- [Development](#development)
- [Additional Information](#additional-information)
- [License](#license)

## Overview
`AllGitStatus` is a [Text-based user interface](https://en.wikipedia.org/wiki/Text-based_user_interface) (TUI) that checks the git status for all repositories found under the specified directory. It can be used to quickly understand the status of multiple repositories stored under the same common ancestor. Additionally, it can be used to pull or push changes to/from a remote when changes are detected.

<img width="1611" height="974" alt="screenshot" src="https://github.com/user-attachments/assets/881c7686-51a5-4e3f-93d6-e1699fa6a7ea" />

[Screenshot of `AllGitStatus`]


https://github.com/user-attachments/assets/332f21a7-b56c-40e8-a33b-d56c079aab64

[Demo of `AllGitStatus`]


### How to use `AllGitStatus`

`AllGitStatus` can be run directly via [uv](https://github.com/astral-sh/uv) or installed as a python package.

#### Running with `uv`

Ensure that `uv` is installed and available on the path. Instructions on installing `uv` are available at https://docs.astral.sh/uv/#installation.

| Command Line | Scenario |
| --- | --- |
| `uvx AllGitStatus` | To run using the current directory as the root of all git repositories. |
| `uvx AllGitStatus <path to directory>` | To run using the specified directory as the root of all git repositories. |

#### Running as a python package

Install `AllGitStatus` as a python package using the [instructions below](#installation).

| Command Line | Scenario |
| --- | --- |
| `AllGitStatus` | To run using the current directory as the root of all git repositories. |
| `AllGitStatus <path to directory>` | To run using the specified directory as the root of all git repositories. |

<!-- Content below this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Installation

| Installation Method | Command |
| --- | --- |
| Via [uv](https://github.com/astral-sh/uv) | `uv add AllGitStatus` |
| Via [pip](https://pip.pypa.io/en/stable/) | `pip install AllGitStatus` |

### Verifying Signed Artifacts
Artifacts are signed and verified using [py-minisign](https://github.com/x13a/py-minisign) and the public key in the file `./minisign_key.pub`.

To verify that an artifact is valid, visit [the latest release](https://github.com/davidbrownell/AllGitStatus/releases/latest) and download the `.minisign` signature file that corresponds to the artifact, then run the following command, replacing `<filename>` with the name of the artifact to be verified:

```shell
uv run --with py-minisign python -c "import minisign; minisign.PublicKey.from_file('minisign_key.pub').verify_file('<filename>'); print('The file has been verified.')"
```

## Development
Please visit [Contributing](https://github.com/davidbrownell/AllGitStatus/blob/main/CONTRIBUTING.md) and [Development](https://github.com/davidbrownell/AllGitStatus/blob/main/DEVELOPMENT.md) for information on contributing to this project.

## Additional Information
Additional information can be found at these locations.

| Title | Document | Description |
| --- | --- | --- |
| Code of Conduct | [CODE_OF_CONDUCT.md](https://github.com/davidbrownell/AllGitStatus/blob/main/CODE_OF_CONDUCT.md) | Information about the norms, rules, and responsibilities we adhere to when participating in this open source community. |
| Contributing | [CONTRIBUTING.md](https://github.com/davidbrownell/AllGitStatus/blob/main/CONTRIBUTING.md) | Information about contributing to this project. |
| Development | [DEVELOPMENT.md](https://github.com/davidbrownell/AllGitStatus/blob/main/DEVELOPMENT.md) | Information about development activities involved in making changes to this project. |
| Governance | [GOVERNANCE.md](https://github.com/davidbrownell/AllGitStatus/blob/main/GOVERNANCE.md) | Information about how this project is governed. |
| Maintainers | [MAINTAINERS.md](https://github.com/davidbrownell/AllGitStatus/blob/main/MAINTAINERS.md) | Information about individuals who maintain this project. |
| Security | [SECURITY.md](https://github.com/davidbrownell/AllGitStatus/blob/main/SECURITY.md) | Information about how to privately report security issues associated with this project. |

## License
`AllGitStatus` is licensed under the <a href="https://choosealicense.com/licenses/MIT/" target="_blank">MIT</a> license.
