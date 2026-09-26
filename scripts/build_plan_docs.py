"""Generate focused plan excerpts; use --check to detect master-plan drift."""

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = 'AI_ANIMATION_STUDIO_CODEX_MASTER_PLAN.md'


def documents():
    source = (ROOT / MASTER).read_text()
    sections = {}
    matches = list(re.finditer(r'^## (\d+)\. .+$', source, re.M))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        sections[int(match[1])] = source[match.start() : end].strip()

    def phases(section, prefix):
        matches = list(re.finditer(r'^' + prefix + r' Phase (\d+) .+$', section, re.M))
        result = {}
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
            result[int(match[1])] = section[match.start() : end].strip()
        return result

    micro, rules = sections[6].split('### Micro-step শেষে', 1)
    steps = phases(micro, '###')
    details = phases(sections[7], '##')
    if set(steps) != set(range(11)) or set(details) != set(range(11)):
        raise ValueError('Expected all 11 phases in both step map and detailed requirements')
    common = sections[1].split('### বর্তমান অবস্থান')[0]
    result = {
        'rules.md': common
        + '\n\n### Micro-step শেষে'
        + rules
        + '\n\n'
        + '\n\n'.join(sections[n] for n in (9, 10, 11, 12)),
        'product.md': sections[2] + '\n\n' + sections[3],
        'architecture.md': sections[4],
        'contracts.md': sections[5],
        'models.md': sections[8],
    }
    for phase in range(11):
        result[f'phase-{phase}.md'] = steps[phase] + '\n\n' + details[phase]
    for name, body in result.items():
        # Excerpts live two directories below the original master.
        body = re.sub(
            r'(\]\()([^\s)]+)(\))',
            lambda m: m[0] if re.match(r'(?:[a-z]+:|/|#)', m[2]) else m[1] + '../../' + m[2] + m[3],
            body,
        )
        yield (
            name,
            (
                f'<!-- Generated from {MASTER}; do not edit directly. -->\n'
                '<!-- Refresh: python3 scripts/build_plan_docs.py -->\n\n' + body + '\n'
            ),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    output = ROOT / 'docs' / 'plan'
    stale = []
    for name, content in documents():
        path = output / name
        if args.check:
            if not path.exists() or path.read_text() != content:
                stale.append(name)
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    if stale:
        print('Stale plan excerpts: ' + ', '.join(stale))
        return 1
    print('Plan excerpts match.' if args.check else 'Generated 16 focused plan documents.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
