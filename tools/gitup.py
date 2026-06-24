#!/usr/bin/python3
from github import Github


def main():
    gitobj = Github()
    repo_trinitty = gitobj.get_repo("on4r4p/trinitty")
    commit = repo_trinitty.get_commits()

    for c in commit:
        print(c)

    print()
    last_trinitty = commit[1].sha
    next_trinitty = commit[0].sha

    print("last_trinitty:", last_trinitty)
    print("next_trinitty:", next_trinitty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
