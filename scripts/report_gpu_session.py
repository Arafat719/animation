"""Read a historical local mock session without recovery or provider calls.

Run from the repository root: python -m scripts.report_gpu_session --help
"""

import argparse
import sys
from pathlib import Path

from animation_studio.providers.gpu_attempts import LocalAttemptLedger


def main(argv=None):
    parser = argparse.ArgumentParser(description='সংরক্ষিত local/mock session-এর read-only report')
    parser.add_argument('--ledger', required=True, type=Path, help='বিদ্যমান ledger file')
    parser.add_argument('--render-id', required=True, help='মূল render ID')
    args = parser.parse_args(argv)
    try:
        report = LocalAttemptLedger(args.ledger).session_report(render_id=args.render_id)
    except FileNotFoundError:
        print('Ledger file পাওয়া যায়নি; কোনো file তৈরি করা হয়নি।', file=sys.stderr)
        return 2
    except (OSError, ValueError):
        # Validation errors can contain raw input; never echo ledger data or paths.
        print('Ledger পড়া যায়নি অথবা তথ্য অবৈধ; ফল অজানা।', file=sys.stderr)
        return 2
    if report is None:
        print('এই render-এর durable session record নেই; cleanup অবস্থা অজানা।')
        return 1
    compute = {'running': 'চলমান', 'stopped': 'বন্ধ', 'absent': 'অনুপস্থিত', 'unknown': 'অজানা'}
    storage = {'none': 'নেই', 'retained': 'রয়ে গেছে', 'unknown': 'অজানা'}
    print('সংরক্ষিত mock তথ্য; বর্তমান GPU বা billing যাচাই হয়নি।')
    print(f'Cleanup observation: {"সংরক্ষিত" if report.source == "saved" else "অজানা"}')
    print(f'Compute: {compute[report.compute]}')
    print(f'Storage: {storage[report.storage]}')
    print(f'সংরক্ষিত admission: {"বন্ধ" if report.closed else "বন্ধ হিসেবে লেখা নেই"}')
    print(f'Cleanup attempt: {report.cleanup_attempts}')
    print(f'সংরক্ষিত cleanup সম্পূর্ণ: {"হ্যাঁ" if report.complete else "না"}')
    if report.storage != 'none':
        print('Storage-এর বর্তমান অবস্থা যাচাই বাকি; billing বন্ধ ধরে নেবেন না।')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
