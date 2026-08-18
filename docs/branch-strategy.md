# Branch strategy, provenance and recovery

## Objective

The repository contained two materially different lines of development:

1. Axel Björk's original `Rush-Royale-Bot`, whose last upstream `main` commit is
   `f61f658459090c18b0d1f371bddc156dc0e823d7` from 17 November 2022.
2. The existing `mleem97/RushBot` fork, whose previous `main` head is
   `3f1d38349dbb37aca657724ca1cc7670ee771a07` from 20 July 2026.

The histories are divergent. Rewriting `main` onto upstream would make review and recovery
unnecessarily difficult. The modernization therefore uses independent, named reference
branches.

## Canonical branches

### `archive/pre-modernization-2026-08-18`

Exact snapshot of the previous fork head:

```text
3f1d38349dbb37aca657724ca1cc7670ee771a07
```

This branch is a recovery point and must not receive normal development commits.

### `upstream/axelbjork-main`

Exact local reference to Axel Björk's last upstream `main`:

```text
f61f658459090c18b0d1f371bddc156dc0e823d7
```

This branch is also immutable. If the original upstream changes in the future, create a new
reviewed sync commit or dated reference rather than force-moving this historical marker.

### `modernization/rushbot-2.0`

Development branch created directly from `upstream/axelbjork-main`. New components are added
in small, reviewable layers. Useful work from the old fork is migrated selectively after its
behavior and licensing are understood; the old branch is not blindly merged.

### `main`

The previous fork remains on `main` until RushBot 2 reaches an acceptance gate. Changing the
default branch is a separate administrative decision after the modernization branch passes
its device, screenshot-replay and live-device test matrix.

## Required GitHub protection

A repository administrator should create active branch rulesets for the two historical
branches. Target each exact branch name and enable at least:

- restrict updates;
- restrict deletions;
- block force pushes;
- no bypass except the repository owner for disaster recovery.

For `modernization/rushbot-2.0`, require pull requests and the `RushBot CI` checks before
merge. Direct pushes may remain temporarily available during initial scaffolding, but should
be removed once the first reviewable baseline is established.

## Recovery procedures

Verify the references:

```bash
git fetch origin --prune
git rev-parse origin/archive/pre-modernization-2026-08-18
git rev-parse origin/upstream/axelbjork-main
```

Create a local recovery branch from the archived fork:

```bash
git switch --create recovery/old-rushbot \
  origin/archive/pre-modernization-2026-08-18
```

Create a fresh modernization checkout without touching `main`:

```bash
git switch --create work/rushbot-2 \
  origin/modernization/rushbot-2.0
```

Do not run `git push --force`, `git push --mirror` or branch-deletion commands against the
archive or upstream reference.

## Migration rule

Every migration from the archived fork must answer four questions in its commit or pull
request:

1. Which behavior is being retained?
2. Which defect or compatibility issue is being removed?
3. How is the behavior tested without a live game account?
4. Does the change import copyrighted assets, credentials or private screenshots?

A change that cannot answer all four remains outside the modernization branch.
