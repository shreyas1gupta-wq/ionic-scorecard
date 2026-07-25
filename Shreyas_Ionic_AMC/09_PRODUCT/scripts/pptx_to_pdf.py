# -*- coding: utf-8 -*-
"""pptx_to_pdf.py — scripted PPTX -> PDF via user-local LibreOffice (no admin install;
extracted 2026-07-26 with msiexec /a to %LOCALAPPDATA%\\Apps\\LibreOffice).

Usage:  python pptx_to_pdf.py <deck.pptx> [more.pptx ...] [--outdir DIR]
Each PDF lands next to its source (or in --outdir). Exit 1 if any conversion fails.
Part of the NDPMS deck pipeline (ndpms-deck skill): build -> gates -> PPTX -> PDF.
"""
import os
import sys
import glob
import subprocess

SOFFICE = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apps", "LibreOffice",
                       "program", "soffice.com")


def find_soffice():
    if os.path.exists(SOFFICE):
        return SOFFICE
    hits = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "Apps",
                                  "LibreOffice*", "**", "soffice.com"), recursive=True)
    return hits[0] if hits else None


def convert(paths, outdir=None):
    so = find_soffice()
    if not so:
        print("soffice.com not found under %LOCALAPPDATA%\\Apps\\LibreOffice - "
              "re-run the extract (see 99_OPS or the ndpms-deck skill).")
        return 1
    rc_all = 0
    for p in paths:
        p = os.path.abspath(p)
        od = os.path.abspath(outdir) if outdir else os.path.dirname(p)
        # LibreOffice writes <basename>.pdf into --outdir; --headless needs no display
        r = subprocess.run([so, "--headless", "--norestore", "--convert-to", "pdf",
                            "--outdir", od, p], capture_output=True, text=True, timeout=600)
        pdf = os.path.join(od, os.path.splitext(os.path.basename(p))[0] + ".pdf")
        if os.path.exists(pdf):
            print(f"OK   {pdf}  ({os.path.getsize(pdf)/1e6:.1f} MB)")
        else:
            print(f"FAIL {p}\n     {r.stdout.strip()[:300]}\n     {r.stderr.strip()[:300]}")
            rc_all = 1
    return rc_all


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    outdir = None
    if "--outdir" in sys.argv:
        outdir = sys.argv[sys.argv.index("--outdir") + 1]
        args = [a for a in args if a != outdir]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(convert(args, outdir))
