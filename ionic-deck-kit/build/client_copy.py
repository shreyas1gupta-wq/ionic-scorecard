# -*- coding: utf-8 -*-
"""Turn an analyst's note into something a client can be handed.

WHY THIS EXISTS. The rationale columns in the score files are written by and for the desk. They say
"the quant model", they cite the file a number came from, they carry the firm's epistemic tags
([DATA], [INFERENCE], [OPINION]), and they use the punctuation and the adjectives an internal note
uses. On the current stock file that is 373 of 750 rationales - half the direct-equity book.

The deck escaped this by accident: its pages read the analyst's written paragraphs and clip them.
The holdings WORKBOOK did not. It dumped the rationale column verbatim into a column headed "Why"
and shipped it to the client, so a client reading their own workbook found the firm discussing its
own model, naming its own CSV files, and marking its own confidence in brackets.

WHAT THIS IS NOT. It is not a rewriter and it does not soften a call. It changes vocabulary and
punctuation and removes what is internal. The claim, the number and the verdict come through
untouched, because the only thing worse than internal language on a client page is a client page
that says something different from the desk's own note.
"""
import re

# The firm's own published name for its direct-equity scoring. Everything internal maps to this.
SCORECARD = "the Ionic scorecard"

# ---- 1. things that are removed outright ---------------------------------------------------
_STRIP = [
    # the firm's epistemic tags. Real and useful internally; meaningless and alarming to a client.
    (re.compile(r"\[\s*(?:DATA|INFERENCE|OPINION|ESTIMATE|ASSUMPTION)[^\]]{0,60}\]\s*", re.I), ""),
    # a filename is never a client's business, and naming one invites a request for it
    (re.compile(r"\(?\b[\w\-]+\.(?:csv|xlsx|parquet|json|py)\b\)?,?\s*", re.I), ""),
    # data-source citations: the desk's sources are the desk's
    (re.compile(r"\(?\b(?:screener\.in|screener|INDmoney|Groww|Paytm Money|Advisorkhoj|Trendlyne|"
                r"moneycontrol|Tickertape|Value ?Research)\b\)?,?\s*", re.I), ""),
    # a bare ticket or run id
    (re.compile(r"\b(?:RUN|TICKET|JOB)[-_ ]?\d{2,}\b", re.I), ""),
]

# ---- 2. things that are renamed -------------------------------------------------------------
# ORDER MATTERS. The longest and most specific phrase has to go first, or a shorter rule eats the
# words the longer one was written to catch and leaves the tail of the phrase stranded.
_RENAME = [
    (r"this firm'?s own STOCK[_ ]SCORECARD engine", SCORECARD),
    (r"this firm'?s own (?:scoring )?engine", SCORECARD),
    (r"STOCK[_ ]SCORECARD(?:[_ ]\d+)?(?: engine)?", SCORECARD),
    (r"the quant (?:model|engine|scorecard)", SCORECARD),
    (r"quant(?:itative)? recommendation", "the scorecard's reading"),
    (r"the quant score(?:'s)?", "the score"),
    (r"quant score", "score"),
    (r"the quant (Sell|Hold|Trim|No View)", r"the scorecard's \1"),
    (r"quant (Sell|Hold|Trim|No View)", r"a scorecard \1"),
    (r"\bquant(?:'s)? (?:view|read|call)\b", "the scorecard's read"),
    (r"\bthe quant\b", "the scorecard"),
    # BARE "Quant" AS A SUBJECT is how the analyst desk actually writes: "Quant already rates this
    # Hold", "Quant lands on Hold", "Quant recommendation is Hold". Requiring an article in front
    # of it missed 373 of 750 rationales, which is to say it missed the pattern entirely.
    (r"(?<![\w-])quant(?=\s+(?:already|also|lands|reads|rates|scores|says|has|is|was|puts|"
     r"gives|carries|flags|recommendation|model|view|call|verdict))", "the scorecard"),
    # QUANT IS ALSO AN AMC. "Quant Small Cap Fund" is a real scheme, and a rule broad enough to
    # catch a bare subject would rename the fund itself to "the scorecard Small Cap Fund". So the
    # bare form is rewritten only where what follows is lower-case or punctuation, never where it
    # is a capitalised word that could be part of a name.
    # The lower-case test has to survive re.I, which makes [a-z] match capitals too and put the
    # rule straight back where it started. (?-i:...) turns case-sensitivity back on for the
    # look-ahead alone, so "Quant Small Cap Fund" is left as the scheme name it is.
    (r"(?<![\w-])quant(?=\s+(?-i:[a-z])|[,;:.])", "the scorecard"),
    # internal field names and run ids that reach analyst prose
    (r"\bfinal[_ ]scores?[_ ]?\d?y?\b", "the score"),
    (r"\bfinal[_ ]score[_ ]\dy\b", "the score"),
    (r"\brecommendation[_ ]overall\b", "the overall call"),
    (r"\bfinal[_ ]verdict\b", "the call"),
    (r"\bn\d+[_ ]union\d+[_ ][\w]+\b", ""),
    (r"\b(?:the )?V\d asymmetric[- ]override rule\b", "the desk's override rule"),
    (r"\bcoverage confidence\b", "coverage"),
    (r"\bQFRA[- ]?[12]?\b", "the firm's fund-quality framework"),
    (r"\bSENTINEL\b", "the watch-out flags"),
    (r"\bMERIT\b", "the grade"),
    (r"\bpf_qual[\w]*\b", "the analyst's note"),
    (r"\bfull[_ ]\d+[_ ]scored\b", SCORECARD),
    # field names that reach prose
    (r"\brecommendation_v\d\b", "the published call"),
    (r"\byour_recommendation\b", "the analyst's call"),
    (r"\bnegative_para\b", "the case against"),
    (r"\basset_class\b", "asset class"),
    (r"\bhit_rate\b", "months ahead of peers"),
    (r"\btrim_to_pct\b", "the trim target"),
    # the writing tells. "genuine" is ordinary English, so only the adverb and the intensifier go.
    # "genuinely clean" becomes "clearly clean", which is worse English than either. Where the
    # adverb only intensifies an adjective that already carries the claim, it goes.
    (r"\bgenuinely (clean|strong|weak|poor|good|real|profitable|cheap|expensive)\b", r"\1"),
    (r"\bgenuinely\b", "clearly"),
    (r"\ba genuinely\b", "a clearly"),
    # ASCII arrows. The deck's typeface has no glyph for a real arrow and the desk's style spells
    # it; left alone, "FY28->FY29" also clips mid-token when a cell is truncated.
    (r"\s*-+>\s*", " to "),
    (r"\s*<-+\s*", " from "),
    (r"\bgenuine (deterioration|decline|risk|concern)\b", r"clear \1"),
    (r"\brobustly\b", "reliably"),
    (r"\bholistic(?:ally)?\b", "whole-portfolio"),
    (r"\bdelve into\b", "look at"),
    (r"\bit is worth noting that\b", ""),
    (r"\bfurthermore,\s*", ""),
    (r"\bmoreover,\s*", ""),
    # abbreviations a client should not have to expand
    (r"\bYoY\b", "year on year"),
    (r"\bQoQ\b", "quarter on quarter"),
    (r"\bTTM\b", "trailing twelve months"),
]
# CASE-INSENSITIVE, and every replacement written in lower case. The desk writes "Quant" at
# the head of a sentence and "the quant model" inside one; a case-sensitive rule caught the
# second and not the first, and then the bare-subject rule fired on what was left and
# produced "The The scorecard model". The sentence is re-capitalised once, at the end.
_RENAME = [(re.compile(p, re.I), r) for p, r in _RENAME]

# ---- 3. punctuation ---------------------------------------------------------------------------
# The em-dash is the single most reliable tell, and the desk's own house style bans it. A dash
# between clauses becomes a comma; a dash used as a bracket pair becomes commas; a dash standing
# where a full stop belongs becomes a full stop. Bahnschrift, the deck's typeface, has no glyph for
# it either, so it renders as a box on a slide.
_DASH = re.compile(r"\s*(?:—|–|--)\s*")
_SPACE = re.compile(r"[ \t]+")
_ORPHAN = re.compile(r"\s+([,.;:])")


def clean(text, max_chars=None):
    """One rationale, made safe to hand over. Returns "" for anything empty."""
    s = " ".join(str(text or "").split())
    if not s:
        return ""
    for rx, rep in _STRIP:
        s = rx.sub(rep, s)
    for rx, rep in _RENAME:
        s = rx.sub(rep, s)
    s = _DASH.sub(", ", s)
    # a rename that swallows a trailing word can leave the next token welded on: "final scores
    # 70.5/51.5" becomes "the score70.5/51.5" unless the boundary is restored
    s = re.sub(r"([a-z])(\d)", r"\1 \2", s)
    s = _SPACE.sub(" ", s)
    s = _ORPHAN.sub(r"\1", s)
    s = re.sub(r",\s*,", ",", s)
    s = re.sub(r"^[,;:.\s]+", "", s)
    s = re.sub(r"\(\s*\)", "", s).strip()
    # A STRANDED PREPOSITION. Removing a filename or a citation leaves the word that governed it
    # sitting against the full stop: "revenue is declining per." reads as a truncation fault.
    s = re.sub(r"\s+\b(?:per|from|in|of|at|via|on|by|see)\s*([.;,])", r"\1", s, flags=re.I)
    s = re.sub(r"\s+\b(?:per|from|via|see)\s*$", "", s, flags=re.I)
    if not s:
        return ""
    s = s[0].upper() + s[1:]
    if max_chars and len(s) > max_chars:
        # cut at a sentence boundary rather than mid-clause; a rationale that stops at "and on"
        # reads as a rendering fault rather than as a reason
        cut = s[:max_chars]
        # A cut at a semicolon leaves ");." on the page. Prefer a full stop; a semicolon is a
        # clause boundary and not a sentence boundary, so what follows one is trimmed and its
        # punctuation goes with it.
        if ". " in cut:
            cut = cut[:cut.rfind(". ") + 1]
        elif "; " in cut:
            cut = cut[:cut.rfind("; ")].rstrip(" ,;:(") + "."
        else:
            cut = cut.rsplit(" ", 1)[0].rstrip(" ,;:(") + "..."
        s = re.sub(r"[\s(,;:]+\.$", ".", cut)
    if s and s[-1] not in ".?!":
        s += "."
    return s


def audit(series):
    """What a column would still carry after cleaning. For the sync check, not for the client."""
    LEFT = re.compile(r"\[(?:DATA|INFERENCE|OPINION)|\.csv\b|\bquant\b|QFRA|SENTINEL|"
                      r"—|–|\bgenuinely\b|screener", re.I)
    out = []
    for i, v in enumerate(series):
        c = clean(v)
        if c and LEFT.search(c):
            out.append((i, c[:160]))
    return out
