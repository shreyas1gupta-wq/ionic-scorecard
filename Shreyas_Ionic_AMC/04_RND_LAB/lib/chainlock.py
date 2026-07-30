"""chainlock — a cross-process semaphore so concurrent agents cannot collectively exhaust RAM.

WHY THIS EXISTS
  `chain.load_expiry` is lru_cache(maxsize=64) and each NIFTY expiry is ~40MB, so ONE unbounded
  loop reaches ~2.5GB. Four jobs died with rc=3221225477 (Windows STATUS_ACCESS_VIOLATION, the
  out-of-memory signature here) on 2026-07-30 for exactly that reason.
  On 2026-07-31 the machine had **2.1GB available of 16.8GB** while SEVEN agents were running, at
  least five of which needed the option chain. Telling each agent "keep under 1.5GB" is not enough:
  five well-behaved 1.5GB jobs still need 7.5GB that does not exist. The constraint is GLOBAL, so
  the fix has to be global.

WHAT IT DOES
  A directory-based counting semaphore (atomic `os.mkdir`, works across processes on Windows with no
  extra dependencies). Default MAX_HOLDERS=2 heavy readers at a time; the rest wait. Stale slots from
  a crashed process are reclaimed automatically after STALE_SEC, so a segfault cannot deadlock the
  whole fleet.

USAGE — wrap the HEAVY part only, not your whole run:

    import sys; sys.path.insert(0, r"...\\04_RND_LAB\\lib")
    from chainlock import chain_slot, free_ram_gb
    import chain, gc

    for exp in expiries:
        with chain_slot("optbuy-A"):          # blocks until a slot frees
            df = chain.load_expiry(exp)
            ... extract what you need into a SMALL frame ...
        chain.load_expiry.cache_clear(); gc.collect()   # release BEFORE the next slot

  Do the reduction INSIDE the slot and keep only the small result. Holding a slot while you compute
  for ten minutes starves everyone else — grab, extract, release.

  `free_ram_gb()` lets a script degrade gracefully: if free RAM is under ~1.2GB, checkpoint what you
  have to disk and exit cleanly rather than dying mid-write.
"""
from __future__ import annotations

import os
import time
from contextlib import contextmanager
from pathlib import Path

LOCK_ROOT = Path(os.environ.get("TEMP", "C:/tmp")) / "sionic_chainlock"
MAX_HOLDERS = int(os.environ.get("CHAINLOCK_MAX", "2"))
STALE_SEC = 900          # a slot older than 15 min is assumed crashed and is reclaimed
POLL_SEC = 3.0
WAIT_WARN_SEC = 120


def free_ram_gb() -> float:
    """Available RAM in GB. Returns a large number if psutil is unavailable, so callers proceed."""
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except Exception:
        return 99.0


def _reap():
    """Remove slots whose owning process is gone or whose lease has expired."""
    if not LOCK_ROOT.exists():
        return
    now = time.time()
    for d in list(LOCK_ROOT.iterdir()):
        if not d.is_dir():
            continue
        try:
            age = now - d.stat().st_mtime
            pid_f = d / "pid"
            dead = False
            if pid_f.exists():
                try:
                    pid = int(pid_f.read_text().strip())
                    import psutil
                    dead = not psutil.pid_exists(pid)
                except Exception:
                    dead = False
            if dead or age > STALE_SEC:
                for f in d.iterdir():
                    try:
                        f.unlink()
                    except OSError:
                        pass
                d.rmdir()
        except OSError:
            pass


def _try_acquire(tag: str):
    LOCK_ROOT.mkdir(parents=True, exist_ok=True)
    _reap()
    for i in range(MAX_HOLDERS):
        d = LOCK_ROOT / f"slot{i}"
        try:
            d.mkdir()                                  # atomic: only one process wins
            (d / "pid").write_text(str(os.getpid()))
            (d / "tag").write_text(tag)
            return d
        except FileExistsError:
            continue
    return None


@contextmanager
def chain_slot(tag: str = "anon", timeout: float = 3600.0, min_free_gb: float = 0.0):
    """Block until one of MAX_HOLDERS slots is free, then hold it for the duration of the block.

    tag          : who you are, for debugging a stuck fleet
    timeout      : give up after this many seconds and raise TimeoutError
    min_free_gb  : if >0, also wait until this much RAM is actually free before proceeding
    """
    t0 = time.time()
    warned = False
    d = None
    while True:
        if free_ram_gb() >= min_free_gb:
            d = _try_acquire(tag)
        if d is not None:
            break
        waited = time.time() - t0
        if waited > timeout:
            raise TimeoutError(f"chainlock: no slot after {waited:.0f}s (tag={tag}). "
                               f"MAX_HOLDERS={MAX_HOLDERS}, free={free_ram_gb():.1f}GB")
        if waited > WAIT_WARN_SEC and not warned:
            print(f"[chainlock] {tag} waiting {waited:.0f}s for a slot "
                  f"(free RAM {free_ram_gb():.1f}GB)", flush=True)
            warned = True
        time.sleep(POLL_SEC)
    try:
        yield d
    finally:
        try:
            for f in d.iterdir():
                try:
                    f.unlink()
                except OSError:
                    pass
            d.rmdir()
        except OSError:
            pass


def status() -> str:
    _reap()
    if not LOCK_ROOT.exists():
        return f"chainlock: 0/{MAX_HOLDERS} held, free {free_ram_gb():.1f}GB"
    held = []
    for d in sorted(LOCK_ROOT.iterdir()):
        if d.is_dir():
            tag = (d / "tag").read_text().strip() if (d / "tag").exists() else "?"
            pid = (d / "pid").read_text().strip() if (d / "pid").exists() else "?"
            held.append(f"{d.name}={tag}(pid {pid})")
    return (f"chainlock: {len(held)}/{MAX_HOLDERS} held [{', '.join(held) or 'none'}], "
            f"free {free_ram_gb():.1f}GB")


def self_test():
    print(status())
    with chain_slot("self-test-1"):
        print(" inside slot 1:", status())
        with chain_slot("self-test-2", timeout=10):
            print(" inside slot 2:", status())
            try:
                with chain_slot("self-test-3", timeout=4):
                    raise AssertionError("third slot should NOT have been granted at MAX_HOLDERS=2")
            except TimeoutError:
                print(" [ok] third concurrent holder correctly refused")
    print(" after release:", status())
    print("chainlock ok")


if __name__ == "__main__":
    self_test()
