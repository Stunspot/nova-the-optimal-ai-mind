"""Execute the pinned repository repair, then remove all temporary machinery."""

from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen


PINNED_IMPLEMENTATION = (
    "https://raw.githubusercontent.com/Stunspot/nova-the-optimal-ai-mind/"
    "e6c5d0892290eda55210cbc826f2f96e7f19cb7f/"
    "tools/one_time_mcp_removal_repair.py"
)


def run_pinned_repair() -> None:
    source = urlopen(PINNED_IMPLEMENTATION, timeout=30).read().decode("utf-8")
    namespace: dict[str, object] = {"__name__": "pinned_repository_repair"}
    exec(compile(source, PINNED_IMPLEMENTATION, "exec"), namespace)
    repair_main = namespace.get("main")
    if not callable(repair_main):
        raise RuntimeError("pinned repository repair does not expose main()")
    result = repair_main()
    if result not in (None, 0):
        raise RuntimeError(f"pinned repository repair returned {result!r}")


def guard_verifier_import() -> None:
    verifier = Path("tools/verify_package.py")
    text = verifier.read_text(encoding="utf-8")
    old = '''        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        observed_fingerprint = load_json(fingerprint_path)
'''
    new = '''        module = importlib.util.module_from_spec(spec)
        prior_dont_write_bytecode = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(module)
        finally:
            sys.dont_write_bytecode = prior_dont_write_bytecode
        observed_fingerprint = load_json(fingerprint_path)
'''
    if old not in text:
        raise RuntimeError("generated fingerprint import block was not found")
    verifier.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def remove_temporary_machinery() -> None:
    temporary_paths = (
        Path(".github/workflows/one-time-repository-repair.yml"),
        Path(".github/workflows/one-time-repository-repair-v2.yml"),
        Path("tools/REPAIR-RUNNER-V2-TEMPORARY.txt"),
        Path("tools/sitecustomize.py"),
        Path(__file__),
    )
    for path in temporary_paths:
        if path.exists():
            path.unlink()


def main() -> int:
    run_pinned_repair()
    guard_verifier_import()
    remove_temporary_machinery()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
