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
- **Parameters**: latitude/longitude (downtown LA), `start_date`, `end_date`, `hourly=temperature_2m,apparent_temperature,precipitation,rain,snowfall,cloud_cover,wind_speed_10m`, `temperature_unit=fahrenheit`, `timezone=America/Los_Angeles`
- **Why hourly**: aggregating hours ourselves gives daily mean *and* max temperature, mean cloud cover, and mean apparent temperature.
- **Auth**: none
- **Caching**: responses saved as JSON in `data/raw/weather_cache/`, keyed by a hash of the request parameters, so re-runs never re-call the API.

## FBI UCR city crime rates (Wikipedia)

- **URL**: https://en.wikipedia.org/wiki/List_of_United_States_cities_by_crime_rate
- **What is extracted**: the main table of FBI Uniform Crime Reporting rates per 100,000 residents for large US cities. The data year is stated at the top of the page and changes when the page is updated.
- **Parsing**: BeautifulSoup finds the first `wikitable`; `pandas.read_html` handles its three-row header. Columns are matched by name, not position.
- **Snapshots**: raw HTML saved daily to `data/raw/html/`, so results are reproducible and the pipeline still runs if the page changes.
- **Terms**: Wikipedia content is CC BY-SA; the underlying FBI data is public domain.
