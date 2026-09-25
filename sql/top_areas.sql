-- LAPD areas ranked by total crime, with each area's share of the city total.
SELECT
    area_name,
    COUNT(*) AS total_crimes,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct_of_total
FROM crime
GROUP BY area_name
ORDER BY total_crimes DESC;
