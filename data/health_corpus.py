"""
Sample corpus về các bệnh lý và khuyến nghị sức khỏe theo thời tiết.
Dữ liệu này sẽ được push vào ChromaDB để RAG sử dụng.
"""

health_corpus = {
    "cardiovascular": [
        """
        BỆNH TIM MẠCH VÀ THỜI TIẾT NÓNG:
        
        Khi nhiệt độ trên 32°C, người bệnh tim mạch cần:
        - Uống đủ nước (2-3 lít/ngày), tránh mất nước
        - Hạn chế hoạt động ngoài trời từ 10h-16h
        - Mang theo thuốc tim mạch (nitrate, aspirin) khi ra ngoài
        - Theo dõi huyết áp 2 lần/ngày
        - Nếu thấy đau ngực, khó thở, chóng mặt → Gọi cấp cứu ngay
        
        Triệu chứng cảnh báo:
        - Đau tức ngực, lan ra vai trái
        - Tim đập nhanh bất thường
        - Khó thở khi gắng sức nhẹ
        - Chân tay sưng phù
        """,
        
        """
        BỆNH TIM MẠCH VÀ THỜI TIẾT LẠNH:
        
        Khi nhiệt độ dưới 15°C, nguy cơ đột quỵ tăng 30%:
        - Mặc ấm, đặc biệt giữ ấm ngực và đầu
        - Không ra ngoài đột ngột khi trời quá lạnh
        - Tránh tắm nước nóng quá lâu (gây giãn mạch đột ngột)
        - Ăn nhiều rau xanh, hạn chế muối
        - Kiểm tra huyết áp thường xuyên (sáng và tối)
        
        Lưu ý khi vận động:
        - Khởi động kỹ 10-15 phút
        - Tránh gắng sức đột ngột
        - Dừng ngay nếu thấy khó chịu
        """,
        
        """
        BỆNH TIM MẠCH VÀ HOẠT ĐỘNG THỂ THAO:
        
        Môn thể thao phù hợp:
        - Đi bộ nhẹ nhàng (30 phút/ngày)
        - Bơi lội (nước ấm, tránh sốc nhiệt)
        - Yoga, thiền (giảm stress)
        
        Các môn NÊN TRÁNH:
        - Đá bóng (gắng sức cao, va chạm)
        - Chạy marathon
        - Cử tạ nặng
        - Thể thao đối kháng
        
        Trước khi tham gia thể thao:
        - Tham khảo bác sĩ tim mạch
        - Kiểm tra sức khỏe định kỳ
        - Đo huyết áp trước và sau vận động
        - Mang theo thuốc cấp cứu
        """,
        
        """
        BỆNH TIM MẠCH VÀ CHẤT LƯỢNG KHÔNG KHÍ:
        
        Khi AQI > 100 (không khí kém):
        - Hạn chế ra ngoài, đặc biệt buổi sáng sớm
        - Đeo khẩu trang N95 khi bắt buộc phải ra ngoài
        - Đóng cửa sổ, dùng máy lọc không khí trong nhà
        - Uống nhiều nước, ăn nhiều trái cây có vitamin C
        
        Khi PM2.5 > 50:
        - Tuyệt đối không tập thể thao ngoài trời
        - Tránh đi xe máy trong giờ cao điểm
        - Theo dõi nhịp tim, huyết áp
        - Nếu ho, khó thở → Gọi bác sĩ ngay
        """
    ],
    
    "respiratory": [
        """
        BỆNH HÔ HẤP VÀ THỜI TIẾT THAY ĐỔI:
        
        Khi thời tiết thay đổi đột ngột (chênh lệch >5°C):
        - Đeo khẩu trang khi ra ngoài
        - Mang theo thuốc xịt (nếu có hen suyễn)
        - Giữ ấm cổ họng
        - Uống nước ấm thường xuyên
        
        Triệu chứng cần chú ý:
        - Ho kéo dài >3 ngày
        - Khó thở, thở khò khè
        - Sốt cao >38.5°C
        - Đau ngực khi hít thở sâu
        """,
        
        """
        BỆNH HÔ HẤP VÀ Ô NHIỄM KHÔNG KHÍ:
        
        Khi AQI > 150 (không khí rất kém):
        - KHÔNG ra ngoài nếu không cần thiết
        - Đeo khẩu trang N95 hoặc KN95
        - Dùng máy lọc không khí trong nhà
        - Uống nhiều nước, súc họng với nước muối ấm
        
        Khi PM2.5 > 100:
        - Hạn chế nói chuyện nhiều (giảm hít thở sâu)
        - Tránh vận động gắng sức
        - Theo dõi triệu chứng ho, khó thở
        - Sẵn sàng đi khám nếu triệu chứng nặng lên
        """
    ],
    
    "diabetes": [
        """
        BỆNH TIỂU ĐƯỜNG VÀ THỜI TIẾT NÓNG:
        
        Nhiệt độ cao ảnh hưởng đường huyết:
        - Đo đường huyết thường xuyên hơn (4-6 lần/ngày)
        - Uống đủ nước (tránh nước ngọt)
        - Mang theo kẹo glucose để xử lý hạ đường huyết
        - Bảo quản insulin đúng nhiệt độ (2-8°C)
        
        Dấu hiệu nguy hiểm:
        - Chóng mặt, đổ mồ hôi nhiều
        - Lú lẫn, mất phương hướng
        - Tim đập nhanh
        → Ăn ngay đường/kẹo, gọi cấp cứu
        """,
        
        """
        BỆNH TIỂU ĐƯỜNG VÀ VẬN ĐỘNG:
        
        Vận động phù hợp:
        - Đi bộ sau bữa ăn 30 phút
        - Bơi lội (kiểm tra đường huyết trước và sau)
        - Yoga, thể dục nhịp điệu
        
        LƯU Ý QUAN TRỌNG:
        - Đo đường huyết trước khi vận động
        - Nếu <100 mg/dL: ăn snack trước
        - Nếu >250 mg/dL: hoãn vận động, đo ketone
        - Mang theo nước và kẹo glucose
        - Không vận động một mình
        """
    ]
}
