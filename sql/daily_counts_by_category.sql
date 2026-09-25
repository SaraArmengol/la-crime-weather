-- Daily crime counts by category, with a 7-day rolling average.
SELECT
    date,
    crime_category,
    crime_count,
    AVG(crime_count) OVER (
        PARTITION BY crime_category
        ORDER BY date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM daily_panel
ORDER BY date, crime_category;
