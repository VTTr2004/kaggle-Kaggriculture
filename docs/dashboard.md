# Phòng phân tích trận Kaggriculture

Dashboard này giúp học và debug bot bằng một trận mô phỏng local. Nó không kết
nối Kaggle và không nằm trong submission.

## Chạy

```bash
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
streamlit run dashboard/app.py
```

Trình duyệt sẽ mở `http://localhost:8501`. Lần đầu dashboard chạy đủ 720 lượt
nên cần chờ vài giây. Một trận được lưu tạm theo `seed`, bot đối thủ và
vị trí người chơi; kéo lượt không chạy lại trận.

## Cách đọc

1. `Quan sát`: hai trang trại, chợ, thị trấn và kho riêng được phép xem.
2. `Phân tích kinh tế`: mở `Bản đồ công thức`, sau đó xem lần lượt
   dự báo cây trồng, đường giá chính thức, bán/giữ, giá thuê và định giá đất.
3. `Quyết định cuối`: tín hiệu trang trại, đề xuất giao dịch, kết quả
   kiểm tra cuối và hành động thực sự đã ghi trong trận.

Trong dữ liệu trận của Kaggle, hành động sinh từ quan sát ở trạng thái `N`
được lưu trên trạng thái `N + 1`. Dashboard tự xử lý ánh xạ này; trạng thái
kết thúc không có hành động kế tiếp.

Nếu `Quyết định được tính lại` khác `Hành động đã ghi trong trận`,
trận được tạo bởi phiên bản code khác hoặc luồng hiện tại không còn cho
cùng kết quả khi chạy lại.

Chi tiết phần nào là luật chính thức và phần nào là giả định dự báo nằm trong
[`economy-formulas.md`](economy-formulas.md).
