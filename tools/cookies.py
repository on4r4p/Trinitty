#!/usr/bin/python3
from pathlib import Path

import g4f.debug
from g4f.cookies import set_cookies_dir, read_cookie_files


COOKIES = Path(__file__).resolve().parent / "har_and_cookies"


def main():
    cookies_dir = str(COOKIES)
    g4f.debug.logging = True
    set_cookies_dir(cookies_dir)
    read_cookie_files(cookies_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
