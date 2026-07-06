#!/usr/bin/env python3
"""
One-time Earth Engine authentication helper.

Opens a browser OAuth flow and stores credentials locally. After this succeeds,
set GEE_PROJECT_ID and run scripts/test_gee_pull.py.
"""

from __future__ import annotations

import ee


def main() -> None:
    print("Starting Earth Engine authentication...")
    print("A browser window should open. Sign in with your Google account.")
    print("Register your Cloud project at: https://code.earthengine.google.com/register")
    ee.Authenticate()
    print("\nAuthentication complete. Credentials saved locally.")
    print("Next steps:")
    print("  1. Copy .env.example to .env and set GEE_PROJECT_ID=your-project-id")
    print("  2. pip install -r python/requirements.txt")
    print("  3. python scripts/test_gee_pull.py")


if __name__ == "__main__":
    main()
