"""Phase-3: Management-Commentary (concall) scoring rubric + prototype text extractor.

This is the "Concall/Management" module agent referenced in 10_AGENT_ARCHITECTURE.md.
It does NOT itself score transcripts with an LLM (no fabrication, per hard rule Q17/D-035) —
it defines the STRUCTURED rubric as data, and a heuristic extractor that pulls candidate
sentences per dimension so a human or the later LLM-agent layer can score fast and
consistently. The LLM-scoring hook is a clearly-marked stub (`llm_score_dimension`).

Rubric dimensions (8, 0-5 each): see `DIMENSIONS` below. Composite -> `management_commentary_score()`.
Theme feed + horizon emphasis: see `THEME_FEED` / `HORIZON_EMPHASIS` and 05/06/10/01 docs.

Data: transcript TEXT is embedded (per-page .txt inside
datasets/india_earnings_calls/extracted_texts.zip), keyed by "<TICKER>_<Mon-YYYY>_transcript/page_N.txt".
The CSV's `transcript_link` column is link-only (BSE PDF URL) but the zip already has the
extracted text, so no web fetch is needed for the pilot demo. See `TranscriptStore` below.
"""
from __future__ import annotations
import os, re, json, zipfile
from dataclasses import dataclass, field
from typing import Optional

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PROJECT = os.path.join(BASE, "ALPHA_RANKER")
EARNINGS_CALLS_DIR = os.path.join(BASE, "datasets", "india_earnings_calls")
TRANSCRIPTS_ZIP = os.path.join(EARNINGS_CALLS_DIR, "extracted_texts.zip")

# ============================================================================
# 1. THE RUBRIC (structured data — 7 scored dimensions + 1 red-flag dimension)
# ============================================================================

@dataclass
class Dimension:
    key: str
    name: str
    is_redflag: bool           # True = penalty dimension (5=clean, 0=severe), feeds Forensic
    anchor_0: str               # what earns a 0
    anchor_5: str               # what earns a 5
    theme_feed: list            # which of the 7 official scoring-engine themes this feeds
    keywords: list = field(default_factory=list)   # regex fragments (case-insensitive) for heuristic pull
    needs_prior_quarter: bool = False               # dimension requires last quarter's transcript/guidance as context


DIMENSIONS: list[Dimension] = [
    Dimension(
        key="guidance_credibility",
        name="Guidance credibility & specificity",
        is_redflag=False,
        anchor_0=("No numeric guidance given; guidance is vague boilerplate ('we remain confident of growth') "
                   "with no basis; or guidance methodology changed without explanation."),
        anchor_5=("Specific, quantified, multi-metric guidance (revenue range, margin range, capex plan) with "
                   "clear assumptions/bridge, consistent methodology quarter-to-quarter, and directly addressed "
                   "when analysts push back."),
        theme_feed=["Growth", "Catalyst"],
        keywords=[r"\bguidance\b", r"\bwe expect\b", r"\bwe (?:are|remain) confident\b", r"\boutlook\b",
                  r"\bfor (?:the|this) (?:full[- ]year|fiscal|quarter)\b", r"\bwe (?:guide|guided)\b",
                  r"\bin the range of\b", r"\btarget(?:ing)?\b.*\b(?:margin|revenue|growth)\b"],
    ),
    Dimension(
        key="tone_shift",
        name="Tone shift vs prior quarter",
        is_redflag=False,
        anchor_0=("Marked deterioration: increased hedging language ('largely', 'broadly', 'should', 'hopefully'), "
                   "shorter/deflecting answers, avoiding numbers previously given freely, new defensiveness on "
                   "questions previously answered plainly."),
        anchor_5=("Stable-or-improving tone: same or greater specificity/confidence as prior quarter(s), "
                   "management proactively raises the hard question before analysts do, no new hedging language."),
        theme_feed=["Growth"],
        keywords=[r"\bhopefully\b", r"\bshould be\b", r"\bbroadly\b", r"\blargely\b", r"\bwe (?:believe|feel)\b",
                  r"\bcautiously optimistic\b", r"\bwait and watch\b", r"\bchallenging (?:quarter|environment)\b"],
        needs_prior_quarter=True,
    ),
    Dimension(
        key="capex_growth_runway",
        name="Capex/expansion & growth-runway language",
        is_redflag=False,
        anchor_0=("No capex/expansion commentary; or expansion plans repeatedly delayed/downsized without new "
                   "explanation; generic 'we continue to invest' with no numbers."),
        anchor_5=("Concrete capacity/capex plan with amount, timeline, and expected utilization/payback, explicitly "
                   "linked to a demand driver (why this capacity, for which growth)."),
        theme_feed=["Growth"],
        keywords=[r"\bcapex\b", r"\bcapital expenditure\b", r"\bcapacity expansion\b", r"\bnew (?:plant|facility|"
                  r"unit|line)\b", r"\bgreenfield\b", r"\bbrownfield\b", r"\binvestment plan\b", r"\bcommission(?:ed|ing)\b",
                  r"\bcapacity utili[sz]ation\b"],
    ),
    Dimension(
        key="promise_vs_delivery",
        name="Promise-vs-delivery tracking",
        is_redflag=False,
        anchor_0=("Prior quarter's specific guidance missed by a wide margin with no acknowledgment; or guidance "
                   "quietly dropped/redefined without reconciliation."),
        anchor_5=("Prior guidance met or exceeded, explicitly reconciled on this call ('as we said last quarter... "
                   "we delivered...')."),
        theme_feed=["Growth", "Quality"],
        keywords=[r"\bas (?:we |I )?(?:said|guided|mentioned) (?:last|previous)\b", r"\bin line with (?:our )?guidance\b",
                  r"\bwe (?:had )?(?:committed|promised)\b", r"\bahead of (?:our )?guidance\b", r"\bmiss(?:ed)? (?:our )?guidance\b",
                  r"\bshort(?:fall)? of (?:our )?(?:guidance|target)\b"],
        needs_prior_quarter=True,
    ),
    Dimension(
        key="demand_orderbook",
        name="Demand/order-book commentary",
        is_redflag=False,
        anchor_0=("No order-book/demand color; or explicit demand softness/order cancellations/pushed-out deals "
                   "acknowledged with no credible offsetting driver."),
        anchor_5=("Order book/pipeline growth vs prior quarter, book-to-bill or backlog-coverage metrics, "
                   "broad-based (not one large one-off order) demand commentary."),
        theme_feed=["Growth", "Catalyst"],
        keywords=[r"\border book\b", r"\border[- ]?intake\b", r"\bbacklog\b", r"\bpipeline\b", r"\bTCV\b",
                  r"\bbook[- ]to[- ]bill\b", r"\bdeal wins?\b", r"\bdemand (?:environment|scenario|outlook)\b",
                  r"\bdeferred?\b.*\border", r"\bcancell?ation\b"],
    ),
    Dimension(
        key="margin_outlook",
        name="Margin outlook",
        is_redflag=False,
        anchor_0=("Margin guidance withdrawn or degraded with vague 'cost pressures' and no specific levers; "
                   "no forward margin view at all."),
        anchor_5=("Specific margin trajectory with named levers (mix, pricing, cost actions, operating leverage) "
                   "and a credible bridge to the guided range."),
        theme_feed=["Growth", "Quality"],
        keywords=[r"\bmargin(?:s)?\b", r"\boperating leverage\b", r"\bcost (?:reduction|control|takeout)\b",
                  r"\bpricing action\b", r"\bmix (?:improvement|shift)\b", r"\bEBITDA margin\b", r"\bOPM\b"],
    ),
    Dimension(
        key="capital_allocation",
        name="Capital-allocation discipline",
        is_redflag=False,
        anchor_0=("Capital deployed into unrelated/related-party ventures, dilutive raises without clear "
                   "use-of-funds, no articulated policy on debt/buyback/dividend, or reversal of stated "
                   "capital-allocation priorities."),
        anchor_5=("Clear, consistently-applied capital-allocation framework (stated ROIC hurdle, dividend/buyback "
                   "policy, debt targets) with actions matching words over multiple quarters."),
        theme_feed=["Quality"],
        keywords=[r"\bbuyback\b", r"\bdividend\b", r"\bcapital allocation\b", r"\bdebt reduction\b", r"\bROIC\b",
                  r"\bROCE\b", r"\bM&A\b", r"\bacquisition\b", r"\bde-?leverag\w*\b"],
    ),
    Dimension(
        key="red_flag_language",
        name="RED-FLAG language (evasion / blame-external / accounting-defensiveness / management churn)",
        is_redflag=True,
        anchor_0=("Multiple/severe instances: hostile or evasive non-answers to direct analyst questions, "
                   "repeated blame on 'one-off'/external factors for recurring misses, defensive/legalistic "
                   "responses on accounting questions, unexplained management/CFO/auditor departure disclosed "
                   "or alluded to on the call."),
        anchor_5=("No evasion; direct answers to tough questions; no externalization of controllable misses; "
                   "no accounting defensiveness; stable management team referenced."),
        theme_feed=["Forensic/Risk"],
        keywords=[r"\bone[- ]off\b", r"\bone[- ]time\b", r"\bexceptional item\b", r"\bmacro headwinds?\b",
                  r"\bindustry[- ]wide\b", r"\bwe (?:cannot|can't|won't) (?:comment|disclose|share)\b",
                  r"\bI (?:don't|do not) (?:have|want to get into)\b", r"\btake (?:that|this) offline\b",
                  r"\bresign(?:ed|ation)\b", r"\bstep(?:ping)? down\b", r"\bwill get back to you\b",
                  r"\bnot (?:the )?(?:right|correct) (?:forum|platform) to discuss\b"],
    ),
]

DIM_BY_KEY = {d.key: d for d in DIMENSIONS}

# ============================================================================
# 2. COMPOSITE SCORING (dimension 0-5 scores -> Management/Commentary 0-100)
# ============================================================================
# NOTE (per 01/02 docs): "Management/Commentary" is NOT one of the official 7 scoring-engine
# themes (Momentum/Value/Quality/Growth/Sentiment/Catalyst/Forensic). It is a META-SCORE that
# is computed here for interpretability/reporting, and then DISTRIBUTED into the official
# themes via THEME_FEED so it enters the composite the same way every other factor does
# (02_SCORING_ENGINE.md Step 2-3). This mirrors 10_AGENT_ARCHITECTURE.md: "Output feeds
# Growth (1Y), Management (5Y), and Forensic themes."

# Equal-weight prior across the 7 positive dimensions (a prior to be calibrated later, same
# status as every other weight in this repo — see 02_SCORING_ENGINE.md Step 3).
POSITIVE_DIM_WEIGHTS = {
    "guidance_credibility": 0.16,
    "tone_shift": 0.10,
    "capex_growth_runway": 0.14,
    "promise_vs_delivery": 0.20,   # highest — the single most falsifiable, least narrative-able dimension
    "demand_orderbook": 0.16,
    "margin_outlook": 0.12,
    "capital_allocation": 0.12,
}
assert abs(sum(POSITIVE_DIM_WEIGHTS.values()) - 1.0) < 1e-9

# How much the Management/Commentary composite matters at each horizon (0=ignore, 1=full display
# weight before it's split into THEME_FEED). Mirrors 01_PHILOSOPHY_AND_ARCHITECTURE.md's own
# "Management integrity / promoter quality" row: Penalty-only(1M) / Medium(1Y) / Dominant(5Y),
# and 07_FRAMEWORK_MICROCAP.md's note that microcaps lean hard on primary reading (concalls)
# because sell-side estimates barely exist.
HORIZON_EMPHASIS = {
    "1M":        {"positive_dims": 0.0, "red_flag": 1.0},   # only the fast red-flag catch matters intraday-to-1M
    "1Y":        {"positive_dims": 0.6, "red_flag": 1.0},
    "5Y":        {"positive_dims": 1.0, "red_flag": 1.0},   # dominant — years of promise-vs-delivery track record
    "Microcap":  {"positive_dims": 0.9, "red_flag": 1.2},   # primary-source reliance + thinner governance -> extra red-flag weight
}

# Which official scoring-engine theme(s) each dimension's signal is folded into.
THEME_FEED = {d.key: d.theme_feed for d in DIMENSIONS}


def management_commentary_score(dim_scores: dict, weights: Optional[dict] = None) -> float:
    """dim_scores: {dim_key: 0-5 float} for the 7 POSITIVE dimensions (red_flag excluded here,
    it's applied as a separate penalty via apply_redflag_penalty). Returns 0-100.
    Missing dims are simply excluded and weights renormalized (never silently imputed to a value)."""
    w = weights or POSITIVE_DIM_WEIGHTS
    present = {k: v for k, v in dim_scores.items() if k in w and v is not None}
    if not present:
        raise ValueError("no positive dimensions scored — cannot compute composite (do not impute, per D-035)")
    wsum = sum(w[k] for k in present)
    raw_0_5 = sum(present[k] * w[k] for k in present) / wsum
    return round(raw_0_5 / 5.0 * 100, 1)


def apply_redflag_penalty(base_score_0_100: float, red_flag_0_5: float, horizon: str = "1Y") -> float:
    """Light-weight version of the 08_FORENSICS_REDFLAGS.md severity model, scoped to concall
    red-flag LANGUAGE only (full context-scaled severity — size_mult/regime_mult/offset — lives
    in the forensic module; this just ensures the concall red-flag dimension actually bites).
    red_flag_0_5: 5=clean -> no penalty, 0=severe -> heavy penalty, scaled by horizon emphasis."""
    emphasis = HORIZON_EMPHASIS.get(horizon, HORIZON_EMPHASIS["1Y"])["red_flag"]
    severity = (5 - red_flag_0_5) / 5.0          # 0 (clean) .. 1 (severe)
    penalty = severity * 40 * emphasis            # up to 40pt haircut at full severity/emphasis, before clipping
    return round(max(0.0, base_score_0_100 - penalty), 1)


def horizon_theme_contribution(dim_scores: dict, horizon: str) -> dict:
    """Documentation/reporting helper: returns, per official theme, the list of dimensions
    feeding it at this horizon and their (weight * horizon_emphasis) — NOT a numeric theme
    z-score (that requires cross-sectional peers, done in 02_SCORING_ENGINE Step 1-2)."""
    emph = HORIZON_EMPHASIS.get(horizon, HORIZON_EMPHASIS["1Y"])["positive_dims"]
    out: dict = {}
    for d in DIMENSIONS:
        if d.is_redflag:
            continue
        for theme in d.theme_feed:
            out.setdefault(theme, []).append({
                "dimension": d.key,
                "score_0_5": dim_scores.get(d.key),
                "effective_weight": round(POSITIVE_DIM_WEIGHTS[d.key] * emph, 4),
            })
    out["Forensic/Risk"] = [{
        "dimension": "red_flag_language",
        "score_0_5": dim_scores.get("red_flag_language"),
        "effective_weight": HORIZON_EMPHASIS.get(horizon, HORIZON_EMPHASIS["1Y"])["red_flag"],
    }]
    return out


# ============================================================================
# 3. TRANSCRIPT STORE (loader interface — text is embedded, see module docstring)
# ============================================================================

class TranscriptStore:
    """Reads per-page extracted text straight out of extracted_texts.zip (no unzip-to-disk,
    no web fetch — a follow-up if/when we need transcripts NOT already in this zip)."""

    def __init__(self, zip_path: str = TRANSCRIPTS_ZIP):
        self.zip_path = zip_path
        self._zf = zipfile.ZipFile(zip_path)
        self._names = self._zf.namelist()
        # folder -> sorted page filenames, built once
        self._folders: dict = {}
        for n in self._names:
            parts = n.split("/")
            if len(parts) == 3 and parts[2].startswith("page_"):
                self._folders.setdefault(parts[1], []).append(n)
        for k in self._folders:
            self._folders[k].sort(key=lambda p: int(re.search(r"page_(\d+)", p).group(1)))

    def list_quarters(self, ticker: str, kind: str = "transcript") -> list:
        """kind: 'transcript' or 'ppt'. Returns sorted list of quarter labels e.g. 'Apr-2023'."""
        suffix = f"_{kind}"
        out = []
        for folder in self._folders:
            if folder.upper().startswith(ticker.upper() + "_") and folder.endswith(suffix):
                label = folder[len(ticker) + 1: -len(suffix)]
                out.append(label)
        return sorted(set(out), key=_month_year_key)

    def load_text(self, ticker: str, quarter_label: str, kind: str = "transcript") -> str:
        folder = f"{ticker}_{quarter_label}_{kind}"
        pages = self._folders.get(folder)
        if not pages:
            raise FileNotFoundError(f"no {kind} pages found for {folder} in {self.zip_path}")
        return "\n".join(self._zf.read(p).decode("utf-8", errors="replace") for p in pages)


_MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _month_year_key(label: str):
    m = re.match(r"([A-Za-z]{3})-(\d{4})", label)
    if not m:
        return (0, 0)
    return (int(m.group(2)), _MONTHS.get(m.group(1), 0))


# ============================================================================
# 4. HEURISTIC EXTRACTOR (keyword/section pull -> candidate sentences per dimension)
# ============================================================================

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def split_sentences(text: str) -> list:
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 15]


def extract_candidate_sentences(text: str, max_per_dim: int = 6) -> dict:
    """Prototype heuristic pass: for each dimension, regex-scan sentences for its keyword
    patterns and return the top hits. This is NOT a score — it is the evidence pool a human
    or the LLM-scoring hook (below) consumes to assign the 0-5 dimension score."""
    sentences = split_sentences(text)
    result = {}
    for d in DIMENSIONS:
        pats = [re.compile(p, re.IGNORECASE) for p in d.keywords]
        hits = [s for s in sentences if any(p.search(s) for p in pats)]
        result[d.key] = hits[:max_per_dim]
    return result


# ============================================================================
# 5. LLM-SCORING HOOK (stub — wired by the later LLM agent layer, NOT implemented here)
# ============================================================================

def llm_score_dimension(dimension_key: str, candidate_sentences: list, prior_quarter_context: Optional[dict] = None) -> dict:
    """*** HOOK ONLY — not implemented in this Phase-3 prototype. ***
    Per the task's hard rule (no fabrication): we do NOT call an LLM or invent a score here.
    When the Concall/Management agent (10_AGENT_ARCHITECTURE.md) is built, this function's
    body becomes: send `candidate_sentences` (+ prior_quarter_context for promise_vs_delivery
    and tone_shift) to Claude with the dimension's anchor_0/anchor_5 text as the rubric, get
    back {score: 0-5, rationale: str, evidence: [sentence,...]}, and require confidence-gating
    per 02_SCORING_ENGINE.md (low agreement/completeness -> human-in-the-loop).
    Returns a placeholder so callers can see the intended shape without a fabricated number."""
    return {
        "dimension": dimension_key,
        "score": None,
        "rationale": "LLM SCORING HOOK NOT WIRED — prototype extractor only, per hard rule against fabrication.",
        "evidence": candidate_sentences[:3],
    }


if __name__ == "__main__":
    # quick smoke test: list quarters for a couple of pilot tickers
    store = TranscriptStore()
    for tk in ["TCS", "HDFCBANK", "GRAVITA"]:
        print(tk, "->", store.list_quarters(tk))
