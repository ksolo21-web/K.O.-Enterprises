"""Offline CE-1P reviewer desktop for a separately provisioned CE-1N room."""
import argparse
import hashlib
import json
import os
import stat
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .competitive_critic_audit import CriticReviewLedger
from .competitive_critic_observations import (
    DISPOSITIONS, MAX_SIGNED_OBSERVATIONS_BYTES, VISUAL_FINDINGS, _annotation,
    _date, _get_room_packet, build_pending_observation_worklist,
    inspect_signed_observation_receipt,
)
from .competitive_critic_review import _id, canonical
from .competitive_critic_room import MAX_SINGLE_IMAGE_BYTES, _check_metadata_file, _file_name
from .source_provenance import EvidenceError


def reviewer_access(room):
    """Require CE-1N's provisioner-owned room and designated reader group."""
    meta = room.lstat()
    groups = {*os.getgroups(), os.getegid()}
    if (os.geteuid() == 0 or meta.st_uid != 0 or meta.st_gid == 0
            or meta.st_gid not in groups or not stat.S_ISDIR(meta.st_mode)
            or stat.S_IMODE(meta.st_mode) != 0o550):
        raise EvidenceError("separate reviewer group and provisioned room required")
    def check(path):
        mode = 0o550 if path == room / "pages" else 0o440
        item = path.lstat()
        kind = stat.S_ISDIR if mode == 0o550 else stat.S_ISREG
        if (not kind(item.st_mode) or item.st_uid != 0 or item.st_gid != meta.st_gid
                or stat.S_IMODE(item.st_mode) != mode):
            raise EvidenceError("unexpected reviewer evidence permissions")

    check(room / "pages")
    check(room / "manifest.json")
    for path in (room / "pages").iterdir():
        check(path)


def private_record(directory, name, data):
    """Publish complete bytes once in a reviewer-owned private directory."""
    meta = directory.lstat()
    if (not stat.S_ISDIR(meta.st_mode) or meta.st_uid != os.geteuid()
            or stat.S_IMODE(meta.st_mode) != 0o700):
        raise EvidenceError("output directory must be reviewer-owned and mode 0700")
    with tempfile.NamedTemporaryFile(dir=directory) as staged:
        staged.write(data)
        staged.flush()
        os.fsync(staged.fileno())
        os.link(staged.name, directory / name)


def page_bytes(room, row):
    data = _check_metadata_file(room / "pages" / row["file"], maximum=MAX_SINGLE_IMAGE_BYTES)
    if hashlib.sha256(data).hexdigest() != row["png_sha256"]:
        raise EvidenceError("display page digest differs from worklist")
    return data


def desktop(args, packet, work):
    import tkinter as tk
    from tkinter import messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    dossier = packet["dossier"]
    reviewer = _id(args.reviewer, "reviewer ID")
    key = _id(args.key, "reviewer key ID")
    if reviewer == dossier["author_id"]:
        raise EvidenceError("author cannot submit reviewer findings")
    root = tk.Tk()
    root.title("Protected evidence review")
    root.geometry("1100x800")
    pages = work["page_tasks"]
    claims = work["claim_tasks"]
    sources = {s["id"]: s for s in dossier["sources"]}
    page_index = {p["file"]: i for i, p in enumerate(pages)}
    tasks = pages + claims
    nav = tk.Listbox(root, exportselection=False, width=30)
    nav.pack(side="left", fill="y")
    for row in tasks:
        nav.insert("end", row.get("file") or row["claim_id"])
    body = ttk.Frame(root, padding=8)
    body.pack(fill="both", expand=True)
    context = ScrolledText(body, wrap="word", height=12)
    context.pack(fill="both", expand=True)
    refs = ttk.Frame(body)
    refs.pack(fill="x")
    choice = ttk.Combobox(body, state="readonly")
    choice.pack(fill="x")
    ttk.Label(body, text="Finding and limitations").pack(anchor="w")
    notes = ScrolledText(body, height=5, wrap="word")
    notes.pack(fill="x")
    active = None
    opened_pages = set()

    def show_page(i):
        from io import BytesIO
        from PIL import Image, ImageTk
        data = page_bytes(args.room, pages[i])
        win = tk.Toplevel(root)
        win.title(pages[i]["file"])
        canvas = tk.Canvas(win, width=850, height=650)
        for direction in ("vertical", "horizontal"):
            vertical = direction == "vertical"
            bar = ttk.Scrollbar(win, orient=direction,
                                command=canvas.yview if vertical else canvas.xview)
            bar.pack(side="right" if vertical else "bottom", fill="y" if vertical else "x")
            canvas.configure(**{("yscrollcommand" if vertical else "xscrollcommand"): bar.set})
        canvas.pack(fill="both", expand=True)
        with Image.open(BytesIO(data), formats=["PNG"]) as img:
            canvas.image = ImageTk.PhotoImage(img)
        canvas.create_image(0, 0, image=canvas.image, anchor="nw")
        canvas.configure(scrollregion=canvas.bbox("all"))
        opened_pages.add(pages[i]["file"])

    def store():
        if active is None:
            return
        page = active < len(pages)
        row = tasks[active]
        field, note, stamp = (("visual_finding", "visual_notes", "observed_at") if page
                              else ("disposition", "reasoning", "assessed_at"))
        answer, detail = choice.get() or None, notes.get("1.0", "end-1c") or None
        if (answer, detail) != (row[field], row[note]):
            row.update({field: answer, note: detail, stamp: datetime.now(timezone.utc).isoformat()})

    def select(event=None):
        nonlocal active
        if not nav.curselection():
            return
        store()
        active = nav.curselection()[0]
        row = tasks[active]
        for widget in refs.winfo_children():
            widget.destroy()
        if active < len(pages):
            detail = row["file"] + "\nSHA-256 " + row["png_sha256"]
            links = [row["file"]]
            options, field, note = VISUAL_FINDINGS, "visual_finding", "visual_notes"
        else:
            claim = dossier["claims"][active - len(pages)]
            detail = json.dumps(claim, ensure_ascii=False, indent=2)
            for heading, ids in [("Supporting sources", claim["source_ids"]),
                                 ("Counterevidence", claim["counter_source_ids"])]:
                detail += "\n\n" + heading + "\n" + json.dumps(
                    [sources[s] for s in ids], ensure_ascii=False, indent=2)
            links = list(dict.fromkeys(_file_name(r["document_id"], r["page_number"])
                                       for r in row["issuer_citation_refs"]))
            options = DISPOSITIONS if links else DISPOSITIONS - {"packet_excerpt_located"}
            field, note = "disposition", "reasoning"
        for name in links:
            ttk.Button(refs, text="View " + name, command=lambda n=name: show_page(page_index[n])).pack(anchor="w")
        context.configure(state="normal")
        context.delete("1.0", "end")
        context.insert("end", detail)
        context.configure(state="disabled")
        choice.configure(values=sorted(options))
        choice.set(row[field] or "")
        notes.delete("1.0", "end")
        notes.insert("end", row[note] or "")

    ttk.Label(body, text="Overall reviewer summary").pack(anchor="w")
    summary = ScrolledText(body, height=4, wrap="word")
    summary.pack(fill="x")

    def export():
        store()
        now = datetime.now(timezone.utc)
        try:
            for i, row in enumerate(tasks):
                page = i < len(pages)
                if page and row["file"] not in opened_pages:
                    raise EvidenceError("Open page before exporting: " + row["file"])
                finding = row["visual_finding" if page else "disposition"]
                if finding not in (VISUAL_FINDINGS if page else DISPOSITIONS):
                    raise EvidenceError("Missing finding for " + (row.get("file") or row["claim_id"]))
                _annotation(row["visual_notes" if page else "reasoning"], row.get("file") or row["claim_id"],
                            minimum=36 if page else 48, maximum=1200 if page else 1500)
                _date(row["observed_at" if page else "assessed_at"], now)
            overall = _annotation(summary.get("1.0", "end-1c"), "summary", minimum=60, maximum=2000)
            rid = "obs-" + uuid.uuid4().hex
            receipt = {k: packet[k] for k in ("handoff_sha256", "dossier_sha256", "issuer_inventory_head_sha256")}
            receipt.update({k: dossier[k] for k in ("author_id", "venture_id", "dossier_id")})
            receipt.update(schema_version="1.0", receipt_id=rid, reviewer_id=reviewer,
                           reviewer_key_id=key, room_manifest_sha256=args.digest,
                           completed_at=now.isoformat(), expires_at=(now + timedelta(minutes=30)).isoformat(),
                           page_observations=pages, claim_assessments=claims, reviewer_summary=overall)
            name = rid + ".unsigned.json"
            private_record(args.output, name, canonical(receipt, MAX_SIGNED_OBSERVATIONS_BYTES))
            messagebox.showinfo("Unsigned receipt saved", name)
        except (ValueError, OSError, EvidenceError) as exc:
            messagebox.showerror("Cannot export review", str(exc))

    ttk.Button(body, text="Save unsigned receipt for signing", command=export).pack(anchor="e")
    nav.bind("<<ListboxSelect>>", select)
    nav.selection_set(0)
    select()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("room", type=Path)
    parser.add_argument("digest", help="manifest SHA-256 received separately")
    parser.add_argument("output", type=Path, help="existing private output directory")
    actions = parser.add_subparsers(dest="action", required=True)
    review = actions.add_parser("review")
    review.add_argument("reviewer")
    review.add_argument("key", help="public key identifier")
    archive = actions.add_parser("archive")
    for field in ("ledger_root", "policy", "envelope"):
        archive.add_argument(field, type=Path)
    args = parser.parse_args()
    reviewer_access(args.room)
    if args.action == "review":
        work = build_pending_observation_worklist(args.room, expected_manifest_sha256=args.digest)
        desktop(args, _get_room_packet(args.room, args.digest), work)
    else:
        envelope = json.loads(args.envelope.read_bytes())
        with CriticReviewLedger(args.ledger_root) as ledger:
            result = inspect_signed_observation_receipt(
                args.room, args.digest, json.loads(args.policy.read_bytes()), envelope,
                critic_audit_ledger=ledger)
        name = envelope["receipt"]["receipt_id"] + ".signed.json"
        private_record(args.output, name, canonical(envelope, MAX_SIGNED_OBSERVATIONS_BYTES + 1024))
        print(result["state"])


if __name__ == "__main__":
    main()
