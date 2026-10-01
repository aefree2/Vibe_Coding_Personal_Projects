#!/usr/bin/env python3
"""
NDJSON reviewer: show each object's `body`, accept/reject with arrow keys,
write accepted/rejected lines to separate ndjson files, and checkpoint for resume.

Keys:
  RIGHT arrow  -> accept
  LEFT arrow   -> reject
  q            -> quit (saves checkpoint)
  a / d        -> accept / reject (fallback keys)
  j / k        -> scroll down/up
  SPACE        -> page down
  b            -> page up
"""

from __future__ import annotations

import argparse
import curses
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re


@dataclass
class Checkpoint:
    byte_offset: int = 0
    line_number: int = 0  # 1-based count of lines already processed

    @staticmethod
    def load(path: Path) -> "Checkpoint":
        if not path.exists():
            return Checkpoint()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Checkpoint(
                byte_offset=int(data.get("byte_offset", 0)),
                line_number=int(data.get("line_number", 0)),
            )
        except Exception:
            # Corrupt checkpoint? Start from scratch (but don't delete it).
            return Checkpoint()

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(
                {"byte_offset": self.byte_offset, "line_number": self.line_number},
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        tmp.replace(path)


def wrap_text(text: str, width: int) -> list[str]:
    """Simple word wrap preserving existing newlines."""
    if width <= 1:
        return [text]
    lines: list[str] = []
    for para in text.splitlines() or [""]:
        if not para:
            lines.append("")
            continue
        words = para.split(" ")
        cur = ""
        for w in words:
            if not cur:
                cur = w
            elif len(cur) + 1 + len(w) <= width:
                cur += " " + w
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def safe_json_loads(line: str) -> Optional[dict]:
    try:
        return json.loads(line)
    except Exception:
        return None


def draw_screen(
    stdscr: "curses._CursesWindow",
    title: str,
    header: str,
    body_lines: list[str],
    scroll: int,
    footer: str,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    # Title line
    stdscr.addnstr(0, 0, title, w - 1, curses.A_BOLD)

    # Header line
    if h >= 2:
        stdscr.addnstr(1, 0, header, w - 1)

    # Body area
    top = 2
    bottom = h - 2  # leave room for footer
    body_height = max(0, bottom - top + 1)
    visible = body_lines[scroll : scroll + body_height]

    for i, line in enumerate(visible):
        y = top + i
        if y >= h - 1:
            break
        stdscr.addnstr(y, 0, line, w - 1)

    # Footer
    if h >= 2:
        stdscr.addnstr(h - 1, 0, footer, w - 1, curses.A_REVERSE)

    stdscr.refresh()


def review_file(
    stdscr: "curses._CursesWindow",
    input_path: Path,
    accepts_path: Path,
    rejects_path: Path,
    checkpoint_path: Path,
    encoding: str,
    field: str
) -> None:
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.keypad(True)

    cp = Checkpoint.load(checkpoint_path)
    with open(input_path, 'r') as fp:
        total_line_num = sum(1 for line in fp)
        #print('Total Number of lines:', lines)

    # Open input in binary so byte offsets are reliable
    with input_path.open("rb") as fin, \
         accepts_path.open("ab") as facc, \
         rejects_path.open("ab") as frej:

        # Resume
        fin.seek(cp.byte_offset, os.SEEK_SET)

        while True:
            start_offset = fin.tell()
            raw = fin.readline()
            if not raw:
                # EOF
                h, w = stdscr.getmaxyx()
                stdscr.erase()
                stdscr.addnstr(0, 0, "Reached EOF. All done.", w - 1, curses.A_BOLD)
                stdscr.addnstr(2, 0, f"Accepted file: {accepts_path}", w - 1)
                stdscr.addnstr(3, 0, f"Rejected file: {rejects_path}", w - 1)
                stdscr.addnstr(5, 0, "Press any key to exit.", w - 1)
                stdscr.refresh()
                stdscr.getch()
                # Save final checkpoint as EOF position
                cp.byte_offset = fin.tell()
                checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                cp.save(checkpoint_path)
                return

            # Decode line for JSON parsing + display
            try:
                line = raw.decode(encoding, errors="replace")
            except Exception:
                line = raw.decode("utf-8", errors="replace")

            obj = safe_json_loads(line)
            body = ""
            meta = ""
            if obj is None:
                body = "(Invalid JSON line — will be treated as reject if you reject it.)\n\n" + line
                meta = "invalid-json"
            else:
                
                body = "\n" + str(obj.get(field, "")) #HERE IS THE LINE TO CHANGE
                if field == "selftext":
                    body = "\n TITLE: " + str(obj.get("title", "")) + "\n" + body
                meta_parts = []
                for k in ("subreddit", "author", "id", "link_id", "created_utc", "score"):
                    if k in obj and obj.get(k) is not None:
                        meta_parts.append(f"{k}={obj.get(k)}")
                meta = "  ".join(meta_parts) if meta_parts else "no-metadata"

            scroll = 0

            while True:
                h, w = stdscr.getmaxyx()
                usable_width = max(10, w - 1)
                body_lines = wrap_text(body, usable_width)

                title = f"NDJSON Review — {input_path.name}"
                header = f"Line: {cp.line_number + 1}/{total_line_num}   Offset: {start_offset}   {meta}" # also changed this line
                footer = "← reject   → accept   (a/d) accept/reject   j/k scroll   space/b page   q quit"

                # Clamp scroll
                body_area_h = max(0, h - 3)  # title+header+footer
                max_scroll = max(0, len(body_lines) - body_area_h)
                scroll = max(0, min(scroll, max_scroll))

                draw_screen(stdscr, title, header, body_lines, scroll, footer)
                ch = stdscr.getch()

                if ch in (ord("q"), ord("Q")):
                    # Save checkpoint and exit without consuming current line
                    cp.byte_offset = start_offset
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    cp.save(checkpoint_path)
                    return

                # Scroll controls
                if ch in (ord("j"), curses.KEY_DOWN):
                    scroll = min(scroll + 1, max_scroll)
                    continue
                if ch in (ord("k"), curses.KEY_UP):
                    scroll = max(scroll - 1, 0)
                    continue
                if ch == ord(" "):  # page down
                    scroll = min(scroll + max(1, body_area_h), max_scroll)
                    continue
                if ch in (ord("b"), ord("B")):  # page up
                    scroll = max(scroll - max(1, body_area_h), 0)
                    continue

                # Decision keys
                if ch in (curses.KEY_RIGHT, ord("a"), ord("A")):
                    # accept: write raw line
                    facc.write(raw)
                    facc.flush()
                    os.fsync(facc.fileno())
                    cp.line_number += 1
                    cp.byte_offset = fin.tell()
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    cp.save(checkpoint_path)
                    break

                if ch in (curses.KEY_LEFT, ord("d"), ord("D")):
                    # reject: write raw line
                    frej.write(raw)
                    frej.flush()
                    os.fsync(frej.fileno())
                    cp.line_number += 1
                    cp.byte_offset = fin.tell()
                    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
                    cp.save(checkpoint_path)
                    break

                # Otherwise ignore key and keep showing


def main() -> int:
    p = argparse.ArgumentParser(description="Interactively accept/reject NDJSON lines by viewing `body`.")
    
    p.add_argument("--file_name", type=Path,)
    p.add_argument("--input", type=Path,default=Path("reddit_sorting"), help="Path to input NDJSON file (one JSON object per line)")
    p.add_argument("--accepts", type=Path, default=Path("accepts.ndjson"), help="Output accepts file (appended)")
    p.add_argument("--rejects", type=Path, default=Path("rejects.ndjson"), help="Output rejects file (appended)")
    p.add_argument("--checkpoint", type=Path, default=Path(".checkpoint.ndjson_review.json"), help="Checkpoint file")
    p.add_argument("--encoding", type=str, default="utf-8", help="Input encoding (default: utf-8)")
    args = p.parse_args()

    file_name = re.split("_", args.file_name.__str__())
    print(file_name)
    field = "body"
    if "submissions" in file_name[1]:
        field = "selftext"
    clean_file = re.sub(".txt", "", str(args.file_name))
    print(clean_file)
    input_path = Path(f"{args.input}/{args.file_name}")
    accepts = Path(f"{args.input}/{clean_file}_accepts.ndjson")
    rejects = Path(f"{args.input}/{clean_file}_rejects.ndjson")
    checkpoint_dir = Path(f"{clean_file}_{args.checkpoint}")


    if not args.input.exists():
        print(f"Input file not found: {args.input}", file=sys.stderr)
        return 2

    # Ensure output dirs exist
    accepts.parent.mkdir(parents=True, exist_ok=True)
    rejects.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.parent.mkdir(parents=True, exist_ok=True)

    curses.wrapper(
        review_file,
        input_path=input_path,
        accepts_path=accepts,
        rejects_path=rejects,
        checkpoint_path=checkpoint_dir,
        encoding=args.encoding,
        field=field
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
