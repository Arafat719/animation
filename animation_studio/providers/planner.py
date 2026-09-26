"""Replaceable synchronous planning boundary and deterministic local mock."""

import hashlib
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animation_studio.domain.duration import PlanDuration, split_duration
from animation_studio.domain.v1.story_plan import PlanCharacter, ShotPlan, StoryPlan, Text


class PlannerCharacter(PlanCharacter):
    """Caller-supplied visual profile; persistence/extraction belongs to Phase 5."""

    visual_traits: list[Text] = Field(min_length=1, max_length=100)
    negative_traits: list[Text] = Field(default_factory=list, max_length=100)


def inject_character_traits(plan: StoryPlan, characters: list[PlannerCharacter]) -> StoryPlan:
    """Return an independent, validated plan with only visible profiles injected.

    Apply once to base prompts. Overflow is rejected, never silently truncated.
    Offscreen dialogue alone does not make a character visually relevant.
    """
    profiles = {c.id: PlannerCharacter.model_validate(c.model_dump()) for c in characters}
    if len(profiles) != len(characters):
        raise ValueError('Character profile IDs must be unique')
    if not profiles.keys() <= {c.id for c in plan.characters}:
        raise ValueError('Character profiles must reference the plan cast')
    data = plan.model_dump()
    for shot in data['shots']:
        visible = [profiles[cid] for cid in shot['visible_character_ids'] if cid in profiles]
        for field, attribute in (
            ('image_prompt', 'visual_traits'),
            ('motion_prompt', 'visual_traits'),
            ('negative_prompt', 'negative_traits'),
        ):
            blocks = [shot[field]] if shot[field] else []
            for character in visible:
                traits = getattr(character, attribute)
                if traits:
                    blocks.append(f'{character.name} [{character.id}]: ' + '; '.join(traits))
            shot[field] = '\n'.join(blocks)
    return StoryPlan.model_validate(data)


class PlannerRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid', frozen=True, str_strip_whitespace=True)

    prompt: str = Field(min_length=1, max_length=4000)
    seed: int = Field(default=0, ge=0, le=2**32 - 1)
    duration_seconds: PlanDuration = 30.0
    characters: list[PlannerCharacter] = Field(default_factory=list, max_length=100)

    @model_validator(mode='after')
    def unique_character_ids(self):
        if len({c.id for c in self.characters}) != len(self.characters):
            raise ValueError('Character IDs must be unique')
        return self


class PlannerProvider(Protocol):
    def plan(self, request: PlannerRequest) -> StoryPlan:
        """Return a schema-valid plan; invalid requests raise ValidationError."""
        ...


class MockPlanner:
    """Timed 30–60 second template, not semantic interpretation or real AI.

    No clock, random state, filesystem, database or network is used. Each call
    returns independent models. Whitespace-normalized prompt and seed determine
    stable shot IDs/seeds, including across interpreter restarts.
    """

    def plan(self, request: PlannerRequest) -> StoryPlan:
        request = PlannerRequest.model_validate(request.model_dump())
        return inject_character_traits(self.base_plan(request), request.characters)

    def base_plan(self, request: PlannerRequest) -> StoryPlan:
        """Unassembled draft for the validated service; retains stable mock IDs."""
        # Revalidate even model_construct/model_copy inputs at the provider boundary.
        request = PlannerRequest.model_validate(request.model_dump())
        # Preserve the default 30-second IDs/seeds from step 3.2.
        exclude = {'duration_seconds'} if request.duration_seconds == 30 else set()
        if not request.characters:
            exclude.add('characters')
        fingerprint = hashlib.sha256(
            request.model_dump_json(exclude=exclude).encode('utf-8')
        ).hexdigest()
        durations = split_duration(request.duration_seconds)
        cast = (
            [PlanCharacter(id=c.id, name=c.name) for c in request.characters]
            if request.characters
            else [PlanCharacter(id='mock-protagonist', name='Mock protagonist')]
        )
        shots = []
        beats = (
            ('Wide', 'Establish the scene'),
            ('Medium', 'The protagonist enters'),
            ('Close-up', 'The protagonist notices a detail'),
            ('Medium', 'The protagonist pauses'),
            ('Wide', 'The protagonist moves forward'),
            ('Wide', 'The scene settles'),
        )
        # Extend the middle beat while retaining the closing beat.
        beats = beats[:-1] + (beats[-2],) * (len(durations) - 6) + beats[-1:]
        for order, ((framing, action), duration) in enumerate(zip(beats, durations), start=1):
            shot_hash = hashlib.sha256(f'{fingerprint}:{order}'.encode('ascii')).hexdigest()
            shots.append(
                ShotPlan(
                    id=f'mock-{shot_hash[:24]}',
                    order=order,
                    duration_seconds=duration,
                    camera_framing=framing,
                    camera_movement='Static',
                    background='Simple illustrated outdoor setting',
                    action=action,
                    lighting='Soft daylight',
                    visible_character_ids=[c.id for c in cast],
                    dialogue=[],
                    image_prompt=request.prompt,
                    negative_prompt='',
                    motion_prompt=action,
                    seed=int(shot_hash[:8], 16),
                )
            )
        plan = StoryPlan(
            schema_version=1,
            logline=request.prompt,
            setting='Mock outdoor scene',
            mood='Calm',
            visual_style='2D Japanese anime',
            characters=cast,
            shots=shots,
            estimated_total_duration_seconds=request.duration_seconds,
        )
        return plan
