"""Check formatting; exempt only the exact bytes of recorded pre-adoption debt."""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB_SUFFIXES = {'.js', '.jsx', '.mjs', '.cjs', '.ts', '.tsx', '.css', '.html', '.json'}


def source_files(root: Path, scope: str) -> list[str]:
    result = subprocess.run(
        ['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
        cwd=root,
        capture_output=True,
        check=True,
    )
    paths = sorted(set(result.stdout.decode().split('\0')) - {''})
    sources = []
    for name in paths:
        path = Path(name)
        if not (root / path).is_file():
            continue  # Deleted tracked files are not check inputs.
        if {'node_modules', 'dist', '.venv', 'output', 'data'} & set(path.parts):
            continue
        if scope == 'backend' and path.suffix == '.py':
            sources.append(name)
        elif scope == 'frontend' and (
            name == '.prettierrc.json'
            or (
                name.startswith(('apps/web/', 'scripts/'))
                and not name.startswith('apps/web/public/schemas/')
                and path.suffix in WEB_SUFFIXES
                and path.name != 'package-lock.json'
            )
        ):
            sources.append(name)
    return sources


def pending_files(root: Path, files: list[str], baseline: dict[str, str]) -> list[str]:
    return [
        name
        for name in files
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != baseline.get(name)
    ]


def check(root: Path, scope: str, strict: bool = False) -> int:
    files = source_files(root, scope)
    baseline = json.loads((root / '.format-baseline.json').read_text())[scope]
    pending = files if strict else pending_files(root, files, baseline)
    print(
        f'{scope}: checking {len(pending)} files; '
        f'{len(files) - len(pending)} unchanged legacy files exempted. '
        'Use --all to include legacy debt.',
        flush=True,
    )
    if not pending:
        return 0
    if scope == 'backend':
        command = [sys.executable, '-m', 'ruff', 'format', '--check']
    else:
        command = ['node', str(root / 'apps/web/node_modules/prettier/bin/prettier.cjs'), '--check']
    return subprocess.run([*command, *pending], cwd=root, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scope', choices=['backend', 'frontend'])
    parser.add_argument(
        '--all', action='store_true', help='Also check recorded legacy formatting debt'
    )
    args = parser.parse_args()
    try:
        return check(ROOT, args.scope, args.all)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Formatter check could not run: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
