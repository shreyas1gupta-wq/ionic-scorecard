# COVID BACKCAST (MODEL — validated corr=0.64 vs real 2021-26; k=1.03, n_val=149)

CONST S1: n=73 net=+18.23 total=+1331 pts | maxDD=-159 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=+429 worst=-48 | worst5={'2021-02-04': -58.0, '2020-11-19': -54.0, '2021-03-04': -53.0, '2020-03-05': -48.0, '2020-06-11': -48.0}

CONST S1b: n=73 net=+17.49 total=+1277 pts | maxDD=-134 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=+353 worst=-45 | worst5={'2021-01-28': -56.0, '2021-03-04': -55.0, '2021-04-01': -55.0, '2021-01-14': -46.0, '2020-06-11': -45.0}

CONST V2: n=73 net=+2.84 total=+207 pts | maxDD=-713 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=+558 worst=-100 | worst5={'2020-03-05': -100.0, '2020-06-11': -100.0, '2021-02-04': -98.0, '2021-03-04': -96.0, '2020-11-19': -89.0}

STRESS S1: n=73 net=+0.28 total=+20 pts | maxDD=-349 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=-285 worst=-168 | worst5={'2020-03-19': -168.0, '2020-03-26': -166.0, '2020-04-09': -86.0, '2021-03-04': -82.0, '2020-05-14': -60.0}

STRESS S1b: n=73 net=-0.66 total=-48 pts | maxDD=-569 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=-251 worst=-169 | worst5={'2020-03-19': -169.0, '2020-03-26': -157.0, '2020-04-09': -101.0, '2021-03-04': -69.0, '2020-05-14': -66.0}

STRESS V2: n=73 net=-16.89 total=-1233 pts | maxDD=-1551 | CRASH WINDOW (20Feb-10Apr 2020): n=8 total=-172 worst=-207 | worst5={'2020-03-26': -207.0, '2020-04-09': -176.0, '2020-03-05': -109.0, '2021-03-04': -108.0, '2021-01-28': -103.0}

SURVIVAL(STRESS,S1) @75% deploy on 10L: final=9.9L maxDD=-16%

SURVIVAL(STRESS,S1b) @75% deploy on 10L: final=9.5L maxDD=-25%

SURVIVAL(STRESS,V2) @75% deploy on 10L: final=5.3L maxDD=-54%
