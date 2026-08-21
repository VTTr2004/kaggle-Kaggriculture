# Kaggriculture Agent

Cuộc thi AI Agent do Kaggle và Google tổ chức - Quản lý trang trại ảo.

## Cài đặt

```bash
pip install kaggle-environments
```

## Chạy Agent

File submit chính là `main.py` (độc lập, không cần import các file cũ).

```bash
python -c "from main import agent; print(agent({'farms':[{'farmer':[0,0],'tiles':[[None]],'money':100}], 'private':{}, 'market':{}}))"
```

Submit:

```bash
kaggle competitions submit kaggriculture -f main.py -m "melon strategy v1"
```

## Chạy UI local

```bash
streamlit run app.py
```

```bash
python run_match.py
```

## Cấu trúc

- `agent.py` - Agent chính
- `run_match.py` - Script test local
- `strategy.py` - Chiến lược chơi
- `utils.py` - Hàm tiện ích
