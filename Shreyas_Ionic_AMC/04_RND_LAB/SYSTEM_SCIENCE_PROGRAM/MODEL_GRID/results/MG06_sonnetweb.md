Draws are i.i.d. uniform over 4 suits; T = number of draws to see all 4 suits at least once (coupon collector, 4 coupons).

**Derivation.** After the 1st draw you have 1 new suit for sure. Let T_k = number of additional draws needed to go from k distinct suits seen to k+1 distinct suits seen. While k suits have been seen, each draw has probability (4−k)/4 of being a new suit, so T_k is geometric with success probability p_k = (4−k)/4, and E[T_k] = 1/p_k = 4/(4−k).

T = T_0 + T_1 + T_2 + T_3 (going from 0→1→2→3→4 distinct suits), and by linearity:
E[T] = 4/4 + 4/3 + 4/2 + 4/1 = 1 + 4/3 + 2 + 4 = 4·(1 + 1/2 + 1/3 + 1/4).

1 + 1/2 + 1/3 + 1/4 = 12/12 + 6/12 + 4/12 + 3/12 = 25/12.

**E[T] = 4 · 25/12 = 25/3 draws (exact fraction).**

**Decimal value: 25/3 ≈ 8.3333.**