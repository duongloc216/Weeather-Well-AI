-- ============================================
-- WEATHERWELL AI - SQL SERVER DATABASE SCHEMA
-- ============================================

USE master;
GO

-- Tạo database nếu chưa tồn tại
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'WeatherWell_AI')
BEGIN
    CREATE DATABASE WeatherWell_AI;
END
GO

USE WeatherWell_AI;
GO

-- ============================================
-- 1. TABLE: disease (Danh mục bệnh)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'disease') AND type in (N'U'))
BEGIN
    CREATE TABLE disease (
        disease_id INT PRIMARY KEY,
        disease_name NVARCHAR(100) NOT NULL
    );
END
GO

-- ============================================
-- 2. TABLE: users (Thông tin người dùng)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'users') AND type in (N'U'))
BEGIN
    CREATE TABLE users (
        user_id INT IDENTITY(1,1) PRIMARY KEY,
        username NVARCHAR(50) UNIQUE NOT NULL,
        email NVARCHAR(100) UNIQUE NOT NULL,
        password NVARCHAR(255) NOT NULL,
        disease_id INT NULL FOREIGN KEY REFERENCES disease(disease_id),
        describe_disease NVARCHAR(MAX) NULL
    );
END
GO

-- ============================================
-- 3. TABLE: city (Danh sách thành phố)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'city') AND type in (N'U'))
BEGIN
    CREATE TABLE city (
        city_id INT PRIMARY KEY,
        city_name NVARCHAR(100) NOT NULL,
        longitude FLOAT NOT NULL,
        latitude FLOAT NOT NULL
    );
END
GO

-- ============================================
-- 4. TABLE: user_city (Quan hệ user-city)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'user_city') AND type in (N'U'))
BEGIN
    CREATE TABLE user_city (
        user_id INT NOT NULL FOREIGN KEY REFERENCES users(user_id) ON DELETE CASCADE,
        city_id INT NOT NULL FOREIGN KEY REFERENCES city(city_id) ON DELETE CASCADE,
        PRIMARY KEY (user_id, city_id)
    );
END
GO

-- ============================================
-- 5. TABLE: weather (Dữ liệu thời tiết)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'weather') AND type in (N'U'))
BEGIN
    CREATE TABLE weather (
        weather_id INT IDENTITY(1,1) PRIMARY KEY,
        city_id INT NOT NULL FOREIGN KEY REFERENCES city(city_id),
        report_year INT NOT NULL,
        report_month INT NOT NULL,
        report_day INT NOT NULL,
        period NVARCHAR(20) NOT NULL,
        temp FLOAT NULL,
        feels_like FLOAT NULL,
        humidity INT NULL,
        pop FLOAT NULL,
        rain_3h FLOAT NULL,
        wind_speed FLOAT NULL,
        wind_gust FLOAT NULL,
        visibility INT NULL,
        clouds_all INT NULL,
        weather_main NVARCHAR(50) NULL,
        weather_description NVARCHAR(100) NULL,
        weather_icon NVARCHAR(10) NULL,
        CONSTRAINT UQ_weather_city_date_period UNIQUE (city_id, report_year, report_month, report_day, period)
    );
END
GO

-- ============================================
-- 6. TABLE: climate (Chất lượng không khí)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'climate') AND type in (N'U'))
BEGIN
    CREATE TABLE climate (
        climate_id INT IDENTITY(1,1) PRIMARY KEY,
        city_id INT NOT NULL FOREIGN KEY REFERENCES city(city_id),
        report_year INT NOT NULL,
        report_month INT NOT NULL,
        report_day INT NOT NULL,
        period NVARCHAR(20) NOT NULL,
        aqi INT NULL,
        co FLOAT NULL,
        no FLOAT NULL,
        no2 FLOAT NULL,
        o3 FLOAT NULL,
        so2 FLOAT NULL,
        pm2_5 FLOAT NULL,
        pm10 FLOAT NULL,
        nh3 FLOAT NULL,
        CONSTRAINT UQ_climate_city_date_period UNIQUE (city_id, report_year, report_month, report_day, period)
    );
END
GO

-- ============================================
-- 7. TABLE: uv (Chỉ số UV)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'uv') AND type in (N'U'))
BEGIN
    CREATE TABLE uv (
        uv_id INT IDENTITY(1,1) PRIMARY KEY,
        city_id INT NOT NULL FOREIGN KEY REFERENCES city(city_id),
        report_year INT NOT NULL,
        report_month INT NOT NULL,
        report_day INT NOT NULL,
        period NVARCHAR(20) NOT NULL,
        uvi FLOAT NULL,
        CONSTRAINT UQ_uv_city_date_period UNIQUE (city_id, report_year, report_month, report_day, period)
    );
END
GO

-- ============================================
-- 8. TABLE: suggestion (Gợi ý sức khỏe AI)
-- ============================================
IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'suggestion') AND type in (N'U'))
BEGIN
    CREATE TABLE suggestion (
        user_id INT NOT NULL FOREIGN KEY REFERENCES users(user_id) ON DELETE CASCADE,
        city_id INT NOT NULL FOREIGN KEY REFERENCES city(city_id) ON DELETE CASCADE,
        text_suggestion NVARCHAR(MAX) NULL,
        report_year INT NULL,
        report_month INT NULL,
        report_day INT NULL,
        PRIMARY KEY (user_id, city_id)
    );
END
GO

-- ============================================
-- INSERT DỮ LIỆU MẪU
-- ============================================

-- Danh mục bệnh
IF NOT EXISTS (SELECT 1 FROM disease WHERE disease_id = 1)
BEGIN
    INSERT INTO disease (disease_id, disease_name) VALUES
    (1, 'respiratory'),      -- Bệnh đường hô hấp (hen suyễn, viêm phổi)
    (2, 'diabetes'),         -- Tiểu đường
    (3, 'cardiovascular'),   -- Tim mạch
    (4, 'allergies'),        -- Dị ứng
    (5, 'hypertension'),     -- Huyết áp cao
    (6, 'skin'),             -- Bệnh da
    (7, 'arthritis');        -- Viêm khớp
END
GO

-- Danh sách 63 thành phố Việt Nam (lấy từ city.csv)
IF NOT EXISTS (SELECT 1 FROM city WHERE city_id = 1559969)
BEGIN
    INSERT INTO city (city_id, city_name, longitude, latitude) VALUES
    (1559969, N'Nghệ An', 104.833328, 19.33333),
    (1559970, N'Ninh Bình', 105.833328, 20.25),
    (1559971, N'Ninh Thuận', 108.833328, 11.75),
    (1559972, N'Sóc Trăng', 105.833328, 9.66667),
    (1559975, N'Trà Vinh', 106.25, 9.83333),
    (1559976, N'Tuyên Quang', 105.25, 22.116671),
    (1559977, N'Vĩnh Long', 106.0, 10.16667),
    (1559978, N'Yên Bái', 104.666672, 21.5),
    (1562412, N'Lào Cai', 104.0, 22.33333),
    (1564676, N'Tiền Giang', 106.166672, 10.41667),
    (1565033, N'Thừa Thiên-Huế', 107.583328, 16.33333),
    (1565088, N'Kon Tum', 107.916672, 14.75),
    (1566165, N'Thanh Hóa', 105.5, 20.0),
    (1566338, N'Thái Bình', 106.333328, 20.5),
    (1566557, N'Tây Ninh', 106.166672, 11.33333),
    (1567643, N'Sơn La', 104.0, 21.16667),
    (1568733, N'Quảng Trị', 107.0, 16.75),
    (1568758, N'Quảng Ninh', 107.333328, 21.25),
    (1568769, N'Quảng Ngãi', 108.666672, 15.0),
    (1568839, N'Quảng Bình', 106.333328, 17.5),
    (1569805, N'Phú Yên', 109.166672, 13.16667),
    (1572594, N'Hòa Bình', 105.25, 20.33333),
    (1575788, N'Long An', 106.166672, 10.66667),
    (1576632, N'Lạng Sơn', 106.5, 21.75),
    (1577882, N'Lâm Đồng', 108.333328, 11.5),
    (1579008, N'Kiên Giang', 105.166672, 10.0),
    (1579634, N'Khánh Hòa', 109.0, 12.33333),
    (1580578, N'TP. Hồ Chí Minh', 106.666672, 10.83333),
    (1580700, N'Hà Tĩnh', 105.75, 18.33333),
    (1581030, N'Hà Giang', 105.0, 22.75),
    (1581088, N'Gia Lai', 108.25, 13.75),
    (1581129, N'Hà Nội', 105.883331, 21.116671),
    (1581188, N'Cần Thơ', 105.666672, 9.83333),
    (1581297, N'Hải Phòng', 106.583328, 20.83333),
    (1581882, N'Bình Thuận', 108.0, 11.08333),
    (1582562, N'Đồng Tháp', 105.666672, 10.66667),
    (1582720, N'Đồng Nai', 107.166672, 11.0),
    (1584169, N'Đắk Lắk', 108.166672, 12.83333),
    (1584534, N'Bà Rịa - Vũng Tàu', 107.25, 10.58333),
    (1586182, N'Cao Bằng', 106.0, 22.66667),
    (1587871, N'Bình Định', 109.0, 14.16667),
    (1587974, N'Bến Tre', 106.5, 10.16667),
    (1594446, N'An Giang', 105.166672, 10.5),
    (1905099, N'Điện Biên', 102.933327, 21.33333),
    (1905412, N'Bắc Ninh', 106.166672, 21.08333),
    (1905419, N'Bắc Giang', 106.333328, 21.33333),
    (1905468, N'Đà Nẵng', 108.083328, 16.08333),
    (1905475, N'Bình Dương', 106.666672, 11.16667),
    (1905480, N'Bình Phước', 106.916672, 11.75),
    (1905497, N'Thái Nguyên', 105.833328, 21.66667),
    (1905516, N'Quảng Nam', 107.916672, 15.58333),
    (1905577, N'Phú Thọ', 105.166672, 21.33333),
    (1905626, N'Nam Định', 106.25, 20.25),
    (1905637, N'Hà Nam', 106.0, 20.58333),
    (1905669, N'Bắc Kạn', 105.833328, 22.16667),
    (1905675, N'Bạc Liêu', 105.75, 9.25),
    (1905678, N'Cà Mau', 105.083328, 9.08333),
    (1905686, N'Hải Dương', 106.333328, 20.91667),
    (1905699, N'Hưng Yên', 106.083328, 20.83333),
    (1905856, N'Vĩnh Phúc', 105.599998, 21.299999);
END
GO

PRINT 'Database schema created successfully!';
GO
