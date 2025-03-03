#!/usr/bin/env bash

# If your GitHub fork has diverged too much to be automatically merged, 
# you’ll need to manually sync it. Here’s a way to do it:
# Add the upstream repository:

git remote add upstream https://github.com/bguan/pylele.git

# Check it’s added with git remote -v.
# Fetch changes from the upstream:

git fetch upstream

# Rebase your fork's main branch onto the upstream main branch:

git checkout main
git rebase upstream/main

# Resolve any conflicts that come up during the rebase.
# Force-push the rebased changes to your fork:

git push origin main --force

# This process updates your fork to match the upstream while preserving your commits on top.