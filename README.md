# GeoGuessr Daily Challenge Score Tracker

Pulls your own GeoGuessr Daily Challenge scores and keeps them in a
`scores.csv` you can open in Excel or Google Sheets. Everyone on the team
runs it with their own account, against a shared CSV. Rows are keyed by
date and player, so repeated runs and runs from different people merge
cleanly instead of duplicating.

Works with free GeoGuessr accounts. No premium needed.

## One-time setup

1. Install Python 3.9 or newer.
2. Install the one dependency:

   ```
   pip install -r requirements.txt
   ```

3. Get your GeoGuessr session cookie:
   - Log in at [geoguessr.com](https://www.geoguessr.com) in your browser.
   - Open developer tools (F12), go to the **Application** tab (Chrome/Edge)
     or **Storage** tab (Firefox).
   - Under **Cookies > https://www.geoguessr.com**, find the cookie named
     `_ncfa` and copy its value.
4. Copy `.env.example` to `.env` and paste your cookie value:

   ```
   GEOGUESSR_NCFA=your-cookie-value-here
   ```

   Keep this file to yourself. The cookie is your GeoGuessr login, so treat
   it like a password. It is already in `.gitignore`.

## Running it

```
python scrape.py
```

That fetches your scores for the last 100 days and adds or updates rows in
`scores.csv`. Days you didn't finish (including partial or abandoned
attempts) are skipped, same as GeoGuessr's own history page.

To pull further back, pass a date range (inclusive, UTC). There's no fixed
limit on how far back this can go, unlike GeoGuessr's small "past week"
widget: it goes back through your account's full Daily Challenge history.

```
python scrape.py --from 2026-01-01 --to 2026-07-16
python scrape.py --from 2026-01-01        # everything since Jan 1st
python scrape.py --to 2026-01-01          # everything up to Jan 1st
```

Other options:

```
python scrape.py --csv path/to/scores.csv --env-file path/to/.env
```

## The CSV

| Column | Meaning |
| --- | --- |
| challenge_date | The Daily Challenge date (UTC) |
| challenge_token | GeoGuessr's id for that challenge, if available |
| player_id | Stable GeoGuessr account id (used to dedupe) |
| player_name | Player's current nickname |
| total_score | Total score out of 25000 |
| total_time_seconds | Total time across all five rounds, if available |
| total_distance | Total guess distance as reported by GeoGuessr, if available |
| scraped_at | When this row was first captured or last changed |
| round_scores | The five round scores, separated by `;`, if available |

Rows are sorted newest date first, then highest score. GeoGuessr's own
score-history endpoint only reports the score itself, so the token, time,
distance, and round score columns can only be filled in for roughly the
last 7 days (today plus the six before it). Once a row has round scores,
later scrapes keep them. Run the scraper at least once a week so your
5k stats don't have gaps.

## Charts and statistics

```
python report.py
```

Prints a per-player stats table and saves nine charts as PNGs into `plots/`.
Charts leave out Saturday and Sunday challenges unless you pass
`--include-weekends`; the stats table always covers every day.

- `score_trends.png` — everyone's score over time
- `score_distribution.png` — box plot of each player's score spread
- `average_scores.png` — average score by player, with error bars for
  score variability
- `wins.png` — how many days each player had the top score (ties count
  for everyone tied)
- `rolling_average.png` — each player's 5-game rolling average, a smoother
  view of the trend
- `day_of_week.png` — average score per player for each day of the week
- `head_to_head.png` — how often each player beat each other player on days
  they both played
- `five_ks.png` — perfect 5000-point rounds per player, with the share of
  tracked rounds that were 5ks
- `round_averages.png` — average score for rounds 1 through 5 per player

The stats table includes games played, average/median/best/worst score,
win count/rate, and 5k count/rate (5k stats only count days with round
scores). Options:

```
python report.py --csv path/to/scores.csv --output-dir path/to/plots
python report.py --no-plots      # just print the table, skip the charts
python report.py --include-weekends
```

## Geobestr Stats dashboard

`site/` is a static, interactive dashboard that reads `scores.csv` straight
in the browser, so there's no build step. Every push to `main` runs
`.github/workflows/pages.yml`, which tests the stats code and publishes
`site/` plus the latest `scores.csv` to GitHub Pages. Scrape, commit
`scores.csv`, push, and the dashboard updates a minute later.

One-time setup: in the repo's **Settings > Pages**, set **Source** to
**GitHub Actions**.

The sidebar switches the main chart: standings, a Hall of Fame of records,
score trails, Elo power rankings, a calendar of daily winners, winning
margins, head-to-head, score spread, weekday averages, per-round stats, and
a round score histogram. Above the chart you can filter by date range,
toggle weekends and players, and turn on **Fair fight** (only days every
selected player played). Some charts have their own knobs, such as
smoothing or Elo volatility. Wins only count days with at least two
players, so a solo day isn't a win.

To preview locally, serve the repo root and open `/site/`:

```
python -m http.server 8000
# then visit http://localhost:8000/site/
```

## Sharing one CSV as a team

Each run only adds the account that ran it, so the team's data comes from
everyone pointing at the same CSV. Keep this folder in a shared location (a
git repo or shared drive) and have each person run the scraper with their
own `.env`. The upsert logic keeps the file consistent no matter who runs
it or how often.

## Troubleshooting

- **"GeoGuessr rejected the session cookie"**: your `_ncfa` cookie expired.
  Log in again and copy a fresh value into `.env`.
- **"no played days found between ... and ..."**: you didn't finish any
  Daily Challenges on this account in that range.
- A day showing up as unplayed even though you remember playing it usually
  means the game wasn't finished (all five rounds), or a streak freeze was
  used that day instead.

## Development

Run the tests with:

```
pip install pytest
python -m pytest
```

The dashboard's stats tests use Node's built-in test runner (Node 22+):

```
npm test
```
