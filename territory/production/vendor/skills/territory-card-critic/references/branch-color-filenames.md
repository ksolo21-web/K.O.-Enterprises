# Branch labels, status paint, and delivery filenames

Apply to every newly reviewed or revised territory card. Reopen prior approval when a user identifies a defect; retain earlier evidence as history. A previous numeric pass never excuses a visible defect.

## Filenames only

Kaleb approved `Territory - 000Letters.pdf`: three-digit zero-padded number, immediately followed by the category and area letters, no intervening period or space. Uppercase A means Apartments; uppercase T means Telephone; lowercase a/b/c/etc identify subdivisions of one larger territory. Preserve combined category and area suffixes. Examples:28→`Territory - 028.pdf`, A29→`Territory - 029A.pdf`,31b→`Territory - 031b.pdf`,A31d→`Territory - 031Ad.pdf`,T42→`Territory - 042T.pdf`. Do not infer a telephone type from an untyped number. Do not rename the visible card identity or change assignments. No `Review`, `Final`, version number, or date in an individual delivery PDF filename unless the user later requests it. Internal masters and batch/audit archives can retain descriptive names. Resolve collisions by preserving source identity and version history, not by silently conflating cards. Use this rule in new and resumed chats whenever these skills are loaded; do not claim control over other active chats.

## Whole-branch readability

Audit the visible road network before marking names complete. Enumerate each navigationally distinct branch, loop, entrance stem and disconnected/status-separated run, including excluded roads useful for navigation. A name elsewhere on the same physical road is insufficient when the branch or entrance cannot be identified unambiguously at output size. Repeat the verified name beside the run where useful (A33 Grove Ln entrance and A31d southern Tribute Creek Blvd loop are regression examples). Verify truly unnamed access against current road/property/site evidence and use a truthful concise descriptor such as `Private drive` or `Main building access`; never invent a street name, infer one solely from a parcel address, or omit a needed label merely because the road is unnamed. Preserve excluded/access-only work rules. Descriptive labels remain bound to the actual access feature and obey regular type, spacing and arrow rules.

## Mixed-status paint

Inspect all visible status handoffs, shared/duplicate segments and junctions at 1x,2x and close-up. Enumerate the locations and actual native paint bindings. Distinguish a legitimate clean T-junction from a colored sliver along another status, parallel duplicate stroke, cap overshoot, bleed-through or mixed blob. Mathematical connectivity and copied `mixed_status_overlaps=0` are not evidence. Original source paint can itself contain a defect.28's thin green duplicate under its red Tremonte segment and31b's red driveway cap across green Orchid are regression examples. Any residual visible defect blocks release. Repair only with existing authority and bounded masks; keep every original style/topology/zero-outside cutoff. Use typed native removal only for an independently planned real redundant/obsolete path removal; do not relabel an existing-path repair to evade its comparator.

## Required report

Both PROJECT.json and each independent review.json contain `branch_color_review`:
- `artifact_sha256`, `delivery_filename`, `actual_size_screenshot`, `closeup_screenshots`;
- `branch_inventory_complete:true`, `status_junction_inventory_complete:true` only after full-network inspection;
- `branches`: nonempty list of objects with `id`, `source_binding`, `name_or_descriptor`, `label_ids`, `decision_evidence`, `visual_evidence`. Include every distinct run in the inventory. A genuinely unnecessary navigation label may use empty `label_ids` only with a specific `omission_evidence` explaining why the run is unambiguous; missing names and generic statements are not reasons;
- `status_junctions`: list with `id`, `source_binding`, `statuses`, `verdict` (`clean_handoff` or `separated`), `visual_evidence`; if none, give `no_status_junctions_evidence`;
- `unresolved_branch_labels:[]`, `mixed_status_defects:[]`.

Use actual capture paths, source/native feature IDs and bound label IDs. Inspect entire clusters, not just pairwise collisions; same-road alternatives remain required. The contract validator checks completeness of reporting and identity, not visual truth. Critics independently enumerate/inspect; never copy the builder's conclusions as their own. Required release score is exactly 10/10 in every category; all mandatory evidence/checks must pass. Saved artifact hashes invalidate earlier final claims until re-reviewed.

## Telephone designation — user clarification, 2026-09-07

Retain an existing authoritative Telephone/T designation even when assigned residences include apartments, houses, condominiums or other housing types. Housing type does not determine territory type: never convert T to A because apartments or condos occur in the territory. Resolve conflicting source identities from the actual user decision or authoritative assignment; do not infer a new type from housing or an unexplained archive suffix. Apply the established type to the filename. Filename normalization alone does not authorize changing the visible card identity.
