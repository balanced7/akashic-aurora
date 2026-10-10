# Releasing the `aurora` CLI

How a release is cut, what it publishes, and how users get it. The flow follows openai/codex's `rust-release.yml`. Master keeps working versions. A release is one commit that bumps them, plus an annotated tag on that commit. The tag triggers [`.github/workflows/release.yml`](../.github/workflows/release.yml), which refuses a tag that its files disagree with.

## What a release is made of

| asset | built from | used by |
|---|---|---|
| `aurora-X.Y.Z.tar.gz` and its `.sha256` | `scripts/release/build_bundle.py`: the repo tree at the tag (`git archive`), minus `apps/` | the launcher, which fetches it on first use and checks the sha256 |
| `akashic_aurora_cli-X.Y.Z-py3-none-any.whl` and its sdist | `uv build --package akashic-aurora-cli` (`aurora-cli/`) | the install scripts, `uv tool install`, `pipx install` (PyPI) |
| `akashic_aurora_rs-X.Y.Z-cp311-abi3-<platform>.whl` | maturin, one per platform (`aurora-rs/py/`) | the launcher, which adds it to the bundle's environment when it exists for the platform |
| `install.sh`, `install.ps1` | `aurora-cli/install/` | the one-liners: `releases/latest/download/install.sh` |

## Cutting a release

```bash
uv run scripts/release/releases.py bump 0.2.0        # aurora-cli/pyproject.toml + aurora-rs/Cargo.toml, relocks
git commit -am "chore(release): 0.2.0"               # through the usual PR
git tag -a v0.2.0 -m v0.2.0 && git push origin v0.2.0
```

The workflow then runs these jobs:

1. **tag-check:** `releases.py check-tag` fails unless every version file says the tag's version.
2. **bundle** and **rust-wheels:** build every asset in the table above. The Rust wheels cover Linux x86_64 and aarch64, macOS x86_64 and arm64, and Windows x64.
3. **smoke:** on Linux, macOS and Windows, run the real install script against the assets this run built. Then run the advertised commands from outside any checkout (`self version`, `discover`, `status`, `learn`, `recall`, `hooks status`, `setup --dry-run`).
4. **release:** `gh release create`, with every asset attached and notes from `releases.py notes` (the conventional commits since the last tag).
5. **pypi:** `uv publish` with trusted publishing for `akashic-aurora-cli` and `akashic-aurora-rs`. The bundle stays on GitHub.

To rebuild and smoke-test an existing tag without publishing, run the workflow by hand (`workflow_dispatch`) with that tag.

### One-time setup

- **PyPI:** add a trusted publisher for `akashic-aurora-cli` and for `akashic-aurora-rs`. Point each at this repository, workflow `release.yml`, environment `pypi`. Until this is done, the `uv`, `pipx` and `uvx` install lines have nothing to install. The `curl` and PowerShell lines work from the first GitHub release.
- **GitHub:** create the `pypi` environment. Add required reviewers if a human should approve each publish.

## Versions

- **Format:** `X.Y.Z` only, with no pre-release suffixes. That one spelling is valid for Cargo and PyPI, and it maps straight onto the `vX.Y.Z` tag the launcher downloads from.
- **One launcher, one bundle:** a launcher fetches the bundle of its own version. Upgrading the launcher (`aurora self update`, `uv tool upgrade`, or re-running an install script) is how users upgrade Aurora.
- **State is not versioned:** bundles live in `~/.aurora/versions/X.Y.Z`. Memory lives in `~/.aurora/data`, which no upgrade touches. `aurora self prune` deletes old bundles.

## Testing a release locally

```bash
uv run scripts/release/build_bundle.py --out /tmp/rel            # bundle from HEAD
uv build --package akashic-aurora-cli --wheel --out-dir /tmp/rel
AURORA_RELEASE_BASE=/tmp/rel sh aurora-cli/install/install.sh --version "$(uv run scripts/release/releases.py version)"
```

`AURORA_RELEASE_BASE` points the installer and the launcher at a directory, or at any URL that holds the assets. The CI job `install-smoke` runs exactly this on every push. Set `HOME` to a scratch directory to keep the test away from your real `~/.aurora` and harness settings. Set `AKASHIC_WORLD=alpha` so its writes go to the alpha world's Redis port, not a live prod one.

## Rust

[`aurora-rs/README.md`](../aurora-rs/README.md) covers when a hot path moves to Rust, and how. The version in `aurora-rs/Cargo.toml` is a release version like the others, and `releases.py` keeps it in step.
