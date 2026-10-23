"""Parse the GDPR text (domains/gdpr/policy.md) into its legal structure.

Deterministic, no model involved. Produces structure.json with:
- chapters, sections, articles (title, chapter, section),
- paragraphs and points with their text (IDs like "17(3)(b)"),
- Article 4 definitions (26 defined terms),
- every cross-reference the text makes ("Article 6(1)", "point (a) of
  Article 9(2)", "Articles 15 to 22", "paragraph 3" inside the same article).

Usage: python3 build_structure.py [policy.md] [structure.json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE.parent / "policy.md"
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "structure.json"

ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11}
ROW = re.compile(r"^\|\s*\\\(([0-9a-z]+)\\\)\s*\|\s*(.*?)\s*\|\s*$")
BOLDROW = re.compile(r"^\*\*\(([0-9a-z]+)\)\*\*\s*(.*)$")  # e.g. **(16)** ‘main establishment’ means: ...
PARA = re.compile(r"^(\d+)\.\s+(.*)$")


def clean(text: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)  # markdown links
    text = text.replace("\\(", "(").replace("\\)", ")").replace("\\", "")
    return re.sub(r"\s+", " ", text).strip()


def parse(lines: list[str]) -> dict:
    start = next(i for i, l in enumerate(lines) if l.strip() == "CHAPTER I")
    chapters, sections, articles = [], [], []
    chapter = section = article = para = None
    pending = None  # which heading expects its title on the next non-empty line
    for raw in lines[start:]:
        line = raw.rstrip("\n")
        s = line.strip()
        if not s or set(s) <= set("|-: "):
            continue
        if pending:
            pending["title"] = clean(s)
            pending = None
            continue
        if re.fullmatch(r"CHAPTER [IVX]+", s):
            chapter = {"id": f"CH.{s.split()[1]}", "num": ROMAN[s.split()[1]], "title": ""}
            chapters.append(chapter)
            section = None
            pending = chapter
            continue
        if re.fullmatch(r"Section \d+", s):
            section = {"id": f"{chapter['id']}.S{s.split()[1]}", "num": int(s.split()[1]), "chapter": chapter["id"], "title": ""}
            sections.append(section)
            pending = section
            continue
        if re.fullmatch(r"Article \d+", s):
            article = {"id": f"ART.{s.split()[1]}", "num": int(s.split()[1]), "title": "",
                       "chapter": chapter["id"], "section": section["id"] if section else None,
                       "intro": [], "paragraphs": []}
            articles.append(article)
            para = None
            pending = article
            continue
        if article is None:
            continue
        m = PARA.match(s)
        if m and not s.startswith("|"):
            para = {"id": f"{article['num']}({m.group(1)})", "num": int(m.group(1)), "text": clean(m.group(2)), "points": [], "more": []}
            article["paragraphs"].append(para)
            continue
        r = ROW.match(s) or BOLDROW.match(s)
        if r:
            label, text = r.group(1), clean(r.group(2))
            owner_id = para["id"] if para else str(article["num"])
            point = {"id": f"{owner_id}({label})", "label": label, "text": text}
            (para["points"] if para else article.setdefault("points", [])).append(point)
            continue
        if para is not None:
            para["more"].append(clean(s))
        else:
            article["intro"].append(clean(s))
    return {"chapters": chapters, "sections": sections, "articles": articles}


def definitions(structure: dict) -> list[dict]:
    art4 = next(a for a in structure["articles"] if a["num"] == 4)
    out = []
    for p in art4.get("points", []):
        m = re.match(r"^[‘'](.+?)[’'](?: of the data subject)? means:? ?(.*)$", p["text"])
        if not m:
            continue
        term = m.group(1)
        out.append({"id": "DT." + re.sub(r"[^a-z0-9]+", "_", term.lower()).strip("_"),
                    "term": term, "article": f"4({p['label']})", "definition": p["text"]})
    return out


REF_PATTERNS = [
    # point (a) of Article 9(2) / points (a) and (b) of Article 6(1)
    (re.compile(r"points? \(([a-z])\)(?:(?:, | and | or )\(([a-z])\))*(?: to \(([a-z])\))? of Article (\d+)\((\d+)\)"), "point"),
    # Article 6(1)(a) / Article 17(3) / Article 9
    (re.compile(r"Article (\d+)(?:\((\d+)\))?(?:\(([a-z])\))?"), "article"),
    # Articles 15 to 22
    (re.compile(r"Articles (\d+) to (\d+)"), "range"),
    # Articles 15, 16 and 17 / Articles 13 and 14
    (re.compile(r"Articles ((?:\d+(?:\(\d+\))?(?:, | and | or ))+\d+(?:\(\d+\))?)"), "list"),
]


def refs_in(text: str, here: int) -> set[tuple[int, str]]:
    """Return {(target_article, precise_ref)} for references in *text*."""
    found: set[tuple[int, str]] = set()
    for pat, kind in REF_PATTERNS:
        for m in pat.finditer(text):
            if kind == "point":
                found.add((int(m.group(4)), f"{m.group(4)}({m.group(5)})({m.group(1)})"))
            elif kind == "article":
                num, par, pt = m.group(1), m.group(2), m.group(3)
                found.add((int(num), num + (f"({par})" if par else "") + (f"({pt})" if pt else "")))
            elif kind == "range":
                a, b = int(m.group(1)), int(m.group(2))
                for n in range(a, b + 1):
                    found.add((n, str(n)))
            elif kind == "list":
                for part in re.findall(r"\d+(?:\(\d+\))?", m.group(1)):
                    found.add((int(part.split("(")[0]), part))
    # paragraph N of this article (not followed by "of Article")
    for m in re.finditer(r"paragraphs? (\d+)(?:(?:, | and | or | to )(\d+))?(?! of Article)", text):
        for g in (m.group(1), m.group(2)):
            if g:
                found.add((here, f"{here}({g})"))
    return found


def cross_references(structure: dict) -> list[dict]:
    edges: dict[tuple[str, str], dict] = {}
    for art in structure["articles"]:
        units = [(str(art["num"]), " ".join(art["intro"]))]
        for p in art["paragraphs"]:
            units.append((p["id"], p["text"] + " " + " ".join(p["more"])))
            units += [(pt["id"], pt["text"]) for pt in p["points"]]
        units += [(pt["id"], pt["text"]) for pt in art.get("points", [])]
        for src_id, text in units:
            for target, precise in refs_in(text, art["num"]):
                if not 1 <= target <= 99:
                    continue
                key = (f"ART.{art['num']}", f"ART.{target}")
                e = edges.setdefault(key, {"source": key[0], "target": key[1], "occurrences": []})
                e["occurrences"].append({"from": src_id, "to": precise})
    out = []
    for (s, t), e in edges.items():
        e["internal"] = s == t
        out.append(e)
    return out


def main() -> None:
    structure = parse(SRC.read_text().splitlines())
    structure["definitions"] = definitions(structure)
    structure["references"] = cross_references(structure)
    OUT.write_text(json.dumps(structure, indent=1, ensure_ascii=False))
    arts = structure["articles"]
    n_par = sum(len(a["paragraphs"]) for a in arts)
    n_pts = sum(len(p["points"]) for a in arts for p in a["paragraphs"]) + sum(len(a.get("points", [])) for a in arts)
    ext = [e for e in structure["references"] if not e["internal"]]
    print(f"chapters={len(structure['chapters'])} sections={len(structure['sections'])} articles={len(arts)} "
          f"paragraphs={n_par} points={n_pts} definitions={len(structure['definitions'])} "
          f"article-to-article references={len(ext)} (internal paragraph refs={len(structure['references']) - len(ext)})")


if __name__ == "__main__":
    main()
