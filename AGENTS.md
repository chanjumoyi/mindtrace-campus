# Repository workflow

For every task that changes project files:

1. Before editing, run `git fetch origin --prune` and compare the current local branches with their upstream branches.
2. Pull available updates with a safe fast-forward-only strategy before applying new work. Never overwrite local or user changes to force a pull.
3. If the worktree contains unrelated changes, or if pulling/merging would cause conflicts, stop and report the conflict instead of discarding work.
4. After implementation and relevant checks pass, commit the intended files to the `moyi` branch and push `origin/moyi` first.
5. Then update `main`, merge `moyi` into `main` (prefer fast-forward when possible), rerun proportionate checks, and push `origin/main`.
6. Never commit private handwriting data, participant information, generated caches, credentials, or ignored files.
