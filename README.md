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

That fetches your scores for the last 7 days and adds or updates rows in
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

Rows are sorted newest date first, then highest score. GeoGuessr's own
score-history endpoint only reports the score itself for older days, not
time or distance, so those two columns are blank for anything pulled in
via `--from`/`--to`. Recent days may have them filled in.

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
