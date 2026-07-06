# MPA Live Stats

Hourly cloud job that pulls last-30-day aggregate totals (spend, leads,
registrations, purchases) across the Max Profit Ads / James Starr Consulting
Meta ad accounts and publishes them as `stats.json` for the funnel pages at
maxprofitads.ai to display.

- Contains ONLY agency-wide totals — the same numbers shown publicly on the
  sales pages. No tokens, no client names, no per-account data.
- Feed URL: https://raw.githubusercontent.com/jsou10/mpa-live-stats/main/stats.json
- If a run fails, the last good stats.json stays live (stale beats wrong).
