# Data sources

## LAPD crime data (LA Open Data, Socrata API)

- **Endpoint**: `https://data.lacity.org/resource/2nrs-mtv8.json` ("Crime Data from 2020 to Present")
- **Query**: `$where=date_occ between '<start>' and '<end>'`, `$order=dr_no`, paged with `$limit` / `$offset`
- **Auth**: none required. An optional free app token (`SOCRATA_APP_TOKEN` in `.env`) raises rate limits.
- **Retries**: 5 attempts with exponential backoff on 429/5xx (`src/crime_weather/http.py`).
- **Caveat**: before extending the date range into 2024+, check the dataset page for notes on reporting-system changes. A sudden drop in counts is more likely a data artifact than a real trend.
- **License/terms**: [check the dataset page and record here]

## Weather (Open-Meteo Historical Weather API)

- **Endpoint**: `https://archive-api.open-meteo.com/v1/archive`
- **Parameters**: latitude/longitude (downtown LA), `start_date`, `end_date`, `daily=temperature_2m_max,...`, `temperature_unit=fahrenheit`, `timezone=America/Los_Angeles`
- **Auth**: none
- **Caching**: responses saved as JSON in `data/raw/weather_cache/`, keyed by a hash of the request parameters, so re-runs never re-call the API.
- **If your original project used a different weather API**: replace `fetch_weather` and `parse_daily` in `extract/weather.py`; keep the same output columns so nothing downstream changes.

## Scraped statistics

- **URL**: [fill in]
- **robots.txt checked**: [yes/no, date]
- **What is extracted**: [table description]
- **Snapshots**: raw HTML saved daily to `data/raw/html/` so the pipeline still runs if the page changes.
