# S1 FINAL filter battery. Baseline +8.02 t=2.94. Adoption bar: uplift>=1.0 AND vetoed<0 AND t up.
RSI5 not 80/20: keep 218/259 | kept=+9.84(t=3.27) vetoed=-1.65(n=41) | uplift=+1.82 | ADOPT-CANDIDATE
RSI5 not 70/30: keep 160/259 | kept=+8.90(t=2.53) vetoed=+6.60(n=99) | uplift=+0.88 | reject
RSI14 not 70/30: keep 229/259 | kept=+8.90(t=3.04) vetoed=+1.26(n=30) | uplift=+0.89 | reject
skip |gap|>0.5%: keep 196/259 | kept=+7.69(t=2.50) vetoed=+9.03(n=63) | uplift=-0.32 | reject
skip |gap|>1.0%: keep 241/259 | kept=+8.56(t=3.18) vetoed=+0.76(n=18) | uplift=+0.54 | reject
skip gap-UP>0.5%: keep 220/259 | kept=+8.37(t=2.79) vetoed=+6.03(n=39) | uplift=+0.35 | reject
skip gap-DOWN<-0.5%: keep 234/259 | kept=+7.43(t=2.67) vetoed=+13.53(n=25) | uplift=-0.59 | reject
skip prior-day |ret|>1.5%: keep 243/259 | kept=+9.78(t=3.59) vetoed=-18.76(n=16) | uplift=+1.76 | ADOPT-CANDIDATE
skip vol-regime RV3>2x median: keep 247/259 | kept=+7.45(t=2.87) vetoed=+19.73(n=12) | uplift=-0.57 | reject
skip 4+ up-day streaks: keep 234/259 | kept=+7.68(t=2.65) vetoed=+11.18(n=25) | uplift=-0.34 | reject
skip |dist from 20DMA|>3%: keep 222/259 | kept=+9.00(t=3.01) vetoed=+2.11(n=37) | uplift=+0.98 | reject
skip after prev S1 loss: keep 179/259 | kept=+6.19(t=1.85) vetoed=+12.11(n=80) | uplift=-1.83 | reject

ADOPT-CANDIDATES: ['RSI5 not 80/20', 'skip prior-day |ret|>1.5%']
