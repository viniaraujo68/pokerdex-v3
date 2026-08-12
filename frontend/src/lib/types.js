/**
 * JSDoc typedefs for the API payloads, mirroring `backend/app/schemas.py`.
 *
 * Types only — this module emits no runtime code, so importing it costs nothing. It exists
 * because `checkJs` is on: without a name for these shapes every `let x = $state(null)` and
 * every `.map((e) => ...)` degrades to `any`, and the checker stops being able to tell a
 * typo from a field. Keep it in step with `schemas.py`; when the two disagree, the Python
 * file is right.
 *
 * Money is always integer cents. Dates are ISO `YYYY-MM-DD` strings (pydantic serializes
 * `datetime.date` that way), never `Date` objects.
 */

/**
 * @typedef {object} User
 * @property {number} id
 * @property {string} username
 */

/**
 * A group as its owner sees it (`GroupOut`).
 * @typedef {object} Group
 * @property {number} id
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {string} currency
 * @property {'public'|'private'} visibility
 * @property {string|null} share_token
 * @property {number} night_count
 * @property {number} participant_count
 */

/**
 * Catalog entry (`NamedOut`) — places, today.
 * @typedef {object} Named
 * @property {number} id
 * @property {string} name
 */

/**
 * @typedef {object} Participant
 * @property {number} id
 * @property {string} name
 * @property {boolean} active `false` after a soft delete; reactivatable.
 */

/**
 * One player's line in a night (`EntryOut`).
 * @typedef {object} Entry
 * @property {number} id
 * @property {number} participant_id
 * @property {string} participant_name
 * @property {number} buy_in_cents
 * @property {number} cash_out_cents
 * @property {number} profit_cents
 */

/**
 * @typedef {object} Night
 * @property {number} id
 * @property {string} date
 * @property {number|null} place_id
 * @property {string|null} place_name
 * @property {Entry[]} entries
 * @property {number} total_pot_cents
 * @property {number} balance_cents Sum of profits; ~0 when the pot closes.
 */

/**
 * What the night form POSTs/PUTs (`NightCreate`). Note it carries no `id`s of its own:
 * entries are addressed by participant, and the server replaces the whole set.
 * @typedef {object} NightPayload
 * @property {string} date
 * @property {number|null} place_id
 * @property {{ participant_id: number, buy_in_cents: number, cash_out_cents: number }[]} entries
 */

/**
 * @typedef {object} RankingRow
 * @property {number} participant_id
 * @property {string} name
 * @property {number} total_profit_cents
 * @property {number} nights_played
 * @property {number} avg_profit_cents
 * @property {number} total_buy_in_cents
 * @property {number|null} roi profit / buy-in; `null` when nothing was ever bought in
 */

/**
 * @typedef {object} GroupRecord
 * @property {string} label Portuguese label from the backend; `Records.svelte` maps the known ones.
 * @property {string|null} participant_name
 * @property {number|null} value_cents `null` when the group has no data for this record yet.
 * @property {string|null} night_date
 */

/**
 * @typedef {object} Stats
 * @property {RankingRow[]} ranking
 * @property {GroupRecord[]} records
 * @property {number} total_nights
 */

/**
 * @typedef {object} EvolutionPoint
 * @property {string} date
 * @property {number|null} cumulative_cents `null` before the participant's first night, so
 *   every series lines up with `Evolution.dates`.
 */

/**
 * @typedef {object} EvolutionSeries
 * @property {number} participant_id
 * @property {string} name
 * @property {EvolutionPoint[]} points
 */

/**
 * @typedef {object} Evolution
 * @property {string[]} dates
 * @property {EvolutionSeries[]} series
 */

/**
 * A row of the public directory (`PublicGroupSummary`) — no `id`, no token: the slug is the
 * only handle a visitor gets.
 * @typedef {object} PublicGroupSummary
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {number} night_count
 * @property {number} participant_count
 */

/**
 * A public scoreboard (`PublicGroupOut`).
 * @typedef {object} PublicGroup
 * @property {string} name
 * @property {string} slug
 * @property {string} description
 * @property {string} currency
 * @property {Stats} stats
 * @property {Evolution} evolution
 * @property {Night[]} nights
 */

export {};
