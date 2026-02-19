STAGES = [
    "DRAFT",
    "VALIDATED",
    "PAPER_DEPLOYED",
    "LIVE_ELIGIBLE",
    "LIVE_ARMED",
]

def advance_stage(candidate: dict, target: str) -> dict:
    # TODO: model_versions / events 기록
    candidate["stage"] = target
    return candidate
