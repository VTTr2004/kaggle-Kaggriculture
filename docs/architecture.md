# Architecture và workflow 2 người

## Dependency rule

Luồng dependency chỉ đi xuống:

```text
domain/models <- state <- farm,economy <- features <- strategy <- fusion <- execution <- agent
```

`farm/` không được import `economy/` và ngược lại. Hai nhánh không trả raw
Kaggle actions; chúng trả immutable feature dataclasses trong `models.py`.
Nhờ vậy từng người có thể thay rules bằng search/ML độc lập.

## Module contracts

- `build_state(obs, config) -> GameState`: chuẩn hóa dict hoặc Kaggle Struct.
- `analyze_farm(state) -> FarmFeatures`: phát hiện maintenance tasks và capacity.
- `analyze_economy(state) -> EconomyFeatures`: crop opportunity, demand, sell intents.
- `build_strategic_features(...) -> StrategicFeatures`: điểm gặp duy nhất của hai nhánh.
- `Strategy.decide(features) -> StrategyPlan`: rule-based hiện tại; model sau này chỉ cần giữ interface.
- `fuse_decisions(state, plan) -> FinalDecision`: giới hạn seed, cash, order count, hand count.
- `to_kaggle_action(decision) -> dict`: biên duy nhất tạo wire format.

## Git workflow đề xuất

1. `main` luôn chạy được và chỉ nhận thay đổi qua PR.
2. Person 1 làm `farm/<experiment>`, Person 2 làm `economy/<experiment>`.
3. Mỗi PR chỉ sửa module sở hữu + test tương ứng. Nếu đổi `models.py`, cả hai review.
4. Rebase/merge `main`, chạy `pytest`, rồi benchmark cùng danh sách seed.
5. Chỉ merge nếu không giảm win rate ngoài ngưỡng team thống nhất; lưu command,
   commit hash và kết quả benchmark trong mô tả PR.

## Nâng cấp Rule -> ML -> RL -> Self-play

Không thay entry point. Thêm implementation mới của protocol `Strategy` trong
`strategy/base.py`, sau đó chọn implementation trong `agent.py`.

- Farm ML dự đoán task value/travel cost, vẫn xuất `FarmFeatures`.
- Economy ML dự đoán future price/demand, vẫn xuất `EconomyFeatures`.
- RL policy đọc `StrategicFeatures`, xuất `StrategyPlan`.
- Self-play chỉ là pipeline train/evaluate bên ngoài runtime; artifact model được
  đóng cùng package và inference vẫn tuân `Strategy` contract.

Tránh state global theo player: validation của Kaggle cho agent đấu với bản sao
của chính nó và hai invocation có thể dùng chung module process.
