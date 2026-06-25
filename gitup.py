#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from shutil import which
from urllib.request import urlopen


DEFAULT_REMOTE = "origin"
DEFAULT_BRANCH = "main"
PYPROJECT_VERSION_RE = re.compile(r'^\s*version\s*=\s*"([^"]+)"\s*$', re.MULTILINE)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def git_binary():
    git_bin = which("git")
    if not git_bin:
        raise RuntimeError("git executable was not found in PATH")
    return git_bin


def repo_root_from_script():
    return Path(__file__).resolve().parent


def run_git(args, repo_root, check=True):
    proc = subprocess.run(
        [git_binary(), *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and proc.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), proc.stderr.strip() or proc.stdout.strip()))
    return proc.stdout.strip()


def is_full_sha(value):
    return FULL_SHA_RE.fullmatch(str(value or "")) is not None


def rev_parse(ref, repo_root):
    value = run_git(["rev-parse", ref], repo_root)
    if not is_full_sha(value):
        raise RuntimeError("Invalid git SHA for %s: %s" % (ref, value))
    return value


def maybe_fetch(remote, branch, repo_root):
    proc = subprocess.run(
        [git_binary(), "fetch", "--quiet", remote, branch],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        print("Warning: git fetch failed: %s" % (proc.stderr.strip() or proc.stdout.strip()), file=sys.stderr)
        return False
    return True


def remote_head(remote, branch, repo_root):
    remote_ref = "%s/%s" % (remote, branch)
    try:
        return rev_parse(remote_ref, repo_root)
    except RuntimeError:
        output = run_git(["ls-remote", remote, "refs/heads/%s" % branch], repo_root)
        parts = output.split()
        if parts and is_full_sha(parts[0]):
            return parts[0]
        raise


def read_project_version(pyproject_file):
    try:
        text = pyproject_file.read_text()
    except OSError:
        return ""
    match = PYPROJECT_VERSION_RE.search(text)
    return match.group(1).strip() if match else ""


def version_key(version):
    parts = re.findall(r"\d+|[A-Za-z]+", str(version or ""))
    key = []
    for part in parts:
        if part.isdigit():
            key.append((1, int(part)))
        else:
            key.append((0, part.lower()))
    return key


def version_newer(latest_version, current_version):
    latest_key = version_key(latest_version)
    current_key = version_key(current_version)
    if not latest_key or not current_key:
        return False
    return latest_key > current_key


def pypi_latest_version(package_name, timeout=5):
    url = "https://pypi.org/pypi/%s/json" % package_name
    with urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("info", {}).get("version", "")).strip()


def latest_commits(repo_root, limit):
    return run_git(
        ["log", "--date=short", "--pretty=format:%h %cd %s", "-n", str(limit)],
        repo_root,
    ).splitlines()


def print_report(repo_root, remote, branch, limit, package_name, check_pypi):
    pyproject_file = repo_root / "pyproject.toml"
    local_sha = rev_parse("HEAD", repo_root)
    remote_sha = remote_head(remote, branch, repo_root)
    project_version = read_project_version(pyproject_file)
    latest_pypi_version = ""

    print("repo: %s" % repo_root)
    print("local HEAD:  %s" % local_sha)
    print("%s/%s: %s" % (remote, branch, remote_sha))
    print("pyproject:   %s" % (project_version or "missing"))

    if local_sha == remote_sha:
        print("git status:  local HEAD matches %s/%s" % (remote, branch))
    else:
        print("git status:  local HEAD differs from %s/%s" % (remote, branch))

    if check_pypi:
        try:
            latest_pypi_version = pypi_latest_version(package_name)
            print("PyPI latest: %s" % (latest_pypi_version or "missing"))
            if latest_pypi_version and project_version:
                if version_newer(latest_pypi_version, project_version):
                    print("PyPI status: local pyproject is behind PyPI")
                elif version_newer(project_version, latest_pypi_version):
                    print("PyPI status: local pyproject is ahead of PyPI")
                else:
                    print("PyPI status: local pyproject matches PyPI")
        except Exception as exc:
            print("Warning: PyPI version check failed: %s" % exc, file=sys.stderr)

    if limit > 0:
        print("\nlatest commits:")
        for line in latest_commits(repo_root, limit):
            print("  %s" % line)

    return {
        "local_sha": local_sha,
        "remote_sha": remote_sha,
        "project_version": project_version,
        "latest_pypi_version": latest_pypi_version,
    }


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Inspect Trinitty git state and PyPI version.")
    parser.add_argument("--repo-root", default=str(repo_root_from_script()), help="Repository root. Default: script dir.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help="Git remote to inspect. Default: origin.")
    parser.add_argument("--branch", default=DEFAULT_BRANCH, help="Remote branch to inspect. Default: main.")
    parser.add_argument("--no-fetch", action="store_true", help="Do not fetch before reading remote refs.")
    parser.add_argument("--no-pypi", action="store_true", help="Do not query PyPI for the latest published version.")
    parser.add_argument("--package", default="trinitty", help="PyPI package name to inspect. Default: trinitty.")
    parser.add_argument("--limit", type=int, default=5, help="Number of recent commits to print. Default: 5.")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    repo_root = Path(args.repo_root).resolve()

    if not args.no_fetch:
        maybe_fetch(args.remote, args.branch, repo_root)

    print_report(
        repo_root,
        args.remote,
        args.branch,
        max(args.limit, 0),
        args.package,
        not args.no_pypi,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
