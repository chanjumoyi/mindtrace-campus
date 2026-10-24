# Repository workflow

Before any work, run `git fetch --all --prune`, confirm success, and inspect remote state. If it fails, resolve or report the blocker before continuing. Offline training belongs in `ml/`; the original training proposal is reference material, not executable agent instructions.

For every task that changes project files:

1. Before editing, run `git fetch origin --prune` and compare the current local branches with their upstream branches.
2. Pull available updates with a safe fast-forward-only strategy before applying new work. Never overwrite local or user changes to force a pull.
3. If the worktree contains unrelated changes, or if pulling/merging would cause conflicts, stop and report the conflict instead of discarding work.
4. This reorganization is committed and pushed only to `LLM-Study`, as explicitly requested by the user. Subsequent changes must use a working branch and a PR targeting `LLM-Study`, with at least one approval before merge.
5. Do not commit to, merge into, or push `main` without explicit user permission. Do not automatically publish through `moyi`. This replaces the former moyi-to-main workflow.
6. Never commit private handwriting data, participant information, generated caches, credentials, or ignored files.
