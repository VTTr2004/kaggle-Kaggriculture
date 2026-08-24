# Economy Intelligence: bắt đầu từ đâu?

Dashboard giúp người mới đọc replay; CLI và unit test vẫn là cách nhanh nhất để
kiểm tra một công thức Economy sau khi sửa code.

## Mô hình tinh thần đơn giản

Mỗi turn Economy chỉ làm ba việc:

```text
1. Đọc: mình đang có gì và thị trường ra sao?
2. Tính: mỗi lựa chọn có thể lời/lỗ bao nhiêu?
3. Đề xuất: nên bán, thuê hoặc đầu tư gì?
```

Economy không điều khiển farmer. Shared Strategy ghép đề xuất đó với khả năng
thực tế do Farm báo cáo.

## Chạy lần đầu

```bash
source .venv/bin/activate
python tools/inspect_economy.py --turn 0 --seed 20260822
```

Đọc output từ trên xuống:

1. `ECONOMY INPUT`: tiền, shed, seeds, town và đối thủ công khai.
2. `CROP RANKING`: crop nào đang được đánh giá cao nhất và có kịp lớn không.
3. `DIRECT MARKET CANDIDATES`: các lệnh Economy có thể quyết định bằng dữ liệu
   kinh tế, hiện chủ yếu là bán hàng.
4. `INVESTMENT QUOTES`: chi phí thuê hand/mua đất; chưa chắc được chấp nhận.
5. `FARM SIGNALS`: workload và mức sử dụng đất.
6. `SHARED STRATEGY RESULT`: crop/lệnh được ghép và qua Fusion chấp nhận.

Xem các giai đoạn khác của cùng trận:

```bash
python tools/inspect_economy.py --turn 0   --seed 20260822
python tools/inspect_economy.py --turn 240 --seed 20260822
python tools/inspect_economy.py --turn 480 --seed 20260822
python tools/inspect_economy.py --turn 719 --seed 20260822
```

## Bài tập code đầu tiên

Đừng thêm ML. Làm từng thay đổi nhỏ theo thứ tự:

### 1. Hiểu snapshot

Đọc `economy/snapshot.py`, thêm hoặc sửa test trong `tests/test_economy.py`.
Mục tiêu: mọi dữ liệu Economy dùng đều hiện rõ và không đọc private đối thủ.

### 2. Hiểu crop score hiện tại

Trong `economy/analyzer.py`, lần theo:

```text
market inventory hiện tại
-> trừ lượng Town sẽ tiêu thụ
-> cộng hàng của mình đã có hoặc đang trồng
-> cộng lượng hàng đối thủ đang có sẵn (giả sử họ bán)
-> price curve chính thức dự báo giá bán
-> expected revenue
-> expected profit
-> profit per occupied day (score)
```

Không còn `Town demand bonus` 4% hay nhân `price ratio` lần hai. Forecast hiện
chỉ dùng thông tin quan sát được và ghi rõ giả định; chưa đoán sản lượng tương lai
bị ẩn của đối thủ.

### 3. Kiểm tra công thức giá

`economy/pricing.py` sao chép price curve bằng standard library. Test so sánh các
mốc `I0`, `I0 + T`, `I0 - T` trực tiếp với interpreter chính thức.

### 4. Cải thiện forecast

`economy/forecast.py` hiện tính lịch Town và cash flow cây trồng. Bước tiếp theo
là ước lượng sản lượng tương lai của đối thủ và rủi ro Farm không chăm kịp.

### 5. So sánh trên cùng seed

```bash
pytest tests/test_economy.py
python tools/inspect_economy.py --turn 240 --seed 20260822
python tools/benchmark.py --opponent starter --seeds 20260820:20260830
```

Ghi lại kết quả cũ/mới. Không kết luận từ một trận random.

## Dashboard

Chạy `streamlit run dashboard/app.py`, chọn tab `2 · Phân tích kinh tế` và mở
`Bản đồ công thức: đã làm gì và còn thiếu gì?`. Giao diện không được đóng
vào bộ code nộp bài.
