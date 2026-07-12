# Coupon Collector Problem: Expected Draws for All 4 Suits

## Problem Statement
Cards are drawn one at a time from an infinite stream where each card is one of 4 suits, uniformly at random and independently. Find E[T], where T is the number of draws until all 4 suits have been seen at least once.

## Solution

### Method: Linearity of Expectation Over Phases

Partition the problem into phases based on how many distinct suits have been collected:

**Phase i (i = 1, 2, 3, 4):** Number of draws needed to obtain the i-th distinct suit, given that i-1 suits are already in hand.

Let X_i = draws in phase i. Then:
$$T = X_1 + X_2 + X_3 + X_4$$

By linearity of expectation:
$$E[T] = \sum_{i=1}^{4} E[X_i]$$

### Computing Each Phase

**Phase 1:** Get any first suit
- The first draw always succeeds
- E[X_1] = 1

**Phase 2:** Get a second distinct suit (1 suit already seen)
- Probability of drawing a new suit: p = 3/4
- X_2 ~ Geometric(3/4), so E[X_2] = 1/p = 4/3

**Phase 3:** Get a third distinct suit (2 suits already seen)
- Probability of drawing a new suit: p = 2/4 = 1/2
- X_3 ~ Geometric(1/2), so E[X_3] = 1/p = 2

**Phase 4:** Get the fourth distinct suit (3 suits already seen)
- Probability of drawing a new suit: p = 1/4
- X_4 ~ Geometric(1/4), so E[X_4] = 1/p = 4

### Final Calculation

$$E[T] = 1 + \frac{4}{3} + 2 + 4$$

Converting to common denominator (3):
$$E[T] = \frac{3}{3} + \frac{4}{3} + \frac{6}{3} + \frac{12}{3} = \frac{25}{3}$$

## Answer

**Exact value (fraction):** 25/3

**Decimal value:** 8.333... (or 8.3̄ with 3 repeating)

**Derivation:** Using the coupon collector framework, the expected waiting time is the sum of four geometric waiting periods, each with decreasing success probability as more suits are collected. The general formula for n suits is E[T] = n·H_n where H_n is the nth harmonic number. For n=4: E[T] = 4·(1 + 1/2 + 1/3 + 1/4) = 4·(25/12) = 25/3.

