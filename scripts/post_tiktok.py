#!/usr/bin/env python3
"""TikTok only. Kept so existing instructions keep working; the Post run now uses
scripts/post_postproxy.py, which posts TikTok and YouTube together (runs/post.md step 3b).

Usage:  python3 scripts/post_tiktok.py <entry_id> [--dry-run]
"""
import sys

import post_postproxy


def main(argv):
    return post_postproxy.main(argv, platforms=("tiktok",))


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main(sys.argv[1:]))
