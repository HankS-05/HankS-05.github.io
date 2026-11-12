"""
Builds the art catalogue on Art.html.

How to use:
  1. Put your full-size art images in  art/originals/
  2. Run:  python3 make_catalogue.py
  3. Open art/catalogue.csv and fill in the title and date for each piece
     (new images are added automatically with a guessed title).
  4. Run  python3 make_catalogue.py  again to update Art.html.

The script makes small thumbnails (art/thumbs/) for the grid and
web-sized copies (art/large/) that open when someone clicks a piece.
Your originals are never changed. Needs Pillow:  pip3 install pillow
"""
import csv
import html
import re
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).parent
ORIGINALS = HERE / "art" / "originals"
THUMBS = HERE / "art" / "thumbs"
LARGE = HERE / "art" / "large"
CSV_FILE = HERE / "art" / "catalogue.csv"
PAGE = HERE / "Art.html"

THUMB_SIZE = 600    # longest side, pixels
LARGE_SIZE = 1800
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
START, END = "<!-- CATALOGUE START -->", "<!-- CATALOGUE END -->"


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "image"


def guess_title(stem):
    return re.sub(r"[_\-]+", " ", stem).strip().title()


def make_copy(src, dest, size):
    """Resize src to fit in size x size and save as JPEG, unless already up to date."""
    if dest.exists() and dest.stat().st_mtime >= src.stat().st_mtime:
        with Image.open(dest) as im:
            return im.size
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)        # fix sideways phone photos
        im = im.convert("RGB")
        im.thumbnail((size, size))
        im.save(dest, "JPEG", quality=85, optimize=True, progressive=True)
        print(f"  made {dest.relative_to(HERE)}")
        return im.size


def load_csv():
    if not CSV_FILE.exists():
        return {}
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return {row["file"]: row for row in csv.DictReader(f)}


def save_csv(rows):
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "title", "date"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    for d in (ORIGINALS, THUMBS, LARGE):
        d.mkdir(parents=True, exist_ok=True)

    originals = sorted(p for p in ORIGINALS.iterdir() if p.suffix.lower() in IMAGE_TYPES)
    known = load_csv()
    rows, new = [], 0
    for p in originals:
        row = known.get(p.name)
        if row is None:
            row = {"file": p.name, "title": guess_title(p.stem), "date": ""}
            new += 1
        rows.append(row)
    save_csv(rows)

    used, entries = set(), []
    for p, row in zip(originals, rows):
        name = slug(p.stem)
        while name in used:              # two files with similar names
            name += "-2"
        used.add(name)
        w, h = make_copy(p, THUMBS / f"{name}.jpg", THUMB_SIZE)
        make_copy(p, LARGE / f"{name}.jpg", LARGE_SIZE)
        entries.append((row["date"].strip(), row["title"].strip(), name, w, h))

    # Newest first; pieces without a date go last.
    entries.sort(key=lambda e: (e[0] != "", e[0]), reverse=True)

    figures = []
    for date, title, name, w, h in entries:
        t, d = html.escape(title), html.escape(date)
        figures.append(
            f'        <figure>\n'
            f'            <a href="art/large/{name}.jpg">'
            f'<img src="art/thumbs/{name}.jpg" alt="{t}" width="{w}" height="{h}" loading="lazy"></a>\n'
            f'            <figcaption><span class="art-title">{t}</span>'
            + (f' <span class="art-date">{d}</span>' if d else "")
            + '</figcaption>\n'
            f'        </figure>'
        )
    block = f'{START}\n    <div class="catalogue">\n' + "\n".join(figures) + f'\n    </div>\n    {END}'

    page = PAGE.read_text(encoding="utf-8")
    if START not in page or END not in page:
        raise SystemExit(f"Couldn't find the {START} / {END} markers in Art.html")
    before, rest = page.split(START, 1)
    after = rest.split(END, 1)[1]
    PAGE.write_text(before + block + after, encoding="utf-8")

    print(f"Done: {len(entries)} pieces on Art.html ({new} new).")
    if new:
        print("Fill in titles and dates in art/catalogue.csv, then run this again.")


if __name__ == "__main__":
    main()
