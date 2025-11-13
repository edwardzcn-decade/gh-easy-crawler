# For Human

> If you are codex agent. You can skip this section.

Learning from [AGENTS.md from OpenAI-codex](https://github.com/openai/codex/blob/main/AGENTS.md).

You can find basic usage of Codex (e.g. Codex CLI/IDE-extension/Cloud/SDK)
from the [OpenAI Developers Codex Documentations](https://developers.openai.com/codex/cloud/code-review).

Here mainly use code review attached to GitHub repository.
We add this file as a repo-specific guidance for codex agent to know.

To be considered, `AGENTS.md` must be in the `cwd` of the session, or in
one of the parent folders up to a Git/filesystem root (whichever is
encountered first).

# Python/core

In the `core` folder where the main logic of REST APIs client implementations and gh APIs client implementations live:

- Install any commands the repo relies on if they aren't already available before running instructions.
- The implementations progress in both sides maybe different (REST APIs faster than gh APIs). Give a simple summary of the gap in short.
- Never add or modify any code related to environment setting. If you think the values or the names are wrong, describe it in conversation/comments.

