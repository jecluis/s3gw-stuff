# Copyright (C) 2022 SUSE, LLC
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or (at
# your option) any later version.

import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

import requests


class GitError(Exception):
    msg: Optional[str]

    def __init__(self, msg: Optional[str] = None):
        self.msg = msg

    def __str__(self) -> str:
        return "" if self.msg is None else self.msg


def clone(repo: str, dest: Path) -> None:
    """
    Clone the specified repository into the provided destination.
    """
    if dest.exists():
        raise GitError(f"destination path '{dest}' already exists.")

    if not dest.parent.exists():
        dest.parent.mkdir(parents=True)

    cmd = ["git", "clone", repo, dest]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        raise GitError(f"error cloning repository: {p.stderr.decode('utf-8')}.")

    assert dest.exists()
    assert dest.joinpath(".git").exists()


def pr_exists(repo: str, pr_id: int) -> Dict[str, Any]:
    """
    Check whether a given PR exists for the provided repository. If not, raises
    error; otherwise, return response map.
    """
    # check pr exists
    req = requests.get(
        f"https://api.github.com/repos/aquarist-labs/{repo}/pulls/{pr_id}",
        headers={"Accept": "application/vnd.github+json"},
    )
    if req.status_code == 404:
        raise GitError(f"pull request '{pr_id}' not found at '{repo}.")
    elif req.status_code != 200:
        raise GitError("unknown error.")
    return req.json()


def fetch(wspath: Path, repo: str, origin: str, branch: str) -> str:
    """
    Fetch a branch from the specified origin.
    """
    repopath = wspath.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()

    localname = f"popcorn/{origin}/{branch}"

    cmd = ["git", "branch", "--show-current"]
    p = subprocess.run(
        cmd, cwd=repopath, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode != 0:
        raise GitError(f"error obtaining branch: {p.stderr}")

    cur_branch = p.stdout.decode("utf-8").strip()

    cmd = [
        "git",
        "fetch",
        origin,
        f"{branch}:{localname}",
    ]
    if cur_branch == localname:
        cmd = [
            "git",
            "pull",
            "--force",
            origin,
            f"{branch}:{localname}",
        ]

    p = subprocess.run(
        cmd,
        cwd=repopath,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise GitError(
            f"error fetching branch {branch} for repository {repo}: {p.stderr}"
        )
    return localname


def pr_fetch(repo: str, pr_id: int, wspath: Path) -> str:
    """
    Fetch a PR branch from a given repository.
    """
    return fetch(wspath, repo, "origin", f"pull/{pr_id}/head")


def clean_repo(path: Path, repo: str) -> None:
    """
    Clean up the provided repository, including submodules.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()

    cmd = [
        "git",
        "submodule",
        "foreach",
        "git clean -fdx",
    ]
    p = subprocess.run(
        cmd,
        cwd=repopath,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise GitError(
            f"error clearing repository {repo}'s submodules: {p.stderr}"
        )

    cmd = ["git", "clean", "-fdx"]
    p = subprocess.run(
        cmd,
        cwd=repopath,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise GitError(f"error clearing repository {repo}: {p.stderr}")


def checkout_branch(path: Path, repo: str, branch: str) -> None:
    """
    Checkout a branch on a given repository.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()

    cmd = ["git", "checkout", branch]
    p = subprocess.run(
        cmd,
        cwd=repopath.as_posix(),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise GitError(f"error checking out branch {branch}: {p.stderr}")


def get_latest_commit(path: Path, repo: str) -> str:
    """
    Obtain latest commit SHA from specified repository's checked out branch.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()
    cmd = ["git", "rev-parse", "--short", "HEAD"]
    p = subprocess.run(
        cmd, cwd=repopath, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode != 0:
        raise GitError(
            f"error obtaining latest commit on repository {repo}: {p.stderr}"
        )
    return p.stdout.decode("utf-8").strip()


def get_remotes(path: Path, repo: str) -> Dict[str, str]:
    """
    Obtain repository's remotes.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()
    cmd = ["git", "remote", "-v"]
    p = subprocess.run(
        cmd, cwd=repopath, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode != 0:
        raise GitError(
            f"error obtaining repository '{repo}' remotes: {p.stderr}"
        )
    outlst = p.stdout.decode("utf-8").splitlines()
    remotes: Dict[str, str] = {}
    for remote in outlst:
        name, url, rtype = remote.split()
        if "fetch" not in rtype:
            continue
        remotes[name] = url
    return remotes


def add_remote(path: Path, repo: str, name: str, remote: str) -> None:
    """
    Add a given name with provided url as a remote to a repository.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()
    cmd = ["git", "remote", "add", name, f"{remote}/{repo}"]
    p = subprocess.run(
        cmd, cwd=repopath, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode != 0:
        raise GitError(
            f"error adding remote '{name}' to repository '{repo}': {p.stderr}"
        )


def update(path: Path, repo: str, remote: Optional[str] = None) -> None:
    """
    Update references, either for all remotes or for a provided remote.
    """
    repopath = path.joinpath(f"{repo}.git")
    assert repopath.exists()
    assert repopath.joinpath(".git").exists()
    cmd = ["git", "remote", "update"]
    if remote is not None:
        cmd.append(remote)
    p = subprocess.run(
        cmd, cwd=repopath, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if p.returncode != 0:
        print(p.stdout)
        raise GitError(f"error updating remotes: {p.stderr}")
