---
type: Change
title: Handle pull/push failures
description: Failed git pull/push operations display an error notification instead of crashing the application.
tags: [bugfix, git, ui]
generated: { by: claude-code/claude-opus-5-5, at: 2026-09-29T15:58:32Z }
sources:
  - id: mainapp
    resource: /src/AllGitStatus/MainApp.py
  - id: local-git-source
    resource: /src/AllGitStatus/Sources/LocalGitSource.py
  - id: tests
    resource: /tests/MainApp_integration_test.py
---

# Summary

`action_PullSelected` and `action_PushSelected` now delegate to a shared `_ExecuteRemoteCommand` helper. The helper catches exceptions raised by the git command, displays them as an error notification titled with the command and repository name, and refreshes the repository regardless of outcome.[^mainapp] Repository name formatting was extracted into `_GetRepositoryName` so the notification title and the name column share it.

`AGENTS.md` was added to capture coding conventions for AI agents working in the repository.

# Motivation

`LocalGitSource.Pull` and `LocalGitSource.Push` raise `RuntimeError` when git exits with a non-zero code (for example, merge conflicts, rejected pushes, or authentication failures).[^local-git-source] The exception was previously unhandled, terminating the TUI and hiding the git output from the user.

# Details

- Notifications use `markup=False` because git output may contain brackets that Textual would otherwise interpret as markup.
- Notifications use a 30 second timeout so multi-line git output can be read.
- The repository is refreshed even on failure, since a partially completed pull or push may have modified repository state.

# Testing

A parametrized integration test covers both pull and push failures, asserting the notification arguments, that the repository is re-queried, and that the application remains running.[^tests]

[^mainapp]: src/AllGitStatus/MainApp.py
[^local-git-source]: src/AllGitStatus/Sources/LocalGitSource.py
[^tests]: tests/MainApp_integration_test.py
