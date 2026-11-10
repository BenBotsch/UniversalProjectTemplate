"""Run Git in a local checkout.

Commands run without a shell and with a fixed argument list, so no value is ever interpreted by a
shell. Git uses the configuration of the checkout and the user, including hooks and commit
signing; nothing is bypassed.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class GitError(Exception):
    """A Git command failed or Git is not available."""


@dataclass(frozen=True)
class Git:
    """Git commands for one working tree.

    Args:
        root: Root directory of the working tree.
        executable: Path of the ``git`` program; found on ``PATH`` by :meth:`in_directory`.
    """

    root: Path
    executable: str

    @classmethod
    def in_directory(cls, root: Path) -> Git:
        """Return a :class:`Git` for ``root`` and check that it is the root of a working tree.

        Raises:
            GitError: If Git is not installed or ``root`` is not the top of a working tree.
        """
        executable = shutil.which("git")
        if executable is None:
            raise GitError("git is not installed or not on PATH")
        git = cls(root, executable)
        top = git.run("rev-parse", "--show-toplevel").strip()
        if Path(top).resolve() != root.resolve():
            raise GitError(f"{root} is not the root of a Git working tree (root is {top})")
        return git

    def run(self, *args: str) -> str:
        """Run ``git -C <root> <args>`` and return its standard output.

        Raises:
            GitError: If the command exits with a non-zero status.
        """
        try:
            # Fixed program and argument list without a shell; values cannot inject commands.
            result = subprocess.run(  # noqa: S603
                [self.executable, "-C", str(self.root), *args],
                capture_output=True,
                check=False,
            )
        except OSError as exc:
            raise GitError(f"cannot run git: {exc.strerror}") from exc
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", "replace").strip()
            raise GitError(f"git {args[0]} failed: {message}")
        return result.stdout.decode("utf-8", "replace")

    def tracked_files(self) -> list[str]:
        """Return the tracked files as sorted POSIX paths relative to the root."""
        output = self.run("ls-files", "-z")
        return sorted(path for path in output.split("\0") if path)

    def status(self) -> list[str]:
        """Return the short status lines: modified, staged and untracked files."""
        return [line for line in self.run("status", "--porcelain").splitlines() if line]

    def remote_url(self, name: str = "origin") -> str | None:
        """Return the URL of a remote, or ``None`` if it does not exist."""
        try:
            return self.run("remote", "get-url", name).strip()
        except GitError:
            return None

    def ref_exists(self, ref: str) -> bool:
        """Return whether ``ref`` names a commit, for example ``develop`` or ``origin/develop``."""
        try:
            self.run("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
        except GitError:
            return False
        return True

    def current_branch(self) -> str | None:
        """Return the checked-out branch, or ``None`` for a detached head."""
        try:
            return self.run("symbolic-ref", "--quiet", "--short", "HEAD").strip()
        except GitError:
            return None

    def create_branch(self, branch: str, start: str) -> None:
        """Create ``branch`` at ``start`` and check it out."""
        self.run("switch", "--create", branch, start)

    def stage_all(self) -> None:
        """Stage every change, including deletions."""
        self.run("add", "--all")

    def commit(self, message: str) -> str:
        """Commit the staged changes and return the new commit hash."""
        self.run("commit", "--quiet", "--message", message)
        return self.run("rev-parse", "HEAD").strip()
