RANK_DEFINITIONS = (
    ("observer", "Observer", 0, 1, "eye"),
    ("source_scout", "Source Scout", 100, 2, "compass"),
    ("timeline_analyst", "Timeline Analyst", 300, 3, "clock"),
    ("evidence_curator", "Evidence Curator", 700, 4, "archive"),
    ("case_researcher", "Case Researcher", 1_400, 5, "search"),
    ("senior_researcher", "Senior Researcher", 2_500, 6, "landmark"),
    ("archivist", "Archivist", 4_500, 7, "key"),
)

RULE_DEFINITIONS = (
    ("email_verified", "Email verified", 20, None, True),
    ("profile_completed", "Profile completed", 10, None, True),
    ("external_evidence_added", "Public evidence source added", 10, 30, False),
    ("evidence_upload_completed", "Evidence upload completed", 12, 36, False),
    ("sourced_timeline_added", "Sourced timeline event added", 8, 32, False),
)

BADGE_DEFINITIONS = (
    (
        "first_citation",
        "First Citation",
        "You added your first qualifying public source.",
        "Add a public evidence link with a title and description.",
        "bookmark",
        1,
    ),
    (
        "timeline_builder",
        "Timeline Builder",
        "You organized ten sourced events into case timelines.",
        "Add 10 timeline events linked to evidence.",
        "clock",
        2,
    ),
    (
        "evidence_curator",
        "Evidence Curator",
        "You built a well-described public evidence library.",
        "Add 25 qualifying public evidence links.",
        "archive",
        3,
    ),
)
