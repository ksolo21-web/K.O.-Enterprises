"""M4 V10 actual-byte verification of V9 photos and lossless video frames.

Offline private check ONLY. Does not authenticate external pins, source capture,
qualified reviewers, defect labels or customer release.
"""
from __future__ import annotations
from pathlib import Path
import tempfile

from PIL import Image, ImageChops
from .capture import MAX_PHOTO_BYTES, MAX_VIDEO_BYTES, decode_video_frame, probe_video
from .m4_frozen_safety_audit import digest, _hex, _ident, _keys
from .m4_media_grounding import MEDIA_FIELDS, MAX_MEDIA, KINDS
from .m4_source_paths import private_root, private_file, hash_file, validate_photo_pixels
from .serious_defect_benchmark import BenchmarkBlock

LOCATOR_FIELDS = {"case_id", "media_id", "relative_path"}


def _replay(parent_path, frame_path, frame_ms, root):
    if type(frame_ms) is not int or not 0 <= frame_ms <= 2 * 60 * 60 * 1000:
        raise BenchmarkBlock("Bad source frame time")
    with Image.open(frame_path) as original:
        if original.format != "PNG":
            raise BenchmarkBlock("Derived video frame must be lossless PNG for pixel replay")
        original.load()
        original_pixels = original.convert("RGB")
    with tempfile.TemporaryDirectory(prefix=".m4_v10_", dir=root) as folder:
        fresh = Path(folder) / "replay.png"
        try:
            actual = decode_video_frame(parent_path, fresh, frame_ms / 1000, timeout=90)
            with Image.open(fresh) as image:
                image.load()
                actual_pixels = image.convert("RGB")
        except Exception as exc:
            raise BenchmarkBlock("Original source video frame could not be decoded") from exc
        if abs(round(actual * 1000) - frame_ms) > 1:
            raise BenchmarkBlock("Frame source PTS does not match frozen timestamp")
        if (original_pixels.size != actual_pixels.size or
                ImageChops.difference(original_pixels, actual_pixels).getbbox() is not None):
            raise BenchmarkBlock("Derived frame pixels disagree with original source video")


def verify_private_source_bytes(media_manifest, source_locators, root, *,
                                independent_media_manifest_pin_sha256):
    """Locally rehash every V9 media row and source-video frame; fail closed.

    source_locators must remain outside Git, inaccessible to the model.
    Independent custodianship remains an EXTERNAL gate.
    """
    if digest(media_manifest) != _hex(independent_media_manifest_pin_sha256,
                                      "separately recorded V9 media pin"):
        raise BenchmarkBlock("V9 original media manifest changed after pin")
    if not isinstance(media_manifest, list) or not 1 <= len(media_manifest) <= MAX_MEDIA:
        raise BenchmarkBlock("Bounded V9 media manifest required")
    if not isinstance(source_locators, list) or len(source_locators) != len(media_manifest):
        raise BenchmarkBlock("Private source locators must cover every manifest row")
    rows = {}
    parent = {}
    for entry in media_manifest:
        _keys(entry, MEDIA_FIELDS, "V9 original media")
        key = (_ident(entry["case_id"], "source case"),
               _ident(entry["media_id"], "source ID"))
        if key in rows or entry["kind"] not in KINDS:
            raise BenchmarkBlock("Repeated source ID or invalid media kind")
        _hex(entry["sha256"], "actual source hash")
        rows[key] = entry
        if entry["kind"] == "video":
            parent[(key[0], entry["sha256"])] = key
    if media_manifest != sorted(media_manifest, key=lambda row:
                                (row["case_id"], row["media_id"])):
        raise BenchmarkBlock("V9 media manifest ordering invalid")
    root = private_root(root)
    paths = {}
    for item in source_locators:
        _keys(item, LOCATOR_FIELDS, "private source locator")
        key = (_ident(item["case_id"], "source locator case"),
               _ident(item["media_id"], "source locator ID"))
        if key not in rows or key in paths:
            raise BenchmarkBlock("Unknown or repeated source locator")
        path = private_file(root, item["relative_path"])
        if path in paths.values():
            raise BenchmarkBlock("One physical file cannot represent separate source media")
        paths[key] = path
    if set(paths) != set(rows):
        raise BenchmarkBlock("Missing source media locator")
    # Check all bytes before sending any untrusted file to a decoder.
    for key, row in rows.items():
        bound = MAX_VIDEO_BYTES if row["kind"] == "video" else MAX_PHOTO_BYTES
        if hash_file(paths[key], bound) != row["sha256"]:
            raise BenchmarkBlock("Source media bytes disagree with V9 SHA256")
    images = videos = frames = 0
    for key, row in rows.items():
        file = paths[key]
        if row["kind"] == "video":
            try:
                probe_video(file)
            except Exception as exc:
                raise BenchmarkBlock("Original video probe failed") from exc
            videos += 1
        else:
            details = validate_photo_pixels(file)
            images += 1
            if row["kind"] == "video_frame":
                source_key = parent.get((key[0], row["parent_video_sha256"]))
                if source_key is None:
                    raise BenchmarkBlock("Derived frame missing its own case's parent video")
                if details["image_format"] != "PNG":
                    raise BenchmarkBlock("Only lossless PNG video frames can be byte replayed")
                _replay(paths[source_key], file, row["frame_time_ms"], root)
                frames += 1
        bound = MAX_VIDEO_BYTES if row["kind"] == "video" else MAX_PHOTO_BYTES
        if hash_file(file, bound) != row["sha256"]:
            raise BenchmarkBlock("Source bytes changed during verification")
    return {
        "schema_version": 1,
        "status": "PRIVATE_ORIGINAL_BYTES_CHECKED_EXTERNAL_VALIDATION_PENDING",
        "media_manifest_sha256": digest(media_manifest),
        "verified_source_records": len(rows),
        "locally_rehashed_original_source_bytes": True,
        "decoded_photo_and_frame_count": images,
        "probed_video_count": videos,
        "lossless_video_frames_replayed": frames,
        "independent_custody_or_pin_authority_verified": False,
        "professionally_adjudicated_real_world_accuracy_verified": False,
        "qualified_inspector_authorized": False,
        "customer_release_allowed": False,
    }
