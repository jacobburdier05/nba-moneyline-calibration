"""
Odds conversion utilities.

Shared by every script in this repository so that the probability
definitions used in the paper exist in exactly one place.
"""

import numpy as np


def american_to_raw_prob(odds):
    """Convert American moneyline odds to a raw (vig-inclusive) implied probability.

    Negative odds: p = |odds| / (|odds| + 100)
    Positive odds: p = 100 / (odds + 100)

    Parameters
    ----------
    odds : array-like of float
        American moneyline odds. Zero is not a valid moneyline and yields NaN.

    Returns
    -------
    numpy.ndarray of float
    """
    odds = np.asarray(odds, dtype=float)
    out = np.full(odds.shape, np.nan, dtype=float)

    neg = odds < 0
    pos = odds > 0

    out[neg] = np.abs(odds[neg]) / (np.abs(odds[neg]) + 100.0)
    out[pos] = 100.0 / (odds[pos] + 100.0)
    return out


def devig_proportional(p_raw_a, p_raw_b):
    """Remove the bookmaker margin by proportional normalization.

    The two raw implied probabilities of a two-outcome market sum to more
    than one. Proportional (multiplicative) normalization divides each by
    their sum so the pair sums to one. This is one normalization among
    several; see the paper's Limitations section.

    Returns
    -------
    (numpy.ndarray, numpy.ndarray)
        Vig-free probabilities for side A and side B.
    """
    p_raw_a = np.asarray(p_raw_a, dtype=float)
    p_raw_b = np.asarray(p_raw_b, dtype=float)
    total = p_raw_a + p_raw_b
    return p_raw_a / total, p_raw_b / total


def overround(p_raw_a, p_raw_b):
    """Bookmaker overround (margin) for a two-outcome market.

    Returns the excess of the raw probability sum over one, e.g. 0.038
    for a 3.8 percent margin.
    """
    return (np.asarray(p_raw_a, dtype=float)
            + np.asarray(p_raw_b, dtype=float)) - 1.0


def payout_multiple(odds):
    """Net profit per unit staked at the quoted American odds.

    A winning -150 bet returns 100/150 = 0.667 profit per unit.
    A winning +130 bet returns 1.30 profit per unit.
    """
    odds = np.asarray(odds, dtype=float)
    out = np.full(odds.shape, np.nan, dtype=float)
    neg = odds < 0
    pos = odds > 0
    out[neg] = 100.0 / np.abs(odds[neg])
    out[pos] = odds[pos] / 100.0
    return out


def breakeven_requirement(p_raw_fav, p_vigfree_fav):
    """Percentage points by which a favorite must beat its vig-free
    probability for a flat bet at the quoted price to break even.

    This equals the share of the bookmaker margin carried by the favorite
    side of the price: p_raw - p_vigfree, expressed in percentage points.
    """
    return (np.asarray(p_raw_fav, dtype=float)
            - np.asarray(p_vigfree_fav, dtype=float)) * 100.0
