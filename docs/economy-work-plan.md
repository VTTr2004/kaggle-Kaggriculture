# Kế hoạch phát triển Economy Intelligence

Tài liệu này mô tả toàn bộ phần việc của nhánh Economy/Business trong
Kaggriculture: cần tính gì, nhận dữ liệu gì từ Farm, xuất kết quả gì cho Shared
Strategy, và cụm nào nên dùng rule-based, tối ưu hóa, ML hay RL.

Mục tiêu cuối cùng của Economy không phải chỉ dự báo giá. Mục tiêu là quy đổi
mọi lựa chọn thành mức thay đổi tiền cuối mùa:

```text
giá trị kế hoạch
  = tiền cuối mùa nếu thực hiện kế hoạch
  - tiền cuối mùa nếu không thực hiện kế hoạch
```

Hàng chưa bán, hạt giống còn dư, cây chưa thu hoạch, animal chưa hoàn vốn và đất
không kịp khai thác đều không trực tiếp cộng vào reward. Vì vậy mọi quote phải
kết thúc ở tiền có thể nhận trước lượt cuối.

## 1. Ranh giới trách nhiệm

### Economy sở hữu

- Snapshot tiền, market, town, shed, seed và tín hiệu công khai của đối thủ.
- Công thức giá chính thức và báo giá giao dịch nhiều đơn vị.
- Forecast cung, cầu, market inventory và giá tương lai.
- Crop, animal, feed, fertilizer và product unit economics.
- Sell/hold/liquidation, cash reserve và shed pressure.
- Báo giá seed, hire, land, animal, product và fertilizer.
- Rủi ro thị trường và dự đoán hành vi đối thủ.
- Danh sách cơ hội kinh tế kèm doanh thu, chi phí, lợi nhuận và độ tin cậy.

### Economy không sở hữu

- Tọa độ, đường đi và phân công unit.
- Các lệnh `WATER`, `HARVEST`, `FEED`, `CARE`, `BUILD_*`, `PICKUP`, `DROP`,
  `PLACE` hoặc `DIG`.
- Khẳng định một kế hoạch có đủ lao động hoặc đủ lượt thực hiện.
- Tự ý mua seed, hire, land hoặc animal khi chưa được Shared Strategy chấp nhận.

### Shared Strategy sở hữu

- Ghép giá trị Economy với khả năng thực hiện do Farm báo cáo.
- Chọn portfolio sản xuất, số lượng seed, số hand, đất và animal.
- Yêu cầu Economy tính lại giá sau khi Farm trả lịch sản lượng khả thi.

## 2. Chọn công nghệ

| Nhãn | Dùng khi nào | Ví dụ |
|---|---|---|
| Exact rule | Interpreter đã cho luật chính xác | Giá market, town interval, seed cost |
| Rule + optimization | Luật đã biết nhưng phải tìm phương án tốt | Portfolio, sell horizon, cash allocation |
| Probabilistic rule | RNG có phân phối đã biết | Shop tương lai, weed expectation |
| ML | Dữ liệu quan trọng bị ẩn hoặc hành vi đối thủ không có công thức | Xác suất đối thủ bán |
| RL | Quyết định dài hạn còn khó sau khi simulator và baseline đã mạnh | Chọn macro-strategy trong self-play |

Nguyên tắc bắt buộc:

1. Không dùng ML/RL để học lại công thức mà interpreter đã công khai.
2. ML chỉ bổ sung phần không chắc chắn vào forecast rule-based.
3. RL chỉ được chọn macro-action đã qua action mask; không điều khiển trực tiếp
   unit operation.
4. Mọi model dùng lúc chạy submission phải deterministic, stateless và có thể
   thực thi bằng Python standard library.

## 3. Pipeline tổng thể

```text
GameState
   |
   v
Economy Snapshot
   |
   +--> Exact Market Pricing
   +--> Town Demand Forecast
   +--> Own Supply Forecast
   +--> Opponent Supply Forecast
   |
   v
Future Market Inventory and Price
   |
   +--> Crop Economics
   +--> Sell/Hold
   +--> Cash and Shed
   +--> Hire/Land Quotes
   +--> Animal/Feed/Fertilizer Economics
   |
   v
Economic Opportunity Candidates
   |
   v
Farm feasibility and production schedule
   |
   v
Economy reprices the feasible schedule
   |
   v
Shared Strategy chooses the final plan
```

Economy và Farm phải có vòng lặp. Một forecast chỉ tính một lần có thể sai vì
Farm thay đổi ngày bán hoặc số lượng thực tế; ngày bán và số lượng lại làm thay
đổi market inventory và giá.

## 4. Cụm 1 — Economy Snapshot

**Phương pháp:** Exact rule.

**Mức ưu tiên:** P0, làm trước mọi forecast.

### Mục tiêu

Tạo một bản chụp kinh tế chỉ từ dữ liệu được phép quan sát. Mọi module phía sau
phải đọc snapshot thay vì tự đọc observation theo nhiều cách khác nhau.

### Input

- `GameState` đã được chuẩn hóa.
- Farm công khai của mình và đối thủ.
- Private state của chính mình.
- Market và town dùng chung.

### Cần tính

- `step`, `day`, `hour`, `remaining_turns`, `remaining_days`.
- Tiền mình, tiền đối thủ và cash reserve hiện tại.
- Market inventory, current prices và market parameters của mọi sản phẩm.
- Shed, seed và từng unit inventory của mình.
- Shed usage và free capacity.
- Shop instances đã mở.
- Số hand, hires trong ngày và land đã mở của hai bên.
- Số cây theo loại, tuổi cây, yield công khai và animal công khai của đối thủ.
- Own committed supply: shed, carried items, ready yield và cây đang sản xuất.

### Output

Một `EconomySnapshot` immutable, không chứa private state của đối thủ.

### Việc cần làm

- Bổ sung `remaining_turns`, không chỉ `remaining_days`.
- Tách own supply thành `shed`, `carried`, `ready`, `future committed`; không
  gộp tất cả thành một số làm mất nguồn gốc.
- Tách opponent supply thành `ready visible` và `predictable future production`.
- Giữ raw market params để hỗ trợ configuration override.

### Tiêu chí hoàn thành

- Dashboard giải thích được nguồn gốc mọi trường snapshot.
- Test chứng minh không đọc private shed, seed hoặc inventory của đối thủ.
- Snapshot đúng tại đầu ngày, cuối ngày và lượt cuối trận.

## 5. Cụm 2 — Exact Market Pricing

**Phương pháp:** Exact rule, tuyệt đối không dùng ML/RL.

**Mức ưu tiên:** P0.

### Mục tiêu

Tính đúng giá một đơn vị và tổng tiền của một order nhiều đơn vị tại bất kỳ mức
market inventory nào.

### Cần hỗ trợ

```text
price(item, inventory)
quote_sell(item, quantity, inventory)
quote_buy_product(item, quantity, inventory)
```

### Công thức

```text
price
  = max(1, round(base + sign * amplitude * shape(distance)))

distance  = abs(inventory - equilibrium)
amplitude = target * base / shape(throughput)
sign      = +1 khi khan hiếm, -1 khi dư cung
```

### Cách đọc độ nhạy giá

Ba tham số phải được đọc cùng nhau:

```text
shape  = giá đi nhanh/chậm theo distance như thế nào
target = tại đúng distance = T, giá lệch bao nhiêu phần trăm so với base
T      = cần thiếu/dư bao nhiêu đơn vị để đạt target
```

`T` càng nhỏ thì chỉ cần ít hàng vào/ra market là giá đã biến động mạnh. Các
shape có ý nghĩa trực quan:

| Shape | Khi lệch ít | Khi lệch rất xa | Cách hiểu |
|---|---|---|---|
| `linear` | Vừa phải | Tăng đều | Độ nhạy không đổi |
| `sqrt` | Phản ứng nhanh | Chậm dần | Nhạy sớm, sau đó bão hòa dần |
| `log`/`log10` | Phản ứng sớm | Rất chậm dần | Nhạy gần cân bằng, ít tăng tốc về sau |
| `sq` | Phản ứng chậm | Cực nhanh | Ít lệch chưa sao, lệch lớn dễ crash/bùng nổ |
| `hinge` | Gần linear trước `T` | Cực nhanh sau `T` | Có điểm gãy; vượt `T` tạo scarcity spike |

Với `hinge` chính thức:

```text
normalized = distance / T
shape       = normalized + 8 * max(0, normalized - 1)^2
```

Do đó `0.5T` cho khoảng `0.5 × target`, `T` cho đúng `target`, nhưng `2T`
cho `10 × target`. Đây là lý do Carrot/Tomato/Egg có thể tăng giá rất mạnh khi
khan hiếm vượt xa `T`.

### Đặc tính từng market item

Bảng dưới dùng default params của interpreter hiện tại. `giá thiếu T` là giá
tại `I0-T`; `giá dư T` là giá tại `I0+T`. Configuration override, nếu có, phải
được ưu tiên thay cho các default này.

| Item | Thiếu hàng | Dư hàng | Base / `T` | Giá tại `I0-T / I0 / I0+T` | Cách hiểu nhanh |
|---|---|---|---:|---:|---|
| Wheat | `sqrt`, +80% | `log`, -20% | $25 / 400 | $45 / $25 / $20 | Thiếu: giá bán tăng khá nhanh, nhận nhiều tiền hơn; dư: giá chỉ giảm nhẹ, ít mất giá |
| Carrot | `hinge`, +100% | `sqrt`, -70% | $35 / 450 | $70 / $35 / $10 | Thiếu vừa: tiền tăng từ từ; thiếu quá `T`: tiền tăng vọt; dư: giá tụt nhanh, dễ bán lỗ |
| Tomato | `hinge`, +40% | `sqrt`, -60% | $60 / 200 | $84 / $60 / $24 | Thiếu vừa: tiền tăng ít; thiếu quá `T`: tăng mạnh; dư: giá tụt nhanh và tiền bán giảm nhiều |
| Strawberry | `sqrt`, +70% | `linear`, -160% | $120 / 100 | $204 / $120 / $1 | Thiếu: giá tăng nhanh, dễ thu thêm tiền; dư: giá tụt rất nhanh về $1, nguy cơ lỗ lớn |
| Melon | `log`, +20% | `sq`, -360% | $250 / 300 | $300 / $250 / $1 | Thiếu: giá chỉ tăng ít; dư ít: giá giảm chậm; dư nhiều: giá sập ngày càng nhanh về $1 |
| Egg | `hinge`, +40% | `log`, -20% | $50 / 332 | $70 / $50 / $40 | Thiếu vừa: tiền tăng ít; thiếu quá `T`: giá tăng vọt; dư: giá giảm nhẹ, tương đối an toàn |
| Milk | `sqrt`, +60% | `linear`, -160% | $160 / 122 | $256 / $160 / $1 | Thiếu: giá tăng nhanh; dư: giá tụt rất nhanh về $1, tiền bán có thể mất gần hết |
| Wool | `log`, +20% | `sq`, -320% | $200 / 105 | $240 / $200 / $1 | Thiếu: giá chỉ tăng ít; dư: chỉ cần dư không nhiều cũng có thể sập giá rất nhanh |
| Fertilizer | `linear`, +40% | `linear`, -40% | $100 / 200 | $140 / $100 / $60 | Thiếu bao nhiêu thì giá tăng đều; dư bao nhiêu thì giá giảm đều, dễ ước tính |

Nhóm đọc nhanh:

- Tương đối chịu dư cung: Wheat, Egg; Fertilizer có curve cân bằng nhưng không
  có Town demand tự động.
- Có scarcity jackpot sau `T`: Carrot, Tomato, Egg.
- Upside tốt nhưng glut risk cao: Strawberry, Milk.
- Upside nhỏ và glut risk cực cao: Melon, Wool.

Các mô tả `tăng nhanh`, `giảm nhanh` chỉ nói về **giá market**, không trực tiếp
là lời/lỗ. Profit còn phải trừ seed/animal/feed/fertilizer cost, tính yield,
Town demand, own/opponent supply, labor feasibility và terminal unsold risk.

### Việc cần làm

- Giữ parity với `linear`, `sq`, `sqrt`, `log`, `log10` và `hinge`.
- SELL phải quote tuần tự từng đơn vị và tăng inventory sau mỗi sale thành công.
- Sale ở giá `$1` không tăng market inventory.
- BUY_PRODUCT quote tại post-buy inventory và giảm inventory sau từng đơn vị.
- Phân biệt seed/animal fixed price với product dynamic price.
- Expose breakdown đủ để dashboard hiển thị từng bước.

### Output

- Giá từng đơn vị.
- Tổng revenue/cost.
- Giá trung bình.
- Inventory trước và sau order.
- Trạng thái scarcity/glut và toàn bộ price-curve terms.

### Tiêu chí hoàn thành

- Regression test trực tiếp với interpreter tại `I0-T`, `I0`, `I0+T`,
  `I0+2T` và các mức floor.
- Multi-unit quote khớp interpreter.

## 6. Cụm 3 — Town Demand Forecast

**Phương pháp:** Exact rule cho shop đã mở; probabilistic rule cho shop tương
lai. Không cần ML/RL.

**Mức ưu tiên:** P0.

### Mục tiêu

Tính lượng sản phẩm bị Town lấy khỏi market trong một horizon theo lượt, không
ước lượng bằng một daily rate khi có thể đếm event chính xác.

### Input

- Item.
- Start step và end step hoặc `days_ahead`.
- Town center interval, shop sell interval và shop unlock interval.
- Danh sách shop instance đã mở.

### Cần tính

- Số town-center tick trong horizon.
- Số shop tick trong horizon.
- Demand của từng shop instance; shop trùng tên phải tính nhiều lần.
- Single-product shop mua hai đơn vị mỗi tick.
- Lịch unlock shop mới và số tick shop đó có thể hoạt động sau khi mở.
- Phân phối xác suất loại shop ở lần unlock tiếp theo. Theo interpreter hiện
  tại, shop được rút đều với replacement nên mỗi loại có xác suất `1/8`; shop
  đã mở và shop duplicate không làm thay đổi phân phối lần sau.
- Expected demand của shop ngẫu nhiên tương lai.
- Scenario thấp/trung bình/cao cho future-shop demand.

### Output

```text
known_center_consumption
known_shop_consumption
next_shop_probabilities
future_shop_unlocks
expected_future_shop_consumption
total_expected_consumption
consumption_events_by_step
```

### Tiêu chí hoàn thành

- Đúng ở horizon bắt đầu giữa ngày.
- Đúng khi unlock xảy ra tại day boundary.
- Đúng với shop duplicate và cap tám instance.
- Xác suất shop tiếp theo có tổng bằng 1 trước cap và rỗng sau khi đủ tám
  instance.
- Town Center không tiêu thụ Fertilizer.

## 7. Cụm 4 — Own Supply Forecast

**Phương pháp:** Exact rule cộng với lịch khả thi do Farm cung cấp.

**Mức ưu tiên:** P0.

### Mục tiêu

Biết bao nhiêu hàng của mình thật sự đi vào market trước một future step. Không
được coi mọi hàng tiềm năng là đã bán.

### Phân loại supply

- Hàng đang trong shed: sellable ngay.
- Hàng unit đang cầm: cần vào shed trước khi sell.
- Yield đang ready trên tile: cần harvest và logistics.
- Future yield từ cây/animal hiện tại.
- Future yield từ kế hoạch mới đang được định giá.

### Input từ Farm

```text
(item, earliest_shed_step, earliest_sell_step, feasible_quantity, confidence)
```

### Cần tính

- Supply batch theo thời điểm, không chỉ tổng quantity.
- Phần dự kiến bán và phần dự kiến giữ.
- Shed overflow có thể làm mất sản lượng.
- Không double-count hàng trong cây, unit inventory và shed.
- Hàng kế hoạch mới phải được tách khỏi `inventory_before_own_sale` để revenue
  có thể quote tuần tự chính xác.

### Output

Một lịch batch:

```text
item, source, available_step, sell_step, quantity, confidence
```

## 8. Cụm 5 — Opponent Supply Forecast

**Phương pháp:** Rule-based trước, ML sau. RL không cần.

**Mức ưu tiên:** P1 sau khi future-price baseline hoạt động.

### Rule-based MVP

- Đếm ready yield công khai trên crop và animal của đối thủ.
- Tính tuổi cây và các production event nhìn thấy trong horizon.
- Tạo ba scenario:
  - thấp: đối thủ không bán thêm;
  - trung bình: bán ready supply một lần;
  - cao: bán ready supply cộng predictable future production.
- Không coi private shed hoặc carried inventory là fact.

### ML nâng cấp

ML chỉ dự đoán phần hành vi không có công thức:

- `P(sell item within 1/3/5 days)`.
- Expected quantity bán trong horizon.
- Expected time-to-sale.
- Xác suất mua Wheat/Fertilizer.
- Xác suất chuyển production target.

Feature chỉ dùng dữ liệu quan sát được:

- Day/hour và remaining time.
- Opponent money, hand, land và utilization.
- Crop counts, ages, ready yields và animal states công khai.
- Market inventory, prices, curve slope và town demand.
- Lịch thay đổi market inventory nếu agent có state history hợp lệ; runtime hiện
  yêu cầu stateless giữa các call nên không được phụ thuộc mutable global state.

Model ưu tiên:

1. Logistic/linear model làm baseline.
2. Small gradient-boosted trees nếu baseline chưa đủ.
3. Export coefficients/trees thành Python constants và evaluator standard
   library cho submission.

### Label

- Đối thủ có bán item trong horizon hay không.
- Số lượng market inventory tăng do đối thủ sau khi loại own sale và town demand.
- Step đối thủ bán lần tiếp theo.

### Tiêu chí hoàn thành

- Split dataset theo seed, không chia ngẫu nhiên các row cùng replay.
- So sánh MAE/calibration với heuristic `sell all visible once`.
- Chỉ bật ML nếu cải thiện final-money benchmark ngoài tập train.

## 9. Cụm 6 — Future Market and Price Engine

**Phương pháp:** Exact/probabilistic rule; dùng ML output như một input tùy chọn.

**Mức ưu tiên:** P0, đây là calculator trung tâm.

### API đề xuất

```python
forecast_item(state, item, days_ahead, scenario="expected")
```

Nội bộ nên hỗ trợ `end_step` để forecast chính xác theo giờ.

### Công thức

```text
future inventory
  = current inventory
  - town consumption
  + own sales before horizon
  + opponent sales before horizon
  - own product purchases
  - opponent product purchases
```

### Scenario

- Conservative: town demand thấp, opponent supply cao.
- Expected: expected shop demand, expected opponent supply.
- Optimistic: town demand cao, opponent supply thấp.

### Output

```text
item
start_step, end_step
current_inventory
town_consumption_breakdown
own_supply_breakdown
opponent_supply_breakdown
purchase_assumptions
projected_inventory_low/base/high
future_price_low/base/high
confidence
assumptions
```

### Tránh lỗi

- Không cộng production vào market trước khi nó được bán.
- Không cộng planned crop supply hai lần.
- Market xử lý trước Town trong cùng step; price bán ở step đó không được dùng
  town consumption của chính step sau khi sale.
- Forecast theo day phải giữ current hour.

### Tiêu chí hoàn thành

- Dashboard nhập item và `days_ahead` rồi giải thích được toàn bộ phép tính.
- Turn 0, giữa ngày, cuối ngày và cuối mùa đều có regression tests.

## 10. Cụm 7 — Crop Economics

**Phương pháp:** Exact rule cộng với optimization. ML chỉ có thể cung cấp risk
adjustment; RL không cần.

**Mức ưu tiên:** P0.

### API đề xuất

```python
quote_crop(state, crop, planned_tiles, farm_schedule, fertilizer_plan=None)
```

### Cần tính

- Batch sản lượng và feasible sell step do Farm cung cấp.
- Future market inventory tại từng sell batch.
- Giá từng unit tuần tự.
- Revenue, seed cost và fertilizer opportunity cost.
- Gross profit, profit per tile và profit per occupied tile-day.
- Latest safe plant/sell step.
- Scenario profit low/base/high.
- Marginal profit của ô tiếp theo.

### Công thức chính

```text
gross crop profit
  = sequential sale revenue
  - seed cost
  - fertilizer economic cost

marginal value of next tile
  = portfolio profit after adding tile
  - portfolio profit before adding tile
```

### Output

- Một `CropOpportunity` cho mỗi crop và mỗi candidate quantity.
- Breakdown đủ để phân biệt raw financial profit với feasibility score.
- `score = -inf` khi Farm xác nhận không thể bán trước cuối mùa.

### Tiêu chí hoàn thành

- Nhiều tile phải tính own price impact; không dùng `one_tile_profit * tiles`.
- Ongoing crop quote từng batch riêng.
- Có test cho horizon không đủ, vừa đủ và dư thời gian.

## 11. Cụm 8 — Crop Portfolio Optimization

**Phương pháp:** Rule + optimization. ML/RL là nâng cấp tùy chọn về sau.

**Mức ưu tiên:** P1.

### Mục tiêu

Chọn số ô mỗi crop thay vì trồng toàn bộ crop đứng đầu.

### MVP

Marginal greedy:

1. Farm báo số slot sản xuất khả thi.
2. Tính marginal value của một tile tiếp theo cho từng crop.
3. Thêm tile có marginal value cao nhất.
4. Cập nhật own supply và market price.
5. Lặp đến khi hết capacity/cash hoặc marginal value không còn dương.

### Nâng cấp

- Beam search trên candidate portfolio.
- Rolling-horizon replan mỗi turn hoặc mỗi event quan trọng.
- Constraint: cash, seed, Farm capacity, shed, deadline và concentration risk.

### Output

```text
tiles_by_crop
seeds_to_buy
expected_revenue
expected_profit
cash_timing
sale_batches
risk_breakdown
```

### ML/RL

- ML continuation value có thể dùng để chấm tie hoặc giá trị tái đầu tư dài hạn.
- RL chỉ cân nhắc sau khi beam-search rule baseline mạnh và action space được
  giới hạn thành macro portfolio choices.

## 12. Cụm 9 — Sell, Hold and Liquidation

**Phương pháp:** Rule + horizon optimization; ML dùng opponent forecast. RL
không cần ở giai đoạn đầu.

**Mức ưu tiên:** P0/P1.

### Cần thử

- Bán ngay.
- Giữ 1, 2, 3, 5 ngày.
- Giữ tới town-demand event lớn tiếp theo.
- Giữ tới latest safe liquidation step.
- Bán một phần và giữ phần còn lại.

### Giá trị mỗi lựa chọn

```text
net sell value at horizon
  = sequential sale revenue
  - liquidity opportunity cost
  - expected overflow loss
  - terminal unsold risk
```

### Hard rules

- Final liquidation trước khi market không còn xử lý được order.
- Shed pressure cao phải ưu tiên giải phóng capacity.
- Thiếu working capital có thể bán sớm dù future quote cao hơn.
- Không giữ hàng nếu revenue gain nhỏ hơn cơ hội tái đầu tư bị mất.

### Output

```text
item, quantity_to_sell, quantity_to_hold, best_sell_step,
revenue_now, revenue_best_horizon, net_advantage, reason
```

## 13. Cụm 10 — Shed Forecast

**Phương pháp:** Exact rule cộng với Farm schedule. Không cần ML/RL.

**Mức ưu tiên:** P1.

### Công thức

```text
future shed usage
  = current shed usage
  + scheduled deposits
  + market purchases landing in shed
  - scheduled sales
  - items picked up for use

overflow quantity
  = max(0, future shed usage - capacity)
```

### Cần tính

- Shed usage theo từng event/step.
- End-of-day auto-drop và phần overflow bị mất.
- Incoming harvest/animal/fertilizer/purchase.
- Giá trị tiền của item có nguy cơ bị discard.
- Thứ tự thanh lý tối ưu khi cần chỗ.

### Output

- Current/projected usage.
- First overflow step.
- Quantity và expected value at risk.
- Suggested sell candidates.

## 14. Cụm 11 — Cash and Working Capital

**Phương pháp:** Exact rule + optimization. ML continuation value là tùy chọn.

**Mức ưu tiên:** P1.

### Cần tính

```text
required reserve
  = planned seed obligations
  + feed obligations
  + planned hire quotes
  + other committed purchases
  + emergency buffer

spendable cash
  = max(0, current money - required reserve)
```

- Cash flow theo thời gian: chi lúc nào, thu lúc nào.
- Payback step của từng investment.
- Liquidity cost của việc HOLD.
- Không dùng doanh thu chưa xảy ra để thanh toán order hiện tại.
- Thứ tự market order có thể làm thay đổi available cash.

### Output

```text
cash_now
required_reserve
spendable_cash
cash_flow_timeline
liquidity_warning
```

## 15. Cụm 12 — Seed Purchase Quote

**Phương pháp:** Exact rule + portfolio optimization. Không cần ML/RL.

**Mức ưu tiên:** P1.

### Economy cung cấp

- Fixed seed price.
- Expected/marginal profit của mỗi seed.
- Maximum economically profitable quantity.
- Affordability theo spendable cash.

### Farm cung cấp

- Number of feasible planting slots.
- Earliest planting/selling steps.
- Existing committed workload.

### Shared Strategy tính

```text
quantity to buy
  = min(economically profitable quantity,
        affordable quantity,
        feasible planting capacity)
```

Phải tôn trọng seed mua turn này chỉ có sau existing unit actions.

## 16. Cụm 13 — Hire Quote

**Phương pháp:** Exact quote trong Economy; decision optimization ở Shared
Strategy. Không cần ML/RL ban đầu.

**Mức ưu tiên:** P1.

### Economy

- Quote Fibonacci cost cho hand tiếp theo và nhiều hand liên tiếp.
- Báo cash impact và remaining working capital.
- Không tự kết luận `có farm task` nghĩa là nên thuê.

### Farm

- Chạy planner với và không có extra hand.
- Báo giá trị công việc được cứu, số action hữu ích và thời gian còn lại trong
  ngày.

### Shared Strategy

```text
net hire value
  = value of rescued/completed work
  - hire cost
```

Không hire nếu hand xuất hiện quá muộn và biến mất trước khi tạo giá trị.

## 17. Cụm 14 — Land Investment

**Phương pháp:** Exact rule + portfolio optimization. ML continuation value là
tùy chọn; RL không cần.

**Mức ưu tiên:** P1/P2.

### Cần tính

- Official land price và 25 new tiles.
- Portfolio tốt nhất trên đất mới, không chỉ một crop cycle đơn giản.
- Own price impact của toàn bộ output.
- Seed/feed/setup working capital.
- Profit before land, net value và payback step.
- Opportunity cost của cash và risk hết mùa.

### Formula

```text
net land value
  = value of feasible production on new land
  - seed/feed costs
  - land cost
  - liquidity/risk penalties
```

Farm phải xác nhận current utilization và incremental labor capacity.

## 18. Cụm 15 — Animal Economics

**Phương pháp:** Exact rule + horizon optimization. ML chỉ hỗ trợ price/opponent
forecast; RL không cần ban đầu.

**Mức ưu tiên:** P2 sau khi Farm có animal state machine.

### Cần tính

- Animal fixed purchase cost.
- Product schedule và max-held capacity.
- Required Wheat plan và feed opportunity cost.
- Product price tại từng feasible sell batch.
- Fertilizer co-product value.
- Payback step và terminal profit.
- Scenario có/không care bonus.

### Formula

```text
animal profit
  = product sale revenue
  + fertilizer economic value
  - animal purchase cost
  - wheat economic cost
```

Không bật BUY_ANIMAL nếu Farm chưa hỗ trợ build, pickup, place, feed, care,
harvest và shed logistics.

## 19. Cụm 16 — Wheat Feed Economics

**Phương pháp:** Exact rule + opportunity-cost optimization.

**Mức ưu tiên:** P2.

### So sánh

- Tự trồng Wheat.
- Mua Wheat từ market.
- Dùng Wheat hiện có thay vì bán.
- Không mở rộng animal production.

### Economic cost

```text
wheat economic cost
  = max(acquisition cost,
        foregone sell value,
        best alternative use value)
```

Output phải cho biết feed plan nào tạo animal net profit cao nhất.

## 20. Cụm 17 — Fertilizer Economics

**Phương pháp:** Exact rule + marginal-value optimization.

**Mức ưu tiên:** P2.

### Với mỗi crop candidate

```text
incremental fertilizer revenue
  = crop revenue with fertilizer
  - crop revenue without fertilizer

fertilizer net value
  = incremental fertilizer revenue
  - fertilizer opportunity cost
```

Opportunity cost là giá trị tốt nhất giữa bán, giữ hoặc dùng cho crop khác.

Farm phải trả feasible target, application step và expected yield change.

## 21. Cụm 18 — Risk and Scenario Engine

**Phương pháp:** Probabilistic rule; ML cung cấp opponent distributions. RL
không cần.

**Mức ưu tiên:** P2.

### Scenario tối thiểu

- Conservative: town demand thấp, opponent supply cao, Farm output thấp.
- Expected: expectation hiện tại.
- Optimistic: town demand cao, opponent supply thấp, Farm output đầy đủ.

### Output

```text
profit_low, profit_expected, profit_high
price_low, price_expected, price_high
probability_of_positive_profit
confidence
assumption_list
```

### Risk-adjusted score baseline

```text
risk-adjusted value
  = 0.7 * expected profit
  + 0.3 * conservative profit
```

Trọng số phải nằm trong settings và benchmark, không coi là luật chính thức.

## 22. Cụm 19 — Endgame and Liquidation

**Phương pháp:** Exact rule + optimization. Không dùng ML/RL.

**Mức ưu tiên:** P0/P1 vì sai endgame làm mất toàn bộ giá trị hàng.

### Cần tính

- Latest profitable planting/selling step cho từng crop.
- Latest animal purchase step còn hoàn vốn.
- Latest land purchase step còn hoàn vốn.
- Last step market orders còn được xử lý.
- Lịch thanh lý shed đủ sớm.
- Giá trị terminal của unsold goods, seeds và unfinished production bằng 0.

### Hard rules

- Không mua seed nếu output không thể vào tiền trước terminal.
- Không mua investment không thể hoàn vốn.
- Ưu tiên bán hàng trước terminal dù current quote thấp.

## 23. Cụm 20 — Opportunity Ranking

**Phương pháp:** Rule + optimization; ML continuation value có thể bổ sung. RL
chỉ là nâng cấp cuối.

**Mức ưu tiên:** P1/P2.

### Candidate chung

- Plant/add one tile of crop X.
- Sell/hold quantity of item X.
- Buy seed quantity.
- Hire next hand.
- Buy next land.
- Start animal plan.
- Buy/use/sell Fertilizer hoặc Wheat.
- Keep cash.

### Thước đo chung

```text
marginal terminal-money value
  = expected final money with candidate
  - expected final money without candidate
```

Không xếp hạng bằng các priority số tùy ý nếu các candidate đã có thể quy đổi
thành coin.

### ML continuation value

Sau khi rule baseline mạnh, có thể học:

```text
V(state) = expected final money from current state
```

Và chấm candidate:

```text
Q(state, action)
  = exact short-horizon cash flow
  + V(next state)
```

ML không được bỏ qua action mask, cash, shed, deadline hoặc feasibility.

## 24. Có nên dùng RL không?

RL không phải dependency để hoàn thành Economy. Chỉ thử khi tất cả điều kiện
sau đã đạt:

- Exact local simulator được regression-test với interpreter.
- Farm planner hoàn chỉnh crop/animal/logistics.
- Economy calculator và opponent baseline ổn định.
- Candidate macro-action có action mask.
- Có population self-play và benchmark nhiều seed.
- Rule/beam-search baseline đủ mạnh để làm đối chứng.

Nếu dùng, RL chỉ chọn macro-action như:

```text
portfolio allocation
sell/hold horizon
hire count
land/animal investment
cash allocation
```

RL không chọn trực tiếp `NORTH`, `WATER`, `HARVEST` hoặc raw market tuple. Farm
planner và Fusion vẫn kiểm soát hành động thật.

Reward train ưu tiên terminal own money, kèm shaping nhỏ nếu cần cho realized
cash flow; không dùng shaping làm thay đổi mục tiêu cuối cùng.

## 25. Contract cần nhận từ Farm

Economy cần một contract theo batch, không chỉ một boolean `feasible`:

```text
ProductionQuote
  item
  source/candidate id
  feasible quantity
  earliest production step
  earliest harvest step
  earliest shed step
  earliest sell step
  latest safe sell step
  required extra hands
  expected loss/overflow
  confidence
```

Farm cũng cần báo:

- Empty/usable tiles theo horizon.
- Maximum manageable plants/animals.
- Workload và urgent workload.
- Incremental capacity khi thêm một hand hoặc land.
- Expected yield với/không fertilizer/care.

Economy không cần coordinates; chỉ cần schedule và capacity đã tổng hợp.

## 26. Vòng lặp Farm–Economy–Strategy

Một pass là chưa đủ vì production làm thay đổi market price.

```text
1. Economy sinh candidate sơ bộ bằng giá hiện tại/forecast.
2. Shared Strategy chọn một số portfolio candidate.
3. Farm trả feasible production/sell schedule cho từng candidate.
4. Economy reprice toàn bộ batch tại đúng sell steps và quantities.
5. Shared Strategy loại candidate âm hoặc không khả thi.
6. Lặp tới khi portfolio ổn định hoặc hết beam-search budget.
7. Fusion kiểm tra cash, seed, shed, order count và action validity.
```

## 27. Lộ trình triển khai

### Phase 0 — Parity và data contract

1. Hoàn thiện Snapshot theo nguồn supply.
2. Hoàn thiện exact pricing và multi-unit buy/sell quote.
3. Tách exact town-demand schedule.
4. Thêm `remaining_turns` và step-level horizons.

### Phase 1 — Economy core hoàn chỉnh

5. Xây `forecast_item(item, days_ahead, scenario)`.
6. Xây own/opponent supply batches.
7. Nâng `quote_crop` lên multi-tile và multi-batch.
8. Thêm exact endgame feasibility và liquidation.
9. Nâng sell/hold thành multi-horizon và partial quantity.

### Phase 2 — Resource allocation

10. Shed forecast.
11. Cash-flow timeline và dynamic reserve.
12. Seed quantity quote.
13. Portfolio marginal-greedy, sau đó beam search.
14. Hire và land marginal-value quotes.

### Phase 3 — Secondary production

15. Animal product economics.
16. Wheat feed opportunity cost.
17. Fertilizer sell/use optimization.

### Phase 4 — Uncertainty và ML

18. Rule scenario engine.
19. Thu replay dataset local.
20. Train opponent sell probability/quantity models.
21. Chỉ bật model sau out-of-seed benchmark improvement.
22. Thử continuation-value model nếu rule decisions vẫn thiếu dài hạn.

### Phase 5 — RL tùy chọn

23. Macro-action environment và action masks.
24. Population self-play.
25. So sánh RL với rule/beam-search trên cùng seed suite.
26. Không dùng RL nếu không cải thiện ổn định và giải thích được failure modes.

## 28. Gợi ý tổ chức file

```text
kaggriculture_agent/economy/
  snapshot.py          # observable economy state
  pricing.py           # exact official price and order quotes
  demand.py            # exact/expected town demand
  supply.py            # own supply batches
  opponent.py          # rule/ML opponent forecast
  future_market.py     # generic item inventory/price forecast
  crops.py             # crop cash-flow quote
  portfolio.py         # crop allocation optimization
  selling.py           # sell/hold/liquidation
  shed.py              # capacity and overflow forecast
  cash.py              # reserve and cash-flow timeline
  seeds.py             # seed quantity quotes
  investment.py        # hire and land quotes
  animals.py           # animal/product economics
  feed.py              # Wheat feed economics
  fertilizer.py        # fertilizer sell/use valuation
  risk.py              # scenarios and confidence
  analyzer.py          # orchestrate modules, no duplicate formulas
```

Không cần tạo tất cả file ngay. Chỉ tách khi module đã có trách nhiệm rõ và test
riêng; tránh tạo nhiều file rỗng.

## 29. Test và benchmark bắt buộc

### Unit tests

- Interpreter parity cho price và multi-unit orders.
- Town schedule tại boundary và duplicated shops.
- No supply double-counting.
- Crop multi-batch và own price impact.
- Endgame feasibility theo step/hour.
- Sell/hold, partial liquidation và price floor.
- Shed overflow và end-of-day deposits.
- Cash/order sequencing.
- Land/hire/animal/fertilizer quote boundaries.

### Integration tests

- Economy không phát unit operations.
- Shared Strategy không mua quá Farm capacity.
- Purchases/hire không được giả sử khả dụng cho existing unit actions cùng turn.
- Fusion không vượt cash, shed quantity hoặc market-order cap.

### Benchmark

- Full 720-turn matches.
- Cùng seed suite cho before/after.
- Starter, random, mirror self-play và population strategies.
- Theo dõi:
  - final money;
  - average/median/worst-decile margin;
  - invalid/no-op action rate;
  - unsold terminal inventory;
  - shed overflow loss;
  - crop/animal investment payback;
  - forecast price/inventory error.

## 30. Definition of Done cho Economy

Economy được xem là hoàn chỉnh ở mức rule-based khi:

1. Forecast được mọi market item theo step/horizon và scenario.
2. Quote đúng crop multi-tile, multi-batch và terminal feasibility.
3. Chọn được sell/hold quantity/horizon.
4. Quản lý được cash và shed theo timeline.
5. Báo giá được seed, hire, land, animal, feed và fertilizer.
6. Nhận Farm production schedule rồi reprice chính xác.
7. Xếp hạng mọi candidate theo marginal terminal-money value.
8. Không dùng private information của đối thủ.
9. Không phát unit action hoặc vượt ownership boundary.
10. Vượt baseline ổn định trên full-season multi-seed benchmark.

ML được xem là đáng dùng khi nó cải thiện forecast đối thủ và final money ngoài
tập train. RL chỉ được xem là đáng dùng khi macro-policy thắng rule/optimization
baseline ổn định trên population self-play; RL không phải tiêu chí bắt buộc để
Economy hoàn thành.
