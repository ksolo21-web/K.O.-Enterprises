"""Exercise the CE-1P Tk desktop on an isolated graphical display."""
from pathlib import Path
from types import SimpleNamespace
import json, tempfile, tkinter as tk
from tkinter import ttk
from unittest.mock import patch
from company_os.competitive_visual_review import desktop
from test_competitive_critic_observations import SignedObservationTests
from datetime import datetime

fx = SignedObservationTests()
fx.setUp()
try:
    with tempfile.TemporaryDirectory() as tmp:
        args = SimpleNamespace(room=fx.path, output=Path(tmp), digest=fx.digest,
                               reviewer="critic-001", key="critic-key-001")
        def interact(root):
            root.update()
            nav, body = root.winfo_children()
            context_frame, links, choice, _, notes_frame, _, summary_frame, save = body.winfo_children()
            def editor(frame):
                return next(w for w in frame.winfo_children() if isinstance(w, tk.Text))
            for i in range(nav.size()):
                nav.selection_clear(0, "end")
                nav.selection_set(i)
                nav.event_generate("<<ListboxSelect>>")
                root.update()
                if i < len(fx.pending["page_tasks"]):
                    links.winfo_children()[0].invoke()
                    root.update()
                    win = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
                    canvas = next(w for w in win.winfo_children() if isinstance(w, tk.Canvas))
                    assert canvas.image.width() > 0 and canvas.image.height() > 0
                    win.destroy()
                if i >= len(fx.pending["page_tasks"]):
                    assert "Counterevidence" in editor(context_frame).get("1.0", "end")
                choice.set("unassessable" if i < len(fx.pending["page_tasks"]) else "unverified")
                editor(notes_frame).insert("end", "Synthetic workflow exercise with a detailed observation for this item only.")
            editor(summary_frame).insert("end", "Synthetic desktop test with no genuine independent visual or factual judgment.")
            save.invoke()
            root.destroy()
        class FixtureClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return fx.now

        with (patch.object(tk.Tk, "mainloop", interact),
              patch("company_os.competitive_visual_review.datetime", FixtureClock),
              patch("tkinter.messagebox.showinfo"),
              patch("tkinter.messagebox.showerror", side_effect=AssertionError)):
            desktop(args, fx.packet, fx.pending)
        receipt = json.loads(next(Path(tmp).glob("*.unsigned.json")).read_bytes())
        assert set(receipt) == set(fx.receipt)
        fx.receipt = receipt
        assert fx.inspect()["state"].startswith("HOLD")
        print("Desktop displayed the sealed image, collected all findings, and exported a CE-1O-compatible receipt.")
finally:
    fx.doCleanups()
