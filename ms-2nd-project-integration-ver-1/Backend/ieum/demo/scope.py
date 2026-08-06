DEMO_MEETING_PREFIX = "demo-"


def scope_demo_meeting_id(meeting_id: str) -> str:
    if meeting_id.startswith(DEMO_MEETING_PREFIX):
        return meeting_id[:100]
    return f"{DEMO_MEETING_PREFIX}{meeting_id}"[:100]
