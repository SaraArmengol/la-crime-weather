# From class project to portfolio project

This project started as a CS 2316 (Data Input & Manipulation) group project at Georgia Tech,
built in a Colab notebook. This page records what came from that version, what changed, and why.

## What carried over

| Class version | Where it lives now |
|---|---|
| UCR crime-type mapping (`crime_mapping` dictionary + keyword fallbacks) | `transform/clean_crime.py` |
| Hourly Open-Meteo weather aggregated to daily values | `extract/weather.py`, `transform/clean_weather.py` |
| Weather-type labels (Snow / Rainy / Cloudy / Hot / Warm / Cool / Cold) | `transform/clean_weather.py` |
| Wikipedia UCR table scraper (BeautifulSoup + `pd.read_html`) | `extract/scrape_stats.py` |
| LA vs. California crime-mix comparison | `analysis/descriptive.py`, dashboard |
| Weather-only linear regression (scikit-learn) | `analysis/baseline.py` |

## What changed, and why

**1. Crime totals by weather type → crimes per day by weather type.**
The class version's pie chart showed Warm days had nearly half of all crimes. But that mostly
reflects how many days were warm, not how dangerous warm days are. The dashboard now shows each
weather type's share of days next to its share of crimes, and compares crimes *per day*.

**2. The 2024 "drop in crime" was a data artifact.**
The class version found crime fell sharply from 2023 to 2024. On March 7, 2024, LAPD moved to a
new records system (NIBRS), and after that date this dataset only contains incidents from the
retiring system. The analysis now ends in December 2023.

**3. Random train/test split → chronological split.**
The regression split days randomly, so it trained on days after the ones it was tested on. For
time series, the honest test trains on the past and predicts the future. A second model with
weekday and month features shows how much of daily crime the calendar explains versus the weather.

**4. Correlation-style analysis → count regression with controls.**
Hot days cluster in summer, which also has more people outdoors, school holidays, and so on.
A negative binomial regression with month, weekday, year, and holiday controls isolates the
association with weather. (Negative binomial because daily counts vary more than a Poisson
model allows.)

**5. Crime categories aligned with FBI definitions.**
To compare with the UCR table, categories must match UCR definitions:
- Simple assault and battery are not aggravated assault; they're now "Simple assault" (not in UCR Part I).
- Burglary from a vehicle is larceny under UCR, not burglary.
- Identity theft and bunco (confidence scams) are fraud, not larceny.

**6. Fallback rules no longer overwrite each other.**
The class version computed the "unmatched" mask once, so a description matching two patterns
took the *last* rule's category. For example, "SEXUAL BATTERY" matched the assault rule and was
then overwritten to "Rape". Rules now apply in order and the first match wins.

**7. First-of-month spikes.**
About [X]% of records are dated the 1st of a month versus ~3.3% expected (see the dashboard's
Data quality panel). When the exact occurrence date is unknown, especially for fraud, the 1st
is often recorded. These days are flagged in the model and hidden by default in the dashboard.

**8. Benchmark: summed rates → population-weighted rates, excluding LA.**
The Wikipedia table reports rates per 100,000 residents. Summing rates across cities treats a
city of 140,000 like a city of 1.4 million. Rates are now weighted by population, and LA is
excluded from its own benchmark. The benchmark covers large California cities, not the whole state.

**9. Smaller fixes.** Rainy day = at least 1 mm of precipitation (the class version counted any
drizzle); duplicates are removed by report number rather than whole-row matching; columns from
the scraped table are matched by name, not position.

## What was dropped

K-means clustering of days: `crime_count` was one of the clustering inputs, so finding that one
cluster had the most crime was partly circular.

## Credits

Original class project by Joy Elkhoury and Sara Armengol. The portfolio version (pipeline
architecture, tests, statistical model, dashboard, and the corrections above) is by Sara Armengol.
