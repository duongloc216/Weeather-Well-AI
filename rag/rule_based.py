import json

def interpret_weather(weather_data: dict) -> str:
    """
    Interprets all weather data parameters into a descriptive text.
    
    Args:
        weather_data (dict): A dictionary containing all weather details.
        
    Returns:
        str: A comprehensive text interpretation of the weather conditions.
    """
    temp = weather_data.get("temp")
    feels_like = weather_data.get("feels_like")
    humidity = weather_data.get("humidity")
    pop = weather_data.get("pop")
    wind_speed = weather_data.get("wind_speed")
    wind_gust = weather_data.get("wind_gust")
    visibility = weather_data.get("visibility")
    clouds_all = weather_data.get("clouds_all")
    weather_main = weather_data.get("weather_main")
    weather_description = weather_data.get("weather_description")
    
    interpretations = []

    # Temperature and Feels Like
    if temp is not None and feels_like is not None:
        interpretations.append(f"Nhiệt độ không khí là {temp}°C, cảm giác như {feels_like}°C.")
        if 20 <= feels_like <= 28:
            interpretations.append("Nhiệt độ cảm nhận rất dễ chịu, lý tưởng cho các hoạt động ngoài trời.")
        elif feels_like > 35:
            interpretations.append("Nhiệt độ cảm nhận rất nóng. Cần cẩn thận với tình trạng say nắng.")
        elif feels_like > 28:
            interpretations.append("Nhiệt độ cảm nhận khá nóng.")
        elif feels_like < 15:
            interpretations.append("Nhiệt độ cảm nhận khá lạnh. Bạn nên mặc ấm.")

    # Humidity
    if humidity is not None:
        if 40 <= humidity <= 70:
            interpretations.append(f"Độ ẩm ở mức lý tưởng ({humidity}%), không khí trong lành.")
        elif humidity > 80:
            interpretations.append(f"Độ ẩm cao ({humidity}%), không khí khá ẩm ướt.")
        elif humidity < 40:
            interpretations.append(f"Độ ẩm thấp ({humidity}%), không khí khá khô.")

    # Wind
    if wind_speed is not None:
        interpretations.append(f"Tốc độ gió là {wind_speed} m/s.")
        if wind_gust and wind_gust > 15: 
            interpretations.append(f"Có gió giật mạnh, lên tới {wind_gust} m/s.")
        elif wind_speed > 10:
            interpretations.append("Gió khá mạnh.")
        else:
            interpretations.append("Gió nhẹ và êm ái.")

    # Probability of Precipitation (POP)
    if pop is not None:
        if pop > 0.7:
            interpretations.append(f"Xác suất mưa rất cao ({int(pop*100)}%).")
        elif pop > 0.4:
            interpretations.append(f"Có khả năng mưa vừa phải ({int(pop*100)}%).")
        else:
            interpretations.append(f"Xác suất mưa thấp ({int(pop*100)}%).")

    # Visibility and Cloudiness
    if visibility is not None:
        if visibility >= 10000:
            interpretations.append("Tầm nhìn xa rất tốt, đạt 10 km.")
        elif visibility < 5000:
            interpretations.append(f"Tầm nhìn xa kém, khoảng {visibility} mét.")
    
    if clouds_all is not None:
        if clouds_all == 0:
            interpretations.append("Bầu trời quang đãng, không có mây.")
        elif clouds_all > 75:
            interpretations.append(f"Bầu trời rất nhiều mây ({clouds_all}%).")
        else:
            interpretations.append(f"Mức độ mây ở mức trung bình ({clouds_all}%).")
        
    # Main Weather Description - translate common weather conditions
    weather_vi = {
        'Clear': 'Trời quang', 'Rain': 'Mưa', 'Drizzle': 'Mưa phùn', 
        'Clouds': 'Có mây', 'Snow': 'Tuyết', 'Thunderstorm': 'Giông bão',
        'Mist': 'Sương mù', 'Fog': 'Sương mù', 'Haze': 'Sương mù nhẹ'
    }
    weather_main_vi = weather_vi.get(weather_main, weather_main)
    interpretations.append(f"Tình trạng thời tiết chính là '{weather_main_vi}' với mô tả '{weather_description}'.")

    return " ".join(interpretations)

def interpret_climate(climate_data: dict) -> str:
    """
    Interprets all climate data parameters into a descriptive text.
    
    Args:
        climate_data (dict): A dictionary containing all climate details.
        
    Returns:
        str: A comprehensive text interpretation of the climate conditions.
    """
    aqi = climate_data.get("aqi")
    co = climate_data.get("co")
    no = climate_data.get("no")
    no2 = climate_data.get("no2")
    o3 = climate_data.get("o3")
    so2 = climate_data.get("so2")
    pm2_5 = climate_data.get("pm2_5")
    pm10 = climate_data.get("pm10")
    nh3 = climate_data.get("nh3")

    interpretations = []

    # AQI
    if aqi is not None:
        if aqi == 1:
            interpretations.append(f"Chỉ số chất lượng không khí (AQI) ở mức Tốt ({aqi}). Không khí trong lành và khỏe mạnh.")
        elif aqi == 2:
            interpretations.append(f"Chỉ số chất lượng không khí (AQI) ở mức Trung bình ({aqi}).")
        elif aqi == 3:
            interpretations.append(f"Chỉ số chất lượng không khí (AQI) ở mức Vừa phải ({aqi}).")
        elif aqi == 4:
            interpretations.append(f"Chỉ số chất lượng không khí (AQI) ở mức Kém ({aqi}).")
        elif aqi == 5:
            interpretations.append(f"Chỉ số chất lượng không khí (AQI) ở mức Rất kém ({aqi}).")
    
    # PM2.5
    if pm2_5 is not None:
        if pm2_5 < 10:
            interpretations.append(f"Nồng độ bụi mịn PM2.5 thấp ở mức {pm2_5} μg/m3, rất tốt cho sức khỏe.")
        elif 10 <= pm2_5 < 25:
            interpretations.append(f"Nồng độ PM2.5 ở mức trung bình, ở {pm2_5} μg/m3.")
        elif 25 <= pm2_5 < 50:
            interpretations.append(f"Nồng độ PM2.5 cao, ở {pm2_5} μg/m3.")
        elif 50 <= pm2_5 < 75:
            interpretations.append(f"Nồng độ PM2.5 ở mức kém, ở {pm2_5} μg/m3.")
        else:
            interpretations.append(f"Nồng độ PM2.5 ở mức rất kém, ở {pm2_5} μg/m3.")

    # PM10
    if pm10 is not None:
        if pm10 < 20:
            interpretations.append(f"Nồng độ bụi thô PM10 thấp ở mức {pm10} μg/m3.")
        elif 20 <= pm10 < 50:
            interpretations.append(f"Nồng độ PM10 ở mức trung bình, ở {pm10} μg/m3.")
        elif 50 <= pm10 < 100:
            interpretations.append(f"Nồng độ PM10 ở mức vừa phải, ở {pm10} μg/m3.")
        elif 100 <= pm10 < 200:
            interpretations.append(f"Nồng độ PM10 ở mức kém, ở {pm10} μg/m3.")
        else:
            interpretations.append(f"Nồng độ PM10 ở mức rất kém, ở {pm10} μg/m3.")

    # O3
    if o3 is not None:
        if o3 < 60:
            interpretations.append(f"Nồng độ Ozone (O3) ở mức tốt, ở {o3} μg/m3.")
        elif 60 <= o3 < 100:
            interpretations.append(f"Nồng độ O3 ở mức trung bình, ở {o3} μg/m3.")
        elif 100 <= o3 < 140:
            interpretations.append(f"Nồng độ O3 ở mức vừa phải, ở {o3} μg/m3.")
        elif 140 <= o3 < 180:
            interpretations.append(f"Nồng độ O3 ở mức kém, ở {o3} μg/m3.")
        else:
            interpretations.append(f"Nồng độ O3 ở mức rất kém, ở {o3} μg/m3.")

    # Other pollutants
    if co is not None:
        if co < 4400:
            interpretations.append(f"Nồng độ Carbon Monoxide (CO) ở mức tốt, ở {co} μg/m3.")
        elif 4400 <= co < 9400:
            interpretations.append(f"Nồng độ CO ở mức trung bình, ở {co} μg/m3.")
        else:
            interpretations.append(f"Nồng độ CO cao, ở {co} μg/m3.")
    
    if no2 is not None:
        if no2 < 40:
            interpretations.append(f"Nồng độ Nitrogen Dioxide (NO2) ở mức tốt, ở {no2} μg/m3.")
        elif 40 <= no2 < 70:
            interpretations.append(f"Nồng độ NO2 ở mức trung bình, ở {no2} μg/m3.")
        else:
            interpretations.append(f"Nồng độ NO2 ở mức vừa phải, ở {no2} μg/m3.")
    
    if so2 is not None:
        if so2 < 20:
            interpretations.append(f"Nồng độ Sulfur Dioxide (SO2) ở mức tốt, ở {so2} μg/m3.")
        elif 20 <= so2 < 80:
            interpretations.append(f"Nồng độ SO2 ở mức trung bình, ở {so2} μg/m3.")
        else:
            interpretations.append(f"Nồng độ SO2 cao, ở {so2} μg/m3.")
        
    if nh3 is not None:
        if nh3 < 20:
            interpretations.append(f"Nồng độ Ammonia (NH3) ở mức tốt, ở {nh3} μg/m3.")
        else:
            interpretations.append(f"Nồng độ Ammonia (NH3) cao, ở {nh3} μg/m3.")

    return " ".join(interpretations)

def interpret_uv_index(uv_data: dict) -> str:
    """
    Interprets the UV index (UVI) into a descriptive text.
    
    Args:
        uv_data (dict): A dictionary containing the UV index.
        
    Returns:
        str: A text interpretation of the UV index.
    """
    uvi = uv_data.get("uvi")
    interpretations = []

    if uvi is not None:
        if uvi < 3:
            interpretations.append(f"Chỉ số UV ở mức Thấp ({uvi}). An toàn khi ra ngoài mà không cần bảo vệ.")
        elif uvi < 6:
            interpretations.append(f"Chỉ số UV ở mức Trung bình ({uvi}). Nên bảo vệ khi ra ngoài trong thời gian dài.")
        elif uvi < 8:
            interpretations.append(f"Chỉ số UV ở mức Cao ({uvi}). Bạn nên che chắn và sử dụng kem chống nắng khi ra ngoài.")
        elif uvi < 11:
            interpretations.append(f"Chỉ số UV ở mức Rất cao ({uvi}). Tốt nhất là hạn chế thời gian ra ngoài, đặc biệt vào buổi trưa, và bảo vệ toàn diện.")
        else:
            interpretations.append(f"Chỉ số UV ở mức Cực kỳ nguy hiểm ({uvi}). Bạn phải cực kỳ cẩn thận và tránh ánh nắng trực tiếp.")

    return " ".join(interpretations)


def interpret_daily_data_for_single_user_city(user_city_data: dict) -> list:
    """
    Interprets weather, climate, and UV data for each period of a single user-city pair,
    and returns a list of interpreted text strings.

    Args:
        user_city_data (dict): A dictionary representing a single user-city pair
                               with their daily data.

    Returns:
        list: A list containing a single string that combines all interpreted data
              for all periods.
    """
    interpreted_texts = []
    
    # Access periods from the daily_data structure
    periods = user_city_data["daily_data"][0]["periods"]
    
    for period_data in periods:
        # Interpret each set of data
        weather_text = interpret_weather(period_data["weather_details"])
        climate_text = interpret_climate(period_data["climate_details"])
        uvi_text = interpret_uv_index(period_data["uvi_details"])
        
        # Combine interpretations into a single string
        # Không cần thêm tên period vào đây nữa, sẽ xử lý ở create_query_question
        full_interpretation = (
            f"Weather conditions: {weather_text} "
            f"Air quality: {climate_text} "
            f"UV radiation: {uvi_text}"
        )

        interpreted_texts.append(full_interpretation)
        
    return interpreted_texts