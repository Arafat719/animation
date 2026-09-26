"""Pure shot lifecycle transitions for planning pipelines.

No provider execution, persistence, approval or artifact verification occurs here.
Callers own the current snapshot and must serialize updates before saving it.
"""

from typing import Literal

from animation_studio.domain.v1.story_plan import ShotError, StoryPlan

ShotStatus = Literal['pending', 'running', 'completed', 'failed', 'cancelled']

_ALLOWED = {
    'pending': frozenset({'running', 'cancelled'}),
    'running': frozenset({'completed', 'failed', 'cancelled'}),
    'failed': frozenset({'running', 'cancelled'}),
    'completed': frozenset(),
    'cancelled': frozenset(),
}


class IllegalShotTransition(ValueError):
    """The requested lifecycle edge is not allowed."""


class UnknownShotError(LookupError):
    """The requested shot does not belong to the supplied plan."""


def transition_shot(
    plan: StoryPlan,
    shot_id: str,
    target: ShotStatus,
    *,
    error: ShotError | None = None,
) -> StoryPlan:
    """Return a validated independent snapshot, or leave the input untouched.

    Starting (including an explicit retry) increments attempts and clears the
    previous error. Failure requires a structured error; other targets forbid it.
    Completed/cancelled shots are terminal; repeated commands are rejected.
    Completion records caller-reported success, not proof of verified media.
    """
    snapshot = StoryPlan.model_validate(plan.model_dump(warnings=False))
    shot = next((shot for shot in snapshot.shots if shot.id == shot_id), None)
    if shot is None:
        raise UnknownShotError(f'Unknown shot: {shot_id}')
    if not isinstance(target, str) or target not in _ALLOWED[shot.status]:
        raise IllegalShotTransition(f'Illegal shot transition: {shot.status} -> {target}')
    if target == 'failed':
        if error is None:
            raise ValueError('Failed transition requires a structured error')
        validated_error = ShotError.model_validate(error.model_dump(warnings=False))
    else:
        if error is not None:
            raise ValueError('Only a failed transition accepts an error')
        validated_error = None
    shot.status = target
    shot.error = validated_error
    if target == 'running':
        shot.attempts += 1
    return StoryPlan.model_validate(snapshot.model_dump())
