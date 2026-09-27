# Retention-audit worktree cache cleanup — 2026-09-27

Removed only these explicitly authorized, regenerable directories in `/home/junhongli/projects/laya-render-measurement-semantics`:

| Directory | Files | Bytes |
| --- | ---: | ---: |
| `.pytest_cache` | 5 | 13,963 |
| `embodied_runtime/__pycache__` | 8 | 91,783 |
| `embodied_runtime/adapters/__pycache__` | 5 | 31,736 |
| `embodied_runtime/experiments/__pycache__` | 39 | 494,984 |
| `tests/__pycache__` | 16 | 177,158 |

Total: 73 files, 809,624 bytes. `git ls-files` found zero tracked files under the targets; a process file-descriptor check found none open there. The worktree remained clean after removal. No source, test, raw run, image, tensor, model or experiment evidence was removed. Later imports/tests may regenerate these caches.

The canonical maintenance directory retains the complete pre-removal file/hash inventory and completed receipt:

- `runs/maintenance/retention-audit-cache-cleanup-20260927-01.before.json`
- `runs/maintenance/retention-audit-cache-cleanup-20260927-01.json`, SHA-256 `4e4ae612217e89208f956654441ab930c215de934aa0cae94ab0e1f1bb1aab75`

Both are under `/home/junhongli/projects/laya-embodied-runtime`. This is a maintenance record, not scientific evidence or additional authority.
