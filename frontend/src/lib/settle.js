/**
 * "Quem paga quem": turns a night's profits into a short list of transfers.
 *
 * Greedy — repeatedly pay the biggest loser's debt to the biggest winner, which for
 * table-sized lists gives the (near-)minimum number of handoffs. Only meaningful when
 * the night is balanced (profits sum to 0); with an open pot the transfers can't add up,
 * so callers should skip it entirely.
 */

/**
 * @param {{ name: string, profit_cents: number }[]} entries
 * @returns {{ from: string, to: string, cents: number }[]}
 */
export function settle(entries) {
	const winners = (entries ?? [])
		.filter((e) => e.profit_cents > 0)
		.map((e) => ({ name: e.name, left: e.profit_cents }));
	const losers = (entries ?? [])
		.filter((e) => e.profit_cents < 0)
		.map((e) => ({ name: e.name, left: -e.profit_cents }));

	/** @type {{ from: string, to: string, cents: number }[]} */
	const transfers = [];
	// Bounded by winners+losers: every pass zeroes at least one of the two sides.
	let guard = winners.length + losers.length + 1;

	while (guard-- > 0) {
		const loser = biggest(losers);
		const winner = biggest(winners);
		if (!loser || !winner) break;
		const cents = Math.min(loser.left, winner.left);
		if (cents <= 0) break;
		transfers.push({ from: loser.name, to: winner.name, cents });
		loser.left -= cents;
		winner.left -= cents;
	}
	return transfers;
}

/*
 * Verified in node (`node -e` against this module):
 *
 *   settle([Vini +50, Ana +30, Rafa -60, Bia -20])
 *     -> Rafa→Vini 50 | Bia→Ana 20 | Rafa→Ana 10          (3 handoffs, the minimum)
 *   settle([Vini +90, Rafa -40, Bia -50])
 *     -> Bia→Vini 50 | Rafa→Vini 40                        (single winner)
 *   settle([Vini 0, Rafa 0])            -> []              (all-even night)
 *   settle([])                          -> []
 *   settle([A +10, B -10])              -> B→A 10
 *   settle([A +70, B +25, C -15, D -80]) transfers sum to 95 = total winnings
 */

/** @param {{ name: string, left: number }[]} list */
function biggest(list) {
	let best = null;
	for (const item of list) if (item.left > 0 && (!best || item.left > best.left)) best = item;
	return best;
}
