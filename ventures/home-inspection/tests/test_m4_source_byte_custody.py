"""V10 local original-bytes adversarial tests. Generated synthetic files only."""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from PIL import Image
from inspection_engine.capture import decode_video_frame
from inspection_engine.m4_frozen_safety_audit import digest
from inspection_engine.m4_source_byte_custody import verify_private_source_bytes
from inspection_engine.serious_defect_benchmark import BenchmarkBlock


def checksum(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


class OriginalMediaByteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="m4_v10_synthetic_")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "evidence").mkdir()
        self.photo = self.root / "evidence" / "photo.png"
        Image.new("RGB", (96, 96), (12, 33, 56)).save(self.photo)
        self.media = [self.row("photo-a", "photo", self.photo)]
        self.locators = [self.loc("photo-a", "evidence/photo.png")]

    def row(self, mid, kind, path, *, parent=None, time=None):
        return {"case_id": "case-001", "media_id": mid, "kind": kind,
                "sha256": checksum(path), "parent_video_sha256": parent,
                "frame_time_ms": time, "review_status": (
                    "source_only" if kind == "video" else "reviewed"),
                "area": "Synthetic roof"}

    def loc(self, mid, path):
        return {"case_id": "case-001", "media_id": mid, "relative_path": path}

    def score(self, *, pin=None, root=None):
        return verify_private_source_bytes(
            self.media, self.locators, root or self.root,
            independent_media_manifest_pin_sha256=pin or digest(self.media))

    def video_fixture(self):
        if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
            self.skipTest("FFmpeg required for video provenance regression")
        video = self.root / "evidence" / "sample.mp4"
        completed = subprocess.run(
            ["ffmpeg", "-nostdin", "-v", "error", "-f", "lavfi",
             "-i", "testsrc=size=96x96:rate=1:duration=3",
             "-c:v", "mpeg4", "-pix_fmt", "yuv420p", "-y", str(video)],
            capture_output=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
        still = self.root / "evidence" / "frame.png"
        self.assertAlmostEqual(decode_video_frame(video, still, 1.0), 1.0, places=3)
        self.media = [
            self.row("frame-001", "video_frame", still,
                     parent=checksum(video), time=1000),
            self.row("video-001", "video", video),
        ]
        self.locators = [
            self.loc("frame-001", "evidence/frame.png"),
            self.loc("video-001", "evidence/sample.mp4"),
        ]
        return video, still

    def test_local_photo_decodes_rehashes_and_never_releases(self):
        result = self.score()
        self.assertEqual(result["verified_source_records"], 1)
        self.assertEqual(result["decoded_photo_and_frame_count"], 1)
        self.assertTrue(result["locally_rehashed_original_source_bytes"])
        self.assertFalse(result["independent_custody_or_pin_authority_verified"])
        self.assertFalse(result["customer_release_allowed"])

    def test_substituted_image_bytes_rejected(self):
        Image.new("RGB", (96, 96), (87, 65, 43)).save(self.photo)
        with self.assertRaisesRegex(BenchmarkBlock, "disagree"):
            self.score()

    def test_corrupt_image_with_matching_frozen_hash_rejected(self):
        self.photo.write_bytes(b"not a decodable image")
        self.media[0]["sha256"] = checksum(self.photo)
        with self.assertRaises(BenchmarkBlock):
            self.score()

    def test_traversal_path_blocked(self):
        self.locators[0]["relative_path"] = "../outside.png"
        with self.assertRaisesRegex(BenchmarkBlock, "traversal"):
            self.score()

    def test_symlinked_photo_blocked(self):
        symlink = self.root / "evidence" / "link.png"
        symlink.symlink_to(self.photo)
        self.locators[0]["relative_path"] = "evidence/link.png"
        with self.assertRaisesRegex(BenchmarkBlock, "Symlinked"):
            self.score()

    def test_missing_private_locator_blocked(self):
        self.locators.clear()
        with self.assertRaisesRegex(BenchmarkBlock, "locators"):
            self.score()

    def test_changed_external_manifest_pin_blocked(self):
        with self.assertRaisesRegex(BenchmarkBlock, "after pin"):
            self.score(pin="a" * 64)

    def test_private_media_inside_git_blocked(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(BenchmarkBlock, "outside Git"):
            self.score()

    def test_wrong_media_kind_not_treated_as_photo(self):
        self.media[0]["kind"] = "unknown"
        with self.assertRaisesRegex(BenchmarkBlock, "invalid media"):
            self.score()

    def test_video_original_and_lossless_frame_replay(self):
        self.video_fixture()
        result = self.score()
        self.assertEqual(result["probed_video_count"], 1)
        self.assertEqual(result["lossless_video_frames_replayed"], 1)
        self.assertFalse(result["customer_release_allowed"])

    def test_video_frame_pixels_tampered_with_fresh_hash_still_fail(self):
        _, still = self.video_fixture()
        Image.new("RGB", (96, 96), "white").save(still)
        self.media[0]["sha256"] = checksum(still)
        with self.assertRaisesRegex(BenchmarkBlock, "pixels disagree"):
            self.score()

    def test_wrong_frozen_frame_timestamp_blocks(self):
        self.video_fixture()
        self.media[0]["frame_time_ms"] = 500
        with self.assertRaisesRegex(BenchmarkBlock, "PTS"):
            self.score()

    def test_video_frame_missing_parent_blocks(self):
        self.video_fixture()
        self.media[0]["parent_video_sha256"] = "b" * 64
        with self.assertRaisesRegex(BenchmarkBlock, "missing"):
            self.score()

    def test_video_frame_must_use_lossless_png(self):
        self.video_fixture()
        jpeg = self.root / "evidence" / "frame.jpg"
        with Image.open(self.root / "evidence" / "frame.png") as im:
            im.save(jpeg)
        self.media[0]["sha256"] = checksum(jpeg)
        self.locators[0]["relative_path"] = "evidence/frame.jpg"
        with self.assertRaisesRegex(BenchmarkBlock, "lossless PNG"):
            self.score()


if __name__ == "__main__":
    unittest.main()
