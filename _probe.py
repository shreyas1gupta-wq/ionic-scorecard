import sys, os, pickle
KIT = r"C:/tmp/kit-publish/ionic-deck-kit"
sys.path.insert(0, os.path.join(KIT, "build"))
sys.path.insert(0, os.path.join(KIT, "parse"))
sys.path.insert(0, r"C:/tmp/kit-publish/Shreyas_Ionic_AMC/09_PRODUCT/pr_template")
STMT, CLIENT, OUTP = sys.argv[1], sys.argv[2], sys.argv[3]
import engine as ENG
_real = ENG.build
CAP = {}
def fake(ctx, tier, verbose=True):
    CAP['ctx'] = ctx
    with open(OUTP, "wb") as fh: pickle.dump(ctx, fh)
    return _real(ctx, tier, verbose=verbose)
ENG.build = fake
import build_review
build_review.ENG.build = fake
sys.argv = ["build_review.py", STMT, "--client", CLIENT, "--profile", "Aggressive"]
build_review.main()
print("CTX DUMPED ->", OUTP)
