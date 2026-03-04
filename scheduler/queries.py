# queries.py

GET_FULL_DATA_QUERY = """
    SELECT
        uc.user_id, uc.city_id, d.disease_name, u.describe_disease,
        w.period, w.report_day, w.report_month, w.report_year,
        w.temp, w.feels_like, w.humidity, w.pop, w.wind_speed, w.wind_gust, w.visibility, w.clouds_all,
        w.weather_main, w.weather_description,
        cl.aqi, cl.co, cl.no, cl.no2, cl.o3, cl.so2, cl.pm2_5, cl.pm10, cl.nh3,
        uvid.uvi
    FROM user_city uc
    JOIN users u ON uc.user_id = u.user_id
    JOIN disease d ON u.disease_id = d.disease_id
    JOIN weather w ON uc.city_id = w.city_id
    JOIN climate cl ON uc.city_id = cl.city_id
    JOIN uv uvid ON uc.city_id = uvid.city_id
    WHERE
        w.report_day = ? AND w.report_month = ? AND w.report_year = ? AND
        cl.report_day = ? AND cl.report_month = ? AND cl.report_year = ? AND
        uvid.report_day = ? AND uvid.report_month = ? AND uvid.report_year = ? AND
        w.period = cl.period AND w.period = uvid.period;
"""