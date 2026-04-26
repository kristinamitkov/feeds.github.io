# Project

...

## Storage

...

1. Store scraped files as an URL + timestamap
2. Store extracted data in SQLite

### TODO:
- Caching via ETag/Last-Modified or other headers?
- Hashing the relevant DOM block of the content?
- Chaching via content date or hash?

## Frequency

How frequently should you re-scrape? We use an adaptive scheduling. The right interval depends on:
- If a product is very important, scrape every 1 hour for 1 day. Priority between 1 and 24.
- If a product is new, scrape every 2-6 hours for 3 days. Priority between 25 and 36.
- Then, scrape every 12 hours for 7 days. Priority between 37 and 50.
- Then, scrape once daily. Priority above or equal 51.
- If a product stock status changes, scrape as if new. I.e., reset priority back to 25.
- If a product changed price (5% delta) recently, scrape as if new. I.e., reset priority back to 25.

## Alerts

...

### TODO:
- Price changed (5% delta).
- Stock change empty/full.

## Ethics

...

- How much load do we impose on the site?
- Do we respect the site's robots.txt?
