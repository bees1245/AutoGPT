# Repository Layers on a Shared Branch

This note interprets the prompt "Repo layers of the same branch to close all" as guidance for consolidating parallel development layers that target a single Git branch. The goal is to reduce fragmentation, surface conflicts early, and deliver a cohesive change set.

## Conceptual interpretation

1. **Repo layers** – Treat each layer as an independent workstream (feature flag, worktree, or directory) that builds toward the same branch tip.
2. **Same branch** – All layers ultimately merge into one canonical branch (e.g., `main` or a feature branch shared by the team).
3. **Close all** – Finish, reconcile, or archive the layers so that no dangling work remains outside the canonical branch.

## Practical workflow

1. **Identify active layers**
   - List open worktrees, forks, or feature directories that target the branch.
   - Review open pull requests and local branches to map outstanding work.

2. **Evaluate readiness**
   - Confirm each layer has passing tests, updated documentation, and a clear review path.
   - Rebase or merge the branch tip into the layer to surface conflicts early.

3. **Consolidate**
   - Merge or cherry-pick the completed work into the shared branch.
   - Close related PRs once their commits are merged.
   - Delete temporary branches or worktrees to prevent divergence.

4. **Verify closure**
   - Run the branch-wide test suite after consolidation.
   - Tag the release or update the changelog if the work represents a milestone.
   - Communicate the closure to stakeholders so everyone switches to the updated branch.

5. **Repository hygiene**
   - Archive or delete stale feature branches both locally and remotely.
   - Rotate credentials or tokens used exclusively by the retired layers.
   - Update automation (CI workflows, release scripts, dashboards) so they no longer reference the retired workstreams.

## Tooling checklist

- `git worktree list` – Audit parallel checkouts.
- `git branch --merged <branch>` – Identify branches safe to delete.
- `git rebase` or `git merge` – Integrate changes.
- `git push --delete origin <branch>` – Remove remote branches after consolidation.
- Issue tracker or PR dashboard – Ensure tickets linked to each layer are closed.

## Key takeaways

- Keep parallel layers short-lived; regularly synchronize them with the canonical branch.
- Close layers decisively once merged to minimize maintenance overhead.
- Transparently document the closure process so collaborators can follow the single source of truth.
