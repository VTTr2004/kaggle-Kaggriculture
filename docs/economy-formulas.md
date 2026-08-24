# Economy formulas — học theo từng bước

Mục tiêu của Economy không phải tạo một con số đẹp. Mục tiêu là ước tính mỗi
lựa chọn sẽ làm **tiền cuối mùa** tăng hoặc giảm bao nhiêu. Dashboard phân biệt:

- `official`: công thức/cost/timing lấy từ interpreter Kaggle đang cài;
- `observed`: dữ liệu bot thực sự nhìn thấy ở turn hiện tại;
- `assumption`: phần tương lai không thể biết chắc và phải ghi rõ giả định.

## 1. Dự báo market inventory

Với một crop mới, tại ngày thu hoạch đầu tiên:

```text
projected inventory
  = inventory hiện tại
  - town consumption đã biết
  - kỳ vọng consumption của shop tương lai
  + hàng đang chờ bán của mình
  + hàng sẵn sàng công khai của đối thủ
```

Town center và shop hiện tại dùng đúng interval chính thức. Danh tính shop chưa
mở là ngẫu nhiên và không quan sát được, nên dùng nhu cầu trung bình của toàn bộ
bảng shop; đây là expectation, không phải sự thật chắc chắn.

## 2. Giá market chính thức

```text
price(inv) = base + sign × amplitude × f(|inv - I0|)

amplitude = target × base / f(T)
sign      = +1 nếu inv < I0   (scarcity)
          = -1 nếu inv >= I0  (glut)
```

`f` là shape chính thức của từng sản phẩm: `linear`, `sq`, `sqrt`, `log`,
`log10` hoặc `hinge`. Kết quả được round và floor ở `$1`. Module local được
regression-test trực tiếp với hàm của interpreter tại các boundary `I0-T`,
`I0`, `I0+T`, `I0+2T`.

## 3. Crop cash flow

```text
expected revenue = tổng giá của từng đơn vị bán ra
expected profit  = expected revenue - seed cost
crop score       = expected profit / occupied tile-days
```

Giá từng đơn vị được tính tuần tự vì mỗi đơn vị bán thành công làm market
inventory tăng một. Với Melon, model dùng ngày 10 là ngày sớm nhất đạt 6 đơn vị
không fertilizer theo watering bonus chính thức.

Baseline hiện chưa trừ labor cost và crop-loss risk. Dashboard ghi rõ assumptions
để không nhầm forecast với luật chính thức.

## 4. SELL hay HOLD

```text
sell-now revenue = tổng unit price nếu bán ngay

inventory after wait
  = current inventory
  - expected town consumption
  + visible opponent-ready supply

hold revenue = tổng unit price tại inventory sau khi chờ một ngày
```

Bot bắt buộc bán nếu là ngày cuối, shed gần đầy hoặc thiếu cash reserve. Nếu
không, baseline so sánh doanh thu bán ngay với giữ một ngày. Khi quote chạm `$1`,
sale không làm market inventory tăng — đúng hành vi interpreter.

## 5. HIRE

Giá official theo Fibonacci, reset mỗi ngày:

```text
1, 1, 2, 3, 5, 8, ... × farmHandCostMult
```

Economy báo cost; Farm báo workload. Shared Strategy mới được quyết định vì:

```text
net hire value = giá trị công việc hand cứu được - hire cost
```

Giá trị công việc chưa được quy đổi hoàn chỉnh thành coin; đây là phần còn phải
làm cùng Person 1.

## 6. BUY_LAND

Một quadrant có 25 ô; giá official lần lượt `$1000`, `$2000`, `$4000`.

Baseline định giá một crop cycle trên 25 ô:

```text
units           = 25 × expected units per tile
revenue         = unit-by-unit market revenue
seed cost       = 25 × seed price
profit          = revenue - seed cost
net land value  = profit - land cost
payback days    = land cost / estimated daily profit
```

Revenue đã tính price impact do chính 25 ô cùng đưa hàng ra market. Shared
Strategy vẫn phải từ chối nếu đất hiện tại chưa dùng đủ hoặc Farm không có năng
lực chăm thêm.

## 7. Những phần chưa bật

- Animal economics: animal cost, structure/setup time, Wheat feed, product
  schedule, fertilizer và labor.
- Fertilizer ROI: yield bonus so với giá mua/giá trị labor.
- Giá trị tiền mặt tái đầu tư khi quyết định HOLD.
- Dự báo sản lượng tương lai của đối thủ ngoài lượng đang sẵn sàng công khai.
- Tối ưu portfolio nhiều crop thay vì chọn duy nhất crop đứng đầu.

Không bật `BUY_ANIMAL` trước khi Farm hỗ trợ đầy đủ build, pickup, place, feed và
harvest; nếu không animal chỉ nằm trong shed và làm mất tiền.
