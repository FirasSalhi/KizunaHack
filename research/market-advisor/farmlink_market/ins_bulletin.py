"""Parse INS 'Bulletin Mensuel de la Statistique' PDFs.

Tables used:
  * 9.5 "Apports au marché de gros de Tunis" (tonnes per month) - source: Marché de Gros de Tunis.
  * 9.1 "Prix moyen de détail à Tunis" (millimes per unit) - source: INS.

Each table holds 13 monthly columns, most recent first. The months and years are read from the
table header, never from the bulletin's title (a bulletin titled "décembre 2025" can end in
September 2025). "…" = not available, "///" = no arrivals / not on sale (out of season).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

MONTHS = {"jan": 1, "janv": 1, "fév": 2, "fev": 2, "févr": 2, "mars": 3, "avril": 4, "avr": 4, "mai": 5,
          "juin": 6, "juill": 7, "juil": 7, "aout": 8, "août": 8, "aôut": 8, "sept": 9, "oct": 10,
          "nov": 11, "déc": 12, "dec": 12}
VALUE = r"(?:\d[\d ]*\d|\d|…|\.\.\.|///)"
MISSING, OUT_OF_SEASON = "not_available", "no_arrivals"


@dataclass
class Header:
    columns: list[tuple[int, int] | None]  # (year, month) per value column; None = annual average


def _month_token(tok: str) -> int | None:
    t = tok.lower().strip(".").replace("é", "é")
    return MONTHS.get(t)


def parse_header(text: str) -> Header:
    """Find the French month line and the year line that precedes it."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        toks = line.replace("Moy. Mens", "MOY").split()
        months = [_month_token(t) for t in toks]
        if len(toks) >= 12 and sum(m is not None for m in months) >= 12 and all(
            m is not None or t == "MOY" for t, m in zip(toks, months)
        ):
            years = None
            for back in range(1, 5):
                ys = re.findall(r"\b(20\d\d)\b", lines[i - back])
                if len(ys) >= 2:
                    years = [int(y) for y in ys]
                    break
            if not years:
                raise ValueError("year line not found above month header")
            year = max(years)
            cols: list[tuple[int, int] | None] = []
            prev = None
            for t, m in zip(toks, months):
                if t == "MOY":
                    cols.append(None)
                    continue
                if prev is not None and m > prev:
                    year -= 1
                cols.append((year, m))
                prev = m
            return Header(cols)
    raise ValueError("month header not found")


def _split_values(raw: str) -> list[str]:
    """Split a run of values. Thousands are never space-separated in these tables."""
    return raw.split()


def _to_number(tok: str) -> tuple[float | None, str]:
    if tok in ("…", "..."):
        return None, MISSING
    if tok == "///":
        return None, OUT_OF_SEASON
    return float(tok.replace(" ", "")), "ok"


ARRIVAL_SECTIONS = {"LEGUMES": "vegetable", "FRUITS": "fruit", "POISSONS": "fish"}


def parse_arrivals_pages(texts: list[str]) -> pd.DataFrame:
    rows = []
    section = None
    for text in texts:
        header = parse_header(text)
        n = len(header.columns)
        for line in text.splitlines():
            key = line.strip().upper()
            if key.split(" ")[0] in ARRIVAL_SECTIONS:
                section = ARRIVAL_SECTIONS[key.split(" ")[0]]
                continue
            m = re.match(rf"^\s*([A-Za-zÀ-ÿ'’\-\. ]+?)\s+((?:{VALUE}\s+){{{n - 1}}}{VALUE})(?:\s|$)", line)
            if not m or section is None:
                continue
            name = re.sub(r"\s+", " ", m.group(1)).strip()
            vals = m.group(2).split()
            if len(vals) != n:
                continue
            for col, tok in zip(header.columns, vals):
                if col is None:
                    continue
                v, status = _to_number(tok)
                rows.append({"item_raw": name, "section": section, "year": col[0], "month": col[1],
                             "value": v, "status": status})
    return pd.DataFrame(rows)


RETAIL_UNITS = r"(Kg|kg|3 p|P|L|1/2 kg|Paq\.|M3|M)"


def parse_retail_pages(texts: list[str]) -> pd.DataFrame:
    rows = []
    for text in texts:
        try:
            header = parse_header(text)
        except ValueError:
            continue
        n = len(header.columns)
        in_food = True
        for line in text.splitlines():
            m = re.match(rf"^\s*([A-Za-zÀ-ÿ'’\-\. ]+?)\s+{RETAIL_UNITS}\s+((?:{VALUE}\s+){{{n - 1}}}{VALUE})(?:\s|$)", line)
            if not m or not in_food:
                continue
            vals = m.group(3).split()
            if len(vals) != n:
                continue
            name = re.sub(r"\s+", " ", m.group(1)).strip()
            for col, tok in zip(header.columns, vals):
                if col is None:
                    continue
                v, status = _to_number(tok)
                rows.append({"item_raw": name, "unit": m.group(2), "year": col[0], "month": col[1],
                             "value": v, "status": status})
    return pd.DataFrame(rows)


def extract(pdf: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    reader = PdfReader(str(pdf))
    arrivals, retail = [], []
    for page in reader.pages:
        t = page.extract_text() or ""
        if "SOMMAIRE" in t or not re.search(r"Unit[ée]\s*:", t):
            continue  # table of contents / other pages
        if re.search(r"Apports au march[ée] de gros de tunis", t, re.I):
            arrivals.append(t)
        elif re.search(r"Prix moyen de d[ée]tail [àa] tunis", t, re.I):
            retail.append(t)
    a = parse_arrivals_pages(arrivals)
    r = parse_retail_pages(retail)
    for df in (a, r):
        df["bulletin"] = pdf.name
    return a, r
