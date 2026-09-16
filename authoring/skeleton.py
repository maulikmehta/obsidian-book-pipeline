#!/usr/bin/env python3
"""
PROXY SCRIPT: The Skeleton tool has been extracted into its own app container: StoryArc.
This file redirects backwards-compatible calls to the new location.
"""
import sys
import os

# Redirect imports: if someone does `from authoring import skeleton`
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/storyarc")))
from main import *

if __name__ == '__main__':
    # Forward execution to the new main
    import main
    sys.exit(main.main())
