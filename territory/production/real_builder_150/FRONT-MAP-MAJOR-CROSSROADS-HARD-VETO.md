# Territory 1.5.0 Front-Map Major Crossroads Hard Veto

This overlay strengthens the active Territory standard for the 1.5.0 real-builder path without mutating the hash-pinned historical R52 vendor package.

## Mandatory rule

Every generated or rebuilt territory card MUST show at least **two distinct verified MAJOR cross roads on the FRONT-PAGE MAP AREA** for navigation.

This requirement is non-optional and cannot be skipped, grandfathered, averaged away, or deferred because of:
- territory type;
- prior approval or score;
- accepted supplied-map crop;
- limited space;
- existing directions text;
- a back page;
- metadata/audit evidence;
- a previous card that omitted the roads.

Both major roads must:
1. be current-source verified and physically distinct;
2. be physically drawn as visible road geometry on the front page;
3. have readable labels bound to that geometry;
4. have a verified drawn connected approach into the territory;
5. be named in visible directions.

Directions text alone, sidebar text, a legend, metadata/audit evidence, a back page, or a floating road name without its road geometry does NOT satisfy the rule.

## Presentation rule

Prefer to show both roads in the main front map.

Only when doing so would make the working territory unreadably small may the builder use a clearly integrated **front-page LOCATION inset**. That inset must itself:
- draw both major roads;
- readably label both;
- show the verified connected approach into the territory.

An inset on another page does not count.

## Release veto

If fewer than two qualifying major roads are present on the exact final front-page map, or either road is unreadable, unverified, floating, disconnected, or only mentioned in text:
- set `release_ready=false`;
- block export/approval;
- return the candidate to the builder for repair.

No critic score, category mean, prior pass, or user omission of an explicit reminder can waive this veto.

## Required structured fields

The 1.5 build plan and critic report must carry:

```json
{
  "major_crossroad_review": {
    "front_map_required": true,
    "minimum_distinct_major_roads": 2,
    "directions_only_satisfies": false,
    "back_page_satisfies": false,
    "skip_allowed": false,
    "roads": [
      {
        "canonical_road_id": "...",
        "name": "...",
        "identity_verified": true,
        "major_status_verified": true,
        "front_page_geometry_drawn": true,
        "front_page_label_readable": true,
        "connected_approach_drawn": true
      }
    ],
    "release_veto_passed": true
  }
}
```

At least two complete distinct road records are required.
