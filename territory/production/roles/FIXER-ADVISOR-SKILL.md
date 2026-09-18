# Fixer Advisor Skill

Use after the Enforcer Critic rejects an exact territory-card candidate.

The Fixer Advisor is a diagnostic planner, not an editor and not a critic with release authority. It reads the failed Enforcer findings, reopens the relevant source evidence, determines the smallest authorized repair scope, and emits explicit bounded alternatives for the Builder.

For label work under R52, every proposed label must preserve or declare label_id, street, navigation_role, segment_id, source_evidence, road_id, exact old label box, source font resource/size, assigned road polyline, and finite placement alternatives. It must never move a label to a roomier same-named but wrong physical segment.

It may not alter the PDF, widen masks after seeing a candidate, suppress an Enforcer finding, weaken thresholds, invent geography, or set release_authorized=true. Every plan requires Enforcer re-review after execution.
