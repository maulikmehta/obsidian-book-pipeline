"""Shared longform authoring tools.

    python3 authoring/cli.py <command>

Run from a book directory - the one holding book.yml and Story/.

    skeleton [--emit-contract]   structure + ride, to Strategy/creative/skeleton.html
    link [--write]               link first mentions to character notes
    check                        character notes and act/chapter agreement
    init                         scaffold a new vault here
    --selftest                   run the kit's own tests
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from authoring import config, init as init_mod, linker, personas, skeleton


def selftest():
    from authoring.tests import (test_config, test_structure, test_personas,
                                 test_linker, test_skeleton, test_init,
                                 test_strip, test_structure_findings,
                                 test_benchmark)
    mods = [test_config, test_structure, test_personas, test_linker,
            test_skeleton, test_init, test_strip, test_structure_findings,
            test_benchmark]
    n = 0
    for m in mods:
        for t in m.TESTS:
            t(); n += 1
    print(f"selftest ok - {n} checks")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "init":
            init_mod.run(); return 0
        if cmd == "check-sync":
            from authoring import sync
            return sync.run()
        if cmd == "skeleton":
            if "--emit-contract" in argv:
                print(json.dumps(skeleton.from_manuscript(), ensure_ascii=False, indent=2))
            else:
                out_path = os.path.join(config.root(), "Strategy", "creative", "skeleton.html")
                if os.path.exists(out_path):
                    import re
                    with open(out_path, "r", encoding="utf-8") as f:
                        m = re.search(r'<meta name="kit-version" content="([^"]+)">', f.read())
                    if not m or m.group(1) != config.KIT_VERSION:
                        print(f"WARN: Strategy/creative/skeleton.html predates kit version {config.KIT_VERSION}. Regenerating...")
                print(f"wrote {skeleton.write()}")
            return 0
        if cmd == "link":
            linker.run("--write" in argv); return 0
        if cmd == "check":
            bad = personas.check()
            for v in bad:
                print(v)
            print(f"{len(bad)} violation(s)")
            return 1 if bad else 0
    except config.BookError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
