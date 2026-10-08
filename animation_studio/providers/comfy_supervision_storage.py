"""Separate mock/live supervision stores guarded by the generation job's lock.

No cleanup dispatch. Missing sidecar means unknown cleanup,
not permission to retry. Generation journals (including legacy v1) are untouched.
"""

import os
import stat
import tempfile

from animation_studio.providers.comfy_storage import ComfyJournalStore, LiveComfyJournalStore
from animation_studio.providers.comfy_supervision import (
    MAX_OBSERVATION_BYTES,
    ComfySupervisionObservation,
    LiveComfySupervisionObservation,
    parse_live_supervision_observation,
    parse_supervision_observation,
)


class ComfySupervisionStore:
    """Caller holds the supplied journal's locked() across operations.

    Reuses its private root checks, permanent lock inode and thread ownership.
    Root ancestors remain caller-trusted. Updates require explicit legal transitions.
    """

    _observation_type = ComfySupervisionObservation
    _parse = staticmethod(parse_supervision_observation)

    def __init__(self, journal: ComfyJournalStore):
        if type(journal) is not ComfyJournalStore:
            raise TypeError('Expected mock journal store')
        self._journal = journal

    @property
    def path(self):
        return self._journal.path.with_suffix('.supervision.json')

    def read(self) -> ComfySupervisionObservation | None:
        """None only for absent sidecar; corrupt/incompatible data raises."""
        self._journal._require_lock()
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return None
        with os.fdopen(fd, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('Invalid supervision file')
            content = stream.read(MAX_OBSERVATION_BYTES + 1)
        return self._parse(content, self._journal._context)

    def create(self, observation: ComfySupervisionObservation) -> ComfySupervisionObservation:
        self._journal._require_lock()
        if os.path.lexists(self.path):
            raise ValueError('Supervision record exists; must not overwrite')
        return self._write(observation)

    def transition(self, observation: ComfySupervisionObservation) -> ComfySupervisionObservation:
        """Reserve one attempt or finish it; never retry unknown/observed cleanup.

        A successful intent write is not dispatch. After restart even intent blocks
        another reservation. Missing sidecar is not implicit permission to act.
        """
        self._journal._require_lock()
        if type(observation) is not self._observation_type:
            raise TypeError('Expected supervision observation')
        candidate = self._parse(observation.model_dump_json().encode(), self._journal._context)
        current = self.read()
        if current is None:
            raise ValueError('Missing supervision record; cleanup outcome unknown')
        allowed = {
            'not_requested': {'intent'},
            'intent': {'observed', 'unknown'},
        }
        if candidate.cleanup_phase not in allowed.get(current.cleanup_phase, set()):
            raise ValueError('Cleanup transition or retry forbidden')
        if (
            candidate.attempt_count != 1
            or candidate.created_at != current.created_at
            or candidate.updated_at < current.updated_at
            or candidate.primary_outcome != current.primary_outcome
            or (current.prompt_id is not None and candidate.prompt_id != current.prompt_id)
        ):
            raise ValueError('Cleanup identity, outcome or timeline changed')
        generation = self._journal.read()
        if generation.state != 'accepted' or candidate.prompt_id != generation.prompt_id:
            raise ValueError('Cleanup requires matching accepted generation receipt')
        return self._write(candidate)

    def _write(self, observation: ComfySupervisionObservation) -> ComfySupervisionObservation:
        self._journal._require_lock()
        if type(observation) is not self._observation_type:
            raise TypeError('Expected supervision observation')
        content = observation.model_dump_json().encode('utf-8')
        if len(content) > MAX_OBSERVATION_BYTES:
            raise ValueError('Supervision record too large')
        validated = self._parse(content, self._journal._context)
        fd, name = tempfile.mkstemp(prefix='.comfy-supervision-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
            directory = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.lexists(name):
                os.unlink(name)
        return validated


class LiveComfySupervisionStore(ComfySupervisionStore):
    """Standalone live v2 bookkeeping; no cleanup dispatcher or evidence verifier.

    The same filename/lock prevents mock sidecars being bypassed by mode changes.
    Existing v1 mock bytes are rejected unchanged, never automatically migrated.
    """

    _observation_type = LiveComfySupervisionObservation
    _parse = staticmethod(parse_live_supervision_observation)

    def __init__(self, journal: LiveComfyJournalStore):
        if type(journal) is not LiveComfyJournalStore:
            raise TypeError('Expected live journal store')
        self._journal = journal
