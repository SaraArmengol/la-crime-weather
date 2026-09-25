-- Average daily crimes by temperature bin and category (raw, unadjusted).
-- Compare these with the regression results: raw differences include seasonal effects.
SELECT
    temp_bin,
    crime_category,
    COUNT(*)                   AS n_days,
    ROUND(AVG(crime_count), 1) AS avg_daily_crimes
FROM daily_panel
GROUP BY temp_bin, crime_category
ORDER BY crime_category, temp_bin;
