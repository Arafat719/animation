"""Application planning service, currently wired only to the offline mock."""

from animation_studio.domain.v1.story_plan import StoryPlan
from animation_studio.providers.planner import MockPlanner, PlannerRequest
from animation_studio.providers.planner_repair import RepairIssue, RepairProvider, repair_plan


class MockDraftProvider:
    """Unassembled deterministic drafts; no model, I/O or narrative claims."""

    def generate(self, request: PlannerRequest) -> str:
        return MockPlanner().base_plan(request).model_dump_json()

    def repair(
        self, request: PlannerRequest, previous_output: str, issues: tuple[RepairIssue, ...]
    ) -> str:
        return self.generate(request)


class PlannerService:
    """PlannerProvider-compatible boundary with validation and trait assembly.

    Review/approval remains the caller's responsibility. No live-provider timeout,
    cancellation or network retry is supplied by this synchronous service.
    """

    def __init__(self, provider: RepairProvider, *, max_retries: int = 0):
        if type(max_retries) is not int or not 0 <= max_retries <= 2:
            raise ValueError('max_retries must be an integer from 0 to 2')
        self.provider = provider
        self.max_retries = max_retries

    def plan(self, request: PlannerRequest) -> StoryPlan:
        return repair_plan(self.provider, request, max_retries=self.max_retries).plan
