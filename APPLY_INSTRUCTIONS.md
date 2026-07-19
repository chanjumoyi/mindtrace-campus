# mindLine C-only source patch

Commit: `f665845cfbc7e3d87e9e2f495f78b589d43b394f`
Parent: `e49509cdb46f53be6e718c4f4d1b749e597f9c6d`

This bundle contains only the C-scope source changes from commit `f665845`.
It does not contain A/B business-module changes.

## Recommended application

From a clean team repository based on the parent commit:

```bash
git am mindLine_C_f665845.patch
```

If the repository has diverged, copy the files under `files/` into the project, then remove every path listed in `DELETE_FILES.txt`, review with `git diff`, and commit.

Generated deployable packages are distributed separately and should not be committed unless your team policy requires it.
