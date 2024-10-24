# Releasing

1. Determine the next version. Try to follow [semantic versioning](https://semver.org/).
   Our public API is described in [the README](./README.md#versioning)
2. Create a branch named `release/vX.Y.Z`.
3. Update:
   - The version in [pyproject.toml](./pyproject.toml)
   - The [CHANGELOG](./CHANGELOG.md)
   - The **pre-commit** hooks: `pre-commit autoupdate`
4. Open a PR with the changes
5. When the PR is merged, created a tag on `main` with that version with a `v` prefix, e.g. `vX.Y.Z`.
6. Push the tag to Github, which will fire off the release workflow.
7. Create a release via [the Github interface](https://github.com/gadomski/stac-asset/releases).
