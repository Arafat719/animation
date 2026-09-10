"""Read a saved fixture as a bounded, verified snapshot for the local API."""

import errno
import hashlib
import os
import stat
from dataclasses import dataclass

from animation_studio.providers.fake import Artifact, FakeConfig


FIXTURE_ROOT = FakeConfig().fixture_dir
MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
FIXTURE_MEDIA = {
    'image': ('sample_image.png', 'image/png', 'png'),
    'audio': ('silent_audio.wav', 'audio/wav', 'wav'),
    'video': ('sample_video.mp4', 'video/mp4', 'mp4'),
}


class ArtifactUnavailable(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class FixtureContent:
    body: bytes
    media_type: str
    extension: str


def load_fixture_artifact(artifact: Artifact) -> FixtureContent:
    """Allow only the provider's three fixtures, never a client/stored arbitrary path.

    Directory-relative opens reject symlinks and non-regular files on Linux.
    Hash verification and the response use the same bytes, so replacing a file
    after validation cannot change the content sent to the browser.
    """
    filename, media_type, extension = FIXTURE_MEDIA[artifact.kind]
    if artifact.path != FIXTURE_ROOT.absolute() / filename:
        raise ArtifactUnavailable(409, 'সংরক্ষিত media path অনুমোদিত নয়।')

    try:
        root_fd = os.open(FIXTURE_ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            file_fd = os.open(
                filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd,
            )
        finally:
            os.close(root_fd)
        try:
            info = os.fstat(file_fd)
            if not stat.S_ISREG(info.st_mode) or not 0 < info.st_size <= MAX_ARTIFACT_BYTES:
                raise ArtifactUnavailable(409, 'সংরক্ষিত media ফাইলটি বৈধ নয়।')
            with os.fdopen(file_fd, 'rb', closefd=False) as source:
                body = source.read(MAX_ARTIFACT_BYTES + 1)
        finally:
            os.close(file_fd)
    except FileNotFoundError as error:
        raise ArtifactUnavailable(410, 'সংরক্ষিত media ফাইলটি আর পাওয়া যাচ্ছে না।') from error
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ArtifactUnavailable(409, 'সংরক্ষিত media path অনুমোদিত নয়।') from error
        raise ArtifactUnavailable(503, 'সংরক্ষিত media ফাইলটি এখন পড়া যাচ্ছে না।') from error

    if (not body or len(body) > MAX_ARTIFACT_BYTES
            or hashlib.sha256(body).hexdigest() != artifact.sha256):
        raise ArtifactUnavailable(409, 'সংরক্ষিত media ফাইলটি বদলে গেছে বা বৈধ নয়।')
    return FixtureContent(body, media_type, extension)
