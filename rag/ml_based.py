"""
ML-Based Health Risk Prediction Module

Sử dụng XGBoost model đã train để predict health risk level từ weather data.
Model được train với 184,464 records, 23 features, và 5 WHO risk levels.

Author: AI Assistant
Date: 2024
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Tuple, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to trained model
MODEL_PATH = Path(__file__).parent.parent / "models" / "xgboost_health_classifier.pkl"


class MLHealthPredictor:
    """
    Wrapper class cho XGBoost health risk prediction model
    """
    
    def __init__(self):
        """Load trained model và metadata"""
        self.model = None
        self.label_encoder = None
        self.feature_columns = None
        self.health_thresholds = None
        self._load_model()
    
    def _load_model(self):
        """Load model từ pickle file"""
        try:
            if not MODEL_PATH.exists():
                raise FileNotFoundError(f"Model file not found at {MODEL_PATH}")
            
            with open(MODEL_PATH, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.label_encoder = model_data['label_encoder']
            self.feature_columns = model_data['feature_columns']
            self.health_thresholds = model_data['health_thresholds']
            
            logger.info(f"✅ ML model loaded successfully from {MODEL_PATH}")
            logger.info(f"   Features: {len(self.feature_columns)}")
            logger.info(f"   Risk levels: {list(self.label_encoder.classes_)}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load ML model: {e}")
            raise
    
    def prepare_features(self, weather_data: dict) -> np.ndarray:
        """
        Chuẩn bị features từ weather data realtime
        
        Args:
            weather_data: Dictionary chứa weather parameters từ API
            
        Returns:
            numpy array với 23 features theo đúng thứ tự model expect
        """
        # Extract raw features từ weather_data
        temp = weather_data.get('temp', 25)
        humidity = weather_data.get('humidity', 60)
        precipitation = weather_data.get('precipitation', 0) or 0
        wind_speed = weather_data.get('wind_speed', 0)
        uv_index = weather_data.get('uv_index', 5) or 0
        
        # Air Quality features (có thể None nếu không có data)
        pm2_5 = weather_data.get('pm2_5', 0) or 0
        pm10 = weather_data.get('pm10', 0) or 0
        aqi = weather_data.get('aqi', 1) or 1
        co = weather_data.get('co', 0) or 0
        no2 = weather_data.get('no2', 0) or 0
        o3 = weather_data.get('o3', 0) or 0
        so2 = weather_data.get('so2', 0) or 0
        nh3 = weather_data.get('nh3', 0) or 0
        
        # Derived features: temp_min, temp_max
        # Nếu không có, estimate từ temp (±3°C)
        temp_min = weather_data.get('temp_min', temp - 3)
        temp_max = weather_data.get('temp_max', temp + 3)
        temp_range = temp_max - temp_min
        
        # Derived boolean features
        is_hot = 1 if temp > 32 else 0
        is_cold = 1 if temp < 18 else 0
        is_humid = 1 if humidity > 70 else 0
        is_dry = 1 if humidity < 40 else 0
        uv_high = 1 if uv_index > 6 else 0
        has_rain = 1 if precipitation > 5 else 0
        pm25_high = 1 if pm2_5 > 25 else 0
        aqi_poor = 1 if aqi >= 4 else 0
        
        # Tạo feature array theo đúng thứ tự
        # ['temperature', 'temp_min', 'temp_max', 'temp_range',
        #  'humidity', 'precipitation', 'wind_speed',
        #  'uv_index',
        #  'pm2_5', 'pm10', 'aqi', 'co', 'no2', 'o3', 'so2', 'nh3',
        #  'is_hot', 'is_cold', 'is_humid', 'is_dry', 'uv_high', 'has_rain',
        #  'pm25_high', 'aqi_poor']
        
        features = np.array([
            temp, temp_min, temp_max, temp_range,
            humidity, precipitation, wind_speed,
            uv_index,
            pm2_5, pm10, aqi, co, no2, o3, so2, nh3,
            is_hot, is_cold, is_humid, is_dry, uv_high, has_rain,
            pm25_high, aqi_poor
        ]).reshape(1, -1)
        
        return features
    
    def predict(self, weather_data: dict) -> Dict[str, any]:
        """
        Predict health risk level từ weather data
        
        Args:
            weather_data: Dictionary chứa weather parameters
            
        Returns:
            Dictionary với risk_level, confidence, và explanation
        """
        try:
            # Prepare features
            features = self.prepare_features(weather_data)
            
            # Predict
            pred_encoded = self.model.predict(features)[0]
            risk_level = self.label_encoder.inverse_transform([pred_encoded])[0]
            
            # Get probability/confidence
            pred_proba = self.model.predict_proba(features)[0]
            confidence = float(pred_proba[pred_encoded])
            
            # Get feature importance (top 5 factors)
            feature_importance = self.model.feature_importances_
            top_factors = self._get_top_factors(features[0], feature_importance)
            
            # Generate explanation
            explanation = self._generate_explanation(
                risk_level, 
                weather_data, 
                top_factors
            )
            
            result = {
                "risk_level": risk_level,
                "confidence": round(confidence * 100, 1),
                "explanation": explanation,
                "top_factors": top_factors,
                "model_version": "xgboost_v1_WHO5levels"
            }
            
            logger.info(f"✅ Prediction: {risk_level} (confidence: {result['confidence']}%)")
            return result
            
        except Exception as e:
            logger.error(f"❌ Prediction failed: {e}")
            # Fallback to safe default
            return {
                "risk_level": "moderate",
                "confidence": 0,
                "explanation": "Không thể tính toán risk level, sử dụng giá trị mặc định.",
                "top_factors": [],
                "model_version": "fallback"
            }
    
    def _get_top_factors(self, features: np.ndarray, importance: np.ndarray, top_n: int = 5) -> List[Dict]:
        """
        Lấy top N factors ảnh hưởng nhất đến prediction
        
        Returns:
            List of dicts with feature name, value, and importance
        """
        # Get indices of top N important features
        top_indices = np.argsort(importance)[-top_n:][::-1]
        
        top_factors = []
        for idx in top_indices:
            feature_name = self.feature_columns[idx]
            feature_value = features[idx]
            feature_importance = importance[idx]
            
            # Format value based on feature type
            if feature_name in ['is_hot', 'is_cold', 'is_humid', 'is_dry', 'uv_high', 'has_rain', 'pm25_high', 'aqi_poor']:
                value_str = "Có" if feature_value == 1 else "Không"
            elif feature_name in ['temperature', 'temp_min', 'temp_max', 'temp_range']:
                value_str = f"{feature_value:.1f}°C"
            elif feature_name == 'humidity':
                value_str = f"{feature_value:.0f}%"
            elif feature_name == 'uv_index':
                value_str = f"{feature_value:.1f}"
            elif feature_name in ['pm2_5', 'pm10']:
                value_str = f"{feature_value:.1f} µg/m³"
            elif feature_name == 'aqi':
                value_str = f"{int(feature_value)} (1-5 scale)"
            else:
                value_str = f"{feature_value:.2f}"
            
            top_factors.append({
                "feature": feature_name,
                "value": value_str,
                "importance": round(feature_importance * 100, 1)
            })
        
        return top_factors
    
    def _generate_explanation(self, risk_level: str, weather_data: dict, top_factors: List[Dict]) -> str:
        """
        Generate human-readable explanation cho prediction
        """
        explanations = {
            "safe": "Điều kiện thời tiết hiện tại an toàn cho sức khỏe. Bạn có thể thoải mái hoạt động ngoài trời.",
            "low": "Điều kiện thời tiết có nguy cơ thấp cho sức khỏe. Cần thận trọng nếu bạn thuộc nhóm nhạy cảm.",
            "moderate": "Điều kiện thời tiết có nguy cơ trung bình. Hạn chế hoạt động ngoài trời kéo dài, đặc biệt nếu bạn có bệnh lý.",
            "high": "Điều kiện thời tiết có nguy cơ cao cho sức khỏe. Nên ở trong nhà, hạn chế ra ngoài không cần thiết.",
            "extreme": "Điều kiện thời tiết CỰC KỲ NGUY HIỂM! Tuyệt đối tránh ra ngoài. Nguy cơ cao về sức khỏe."
        }
        
        base_explanation = explanations.get(risk_level, "Không xác định được mức độ rủi ro.")
        
        # Thêm chi tiết về top factors
        if top_factors:
            factor_details = []
            for factor in top_factors[:3]:  # Top 3 factors
                feature = factor['feature']
                value = factor['value']
                
                # Human-readable feature names
                feature_names = {
                    'pm2_5': 'PM2.5',
                    'temperature': 'Nhiệt độ',
                    'uv_index': 'Chỉ số UV',
                    'humidity': 'Độ ẩm',
                    'aqi': 'Chỉ số chất lượng không khí',
                    'pm25_high': 'PM2.5 cao',
                    'is_hot': 'Thời tiết nóng',
                    'is_humid': 'Độ ẩm cao'
                }
                
                readable_name = feature_names.get(feature, feature)
                factor_details.append(f"{readable_name}: {value}")
            
            base_explanation += f"\n\nCác yếu tố ảnh hưởng chính: {', '.join(factor_details)}."
        
        return base_explanation


# Global predictor instance
_predictor = None

def get_predictor() -> MLHealthPredictor:
    """
    Get singleton instance của ML predictor
    """
    global _predictor
    if _predictor is None:
        _predictor = MLHealthPredictor()
    return _predictor


def predict_health_risk(weather_data: dict) -> Dict[str, any]:
    """
    Main function để predict health risk từ weather data
    
    Args:
        weather_data: Dictionary chứa các weather parameters
        
    Returns:
        Dictionary với prediction results
        
    Example:
        >>> weather = {
        ...     'temp': 35,
        ...     'humidity': 75,
        ...     'uv_index': 10,
        ...     'pm2_5': 45
        ... }
        >>> result = predict_health_risk(weather)
        >>> print(result['risk_level'])
        'high'
    """
    predictor = get_predictor()
    return predictor.predict(weather_data)


# Test function
if __name__ == "__main__":
    # Test với sample data
    test_cases = [
        {
            "name": "Safe conditions",
            "data": {
                "temp": 25,
                "humidity": 60,
                "uv_index": 4,
                "pm2_5": 10,
                "aqi": 1
            }
        },
        {
            "name": "High PM2.5",
            "data": {
                "temp": 30,
                "humidity": 65,
                "uv_index": 6,
                "pm2_5": 60,
                "aqi": 4
            }
        },
        {
            "name": "Extreme heat + UV",
            "data": {
                "temp": 38,
                "humidity": 80,
                "uv_index": 12,
                "pm2_5": 35,
                "aqi": 3
            }
        }
    ]
    
    print("🧪 Testing ML Health Predictor...\n")
    for test in test_cases:
        print(f"📊 Test: {test['name']}")
        result = predict_health_risk(test['data'])
        print(f"   Risk Level: {result['risk_level']}")
        print(f"   Confidence: {result['confidence']}%")
        print(f"   Explanation: {result['explanation']}")
        top_3 = [f"{x['feature']}: {x['value']}" for x in result['top_factors'][:3]]
        print(f"   Top Factors: {top_3}")
        print()
