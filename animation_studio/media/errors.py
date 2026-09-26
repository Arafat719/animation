"""Safe user-facing composer failures and conservative storage preflight."""

import errno
import shutil
import subprocess
from pathlib import Path

from animation_studio.media.export import export_bundle


class ComposerError(Exception):
    def __init__(self, code: str, message: str, status: int = 422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def storage_error(error: OSError) -> ComposerError:
    if error.errno in (errno.ENOSPC, errno.EDQUOT):
        return ComposerError('disk_full', 'ডিস্কে পর্যাপ্ত জায়গা নেই। জায়গা খালি করে আবার চেষ্টা করুন।', 507)
    return ComposerError(
        'storage_error', 'ফাইল পড়া বা সংরক্ষণ করা যাচ্ছে না। অনুমতি ও স্টোরেজ পরীক্ষা করুন।', 500
    )


def checked_export(clips, destination, **options):
    """Translate failures without returning private paths or subprocess stderr."""
    try:
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            raise ComposerError('dependency_missing', 'ভিডিও তৈরির FFmpeg প্রস্তুত নেই।', 503)
        sources = [Path(p) for p in clips]
        sources += [
            Path(options[key]) for key in ('dialogue', 'background') if options.get(key) is not None
        ]
        if any(not source.is_file() for source in sources):
            raise ComposerError(
                'media_missing', 'প্রয়োজনীয় media ফাইল পাওয়া যায়নি। ফাইলটি ফিরিয়ে দিয়ে আবার চেষ্টা করুন।'
            )
        parent = Path(destination).absolute().parent
        while not parent.exists():
            parent = parent.parent
        # Minimum headroom, not a guarantee for arbitrary durations/resolutions.
        required = max(64 * 1024 * 1024, sum(p.stat().st_size for p in sources) * 8)
        if shutil.disk_usage(parent).free < required:
            raise ComposerError('disk_full', 'ডিস্কে পর্যাপ্ত জায়গা নেই। জায়গা খালি করে আবার চেষ্টা করুন।', 507)
        return export_bundle(clips, destination, **options)
    except ComposerError:
        raise
    except subprocess.CalledProcessError as error:
        stderr = error.stderr or b''
        if isinstance(stderr, bytes):
            stderr = stderr.decode('utf-8', errors='replace')
        if 'No space left on device' in stderr or 'Disk quota exceeded' in stderr:
            raise ComposerError(
                'disk_full',
                'ভিডিও সংরক্ষণের সময় ডিস্কের জায়গা শেষ হয়েছে। জায়গা খালি করে আবার চেষ্টা করুন।',
                507,
            ) from error
        raise ComposerError(
            'media_invalid', 'Media ফাইলটি নষ্ট বা format সমর্থিত নয়। বৈধ ফাইল দিয়ে আবার চেষ্টা করুন।'
        ) from error
    except FileNotFoundError as error:
        raise ComposerError(
            'media_missing', 'প্রয়োজনীয় media ফাইল আর পাওয়া যাচ্ছে না। আবার চেষ্টা করুন।'
        ) from error
    except FileExistsError as error:
        raise ComposerError(
            'destination_exists', 'এই export folder আগে থেকেই আছে। নতুন folder বেছে নিন।', 409
        ) from error
    except OSError as error:
        raise storage_error(error) from error
    except ValueError as error:
        raise ComposerError(
            'invalid_settings', 'Export settings বা subtitle timing সঠিক নয়। পরীক্ষা করে আবার চেষ্টা করুন।'
        ) from error
    except RuntimeError as error:
        raise ComposerError(
            'input_changed', 'Export চলাকালে input বদলে গেছে। ফাইল স্থির রেখে আবার চেষ্টা করুন।', 409
        ) from error
