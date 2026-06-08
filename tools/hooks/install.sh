#!/usr/bin/env bash
# Install the dev-kit pre-commit hook into this repo's .git/hooks/.
set -eu
repo_root="$(git rev-parse --show-toplevel)"
hook_src="$repo_root/tools/hooks/pre-commit"
hook_dst="$repo_root/.git/hooks/pre-commit"

chmod +x "$hook_src"
if [ -e "$hook_dst" ] && [ ! -L "$hook_dst" ]; then
    echo "A pre-commit hook already exists at $hook_dst — backing it up to pre-commit.bak"
    mv "$hook_dst" "$hook_dst.bak"
fi
ln -sf "../../tools/hooks/pre-commit" "$hook_dst"
echo "✓ Installed pre-commit hook -> $hook_dst"
echo "  Runs preflight.py --strict + manifest_check.py on changed plugins."
echo "  Bypass once with: git commit --no-verify"
