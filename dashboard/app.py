"""Streamlit replay inspector for learning the Kaggriculture agent."""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.replay import LocalReplay, run_local_match  # noqa: E402
from dashboard.view_models import (  # noqa: E402
    TurnAnalysis,
    analyze_turn,
    crop_score_breakdown,
)
from kaggriculture_agent.domain import BASE_PRICES, CROPS  # noqa: E402

CROP_SYMBOLS = {
    "WHEAT": "🌾",
    "CARROT": "🥕",
    "TOMATO": "🍅",
    "STRAWBERRY": "🍓",
    "MELON": "🍈",
}
ANIMAL_SYMBOLS = {"GOOSE": "🪿", "COW": "🐄", "SHEEP": "🐑"}
ITEM_NAMES_VI = {
    "WHEAT": "Lúa mì",
    "CARROT": "Cà rốt",
    "TOMATO": "Cà chua",
    "STRAWBERRY": "Dâu tây",
    "MELON": "Dưa lưới",
    "EGG": "Trứng",
    "MILK": "Sữa",
    "WOOL": "Len",
    "FERTILIZER": "Phân bón",
}
SHOP_NAMES_VI = {
    "BAKERY": "Tiệm bánh",
    "PIZZA_SHOP": "Tiệm pizza",
    "BRUNCH_SPOT": "Quán ăn trưa",
    "YARN_STORE": "Cửa hàng len",
    "ICE_CREAM_SHOP": "Tiệm kem",
    "PET_CAFE": "Quán cà phê thú cưng",
    "SMOOTHIE_SHOP": "Tiệm sinh tố",
    "FARMERS_MARKET": "Chợ nông sản",
}
REPLAY_CACHE_VERSION = "economy-forecast-v4"


@st.cache_data(show_spinner=False)
def _load_match(seed: int, opponent: str, player: int, cache_version: str) -> LocalReplay:
    if cache_version != REPLAY_CACHE_VERSION:
        raise ValueError("unsupported replay cache version")
    return run_local_match(seed=seed, opponent=opponent, player=player)


def _inventory_text(values: Mapping[str, Any]) -> str:
    parts = [
        f"{_item_text(item)}: {int(count)}" for item, count in values.items() if int(count or 0) > 0
    ]
    return ", ".join(parts) if parts else "Trống"


def _item_text(item: str) -> str:
    name = ITEM_NAMES_VI.get(item)
    return f"{name} ({item})" if name else item


def _shop_text(shop: str) -> str:
    name = SHOP_NAMES_VI.get(shop)
    return f"{name} ({shop})" if name else shop


def _counts_text(values: Mapping[str, Any]) -> str:
    return _inventory_text(values) if values else "Không có"


def _combined_inventory_text(inventories: Sequence[Mapping[str, int]]) -> str:
    combined: Counter[str] = Counter()
    for inventory in inventories:
        combined.update({item: int(count or 0) for item, count in inventory.items()})
    return _inventory_text(combined)


def _command_text(command: Sequence[Any]) -> str:
    raw = " ".join(str(part) for part in command)
    if not command:
        return raw
    operation = str(command[0])
    labels = {
        "SELL": "Bán",
        "BUY_SEED": "Mua hạt giống",
        "BUY_PRODUCT": "Mua sản phẩm",
        "BUY_ANIMAL": "Mua vật nuôi",
        "HIRE": "Thuê nhân công",
        "BUY_LAND": "Mua đất",
    }
    label = labels.get(operation)
    if label is None:
        return raw
    details = ""
    if len(command) > 1:
        details = f" {_item_text(str(command[1]))}"
    if len(command) > 2:
        details += f" × {command[2]}"
    return f"{label}{details}  [{raw}]"


def _economy_schema_is_current(analysis: TurnAnalysis) -> bool:
    """Detect modules retained by an old Streamlit process before rendering."""
    opportunities = analysis.economy.crop_opportunities
    required_crop_fields = (
        "expected_sell_price",
        "expected_unit_prices",
        "known_town_consumption",
    )
    return (
        bool(opportunities)
        and all(hasattr(opportunities[0], field) for field in required_crop_fields)
        and hasattr(analysis.economy, "sell_opportunities")
    )


def _reason_vi(reason: str) -> str:
    translations = {
        "final-day liquidation: unsold goods score zero": (
            "Bán hết vào ngày cuối vì hàng chưa bán không được tính điểm"
        ),
        "sell to prevent shed overflow": "Bán để tránh kho bị đầy và mất hàng",
        "sell to restore the configured cash reserve": "Bán để khôi phục tiền dự phòng",
        "sell-now revenue is at least the one-day hold forecast": (
            "Doanh thu bán ngay không thấp hơn dự báo giữ thêm một ngày"
        ),
        "hold one day: known/expected town demand may improve the quote": (
            "Giữ thêm một ngày vì nhu cầu thị trấn có thể làm giá tốt hơn"
        ),
    }
    return translations.get(reason, reason)


def _tile_text(tile: Any) -> str:
    if tile == "LOCKED":
        return "🔒"
    if tile is None:
        return "·"
    if not isinstance(tile, Mapping):
        return "?"
    if tile.get("kind") == "WEED":
        return "🌿"
    if tile.get("kind") == "PLANT":
        crop = str(tile.get("crop", ""))
        units = int(tile.get("yield_units", 0) or 0)
        return f"{CROP_SYMBOLS.get(crop, '🌱')}{units}"
    animal = str(tile.get("animal", ""))
    if animal:
        units = int(tile.get("yield_units", 0) or 0)
        return f"{ANIMAL_SYMBOLS.get(animal, '🐾')}{units}"
    if tile.get("kind") == "COOP":
        return "▧"
    if tile.get("kind") == "PASTURE":
        return "□"
    return "?"


def _board_table(farm: Mapping[str, Any]) -> dict[str, list[str]]:
    rows = farm.get("tiles", ()) or ()
    farmer = tuple(farm.get("farmer", ()) or ())
    hands = Counter(tuple(position) for position in (farm.get("hands", ()) or ()))
    rendered: list[list[str]] = []
    for y, row in enumerate(rows):
        rendered_row: list[str] = []
        for x, tile in enumerate(row):
            position = (x, y)
            units = (1 if position == farmer else 0) + hands[position]
            prefix = "🧑" if units == 1 else f"🧑×{units}" if units > 1 else ""
            rendered_row.append(f"{prefix}{_tile_text(tile)}")
        rendered.append(rendered_row)
    width = max((len(row) for row in rendered), default=0)
    return {str(x): [row[x] for row in rendered] for x in range(width)}


def _growing_crop_rows(analysis: TurnAnalysis) -> list[dict[str, Any]]:
    planted: Counter[str] = Counter()
    yield_units: Counter[str] = Counter()
    harvestable_units: Counter[str] = Counter()
    watered_tiles: Counter[str] = Counter()
    for row in analysis.state.tiles:
        for tile in row:
            if not isinstance(tile, Mapping) or tile.get("kind") != "PLANT":
                continue
            crop = str(tile.get("crop", ""))
            spec = CROPS.get(crop)
            if spec is None:
                continue
            planted[crop] += 1
            units = int(tile.get("yield_units", 0) or 0)
            yield_units[crop] += units
            age = analysis.state.day - int(tile.get("planted_day", analysis.state.day))
            if age >= spec.first_yield_day:
                harvestable_units[crop] += units
            if bool(tile.get("watered_today", False)):
                watered_tiles[crop] += 1

    return [
        {
            "Cây": _item_text(crop),
            "Ô đang trồng": planted[crop],
            "yield_units trên board": yield_units[crop],
            "Thu hoạch được ngay": harvestable_units[crop],
            "Ô đã tưới hôm nay": watered_tiles[crop],
            "Model units/ô": CROPS[crop].unfertilized_yield,
            "Ngày đạt model units": CROPS[crop].unfertilized_peak_day,
        }
        for crop in sorted(planted)
    ]


def _growing_crop_text(rows: Sequence[Mapping[str, Any]]) -> str:
    if not rows:
        return "Không có"
    return ", ".join(f"{row['Cây']}: {row['Ô đang trồng']} ô" for row in rows)


def _market_rows(analysis: TurnAnalysis) -> list[dict[str, Any]]:
    return [
        {
            "Sản phẩm": _item_text(item),
            "Giá hiện tại": float(analysis.snapshot.prices.get(item, base)),
            "Giá gốc": base,
            "Tỉ lệ giá": round(analysis.economy.price_ratios.get(item, 1.0), 2),
            "Thị trấn dùng/ngày": round(analysis.economy.demand.get(item, 0.0), 1),
            "Hàng trong kho": int(analysis.snapshot.shed.get(item, 0) or 0),
        }
        for item, base in BASE_PRICES.items()
    ]


def _crop_rows(analysis: TurnAnalysis) -> list[dict[str, Any]]:
    return [
        {
            "Hạng": rank,
            "Cây": _item_text(item.crop),
            "Giá hiện tại": float(analysis.snapshot.prices.get(item.crop, 0.0)),
            "Giá hạt": item.seed_cost,
            "Ngày chiếm đất": item.days_to_maturity,
            "Sản lượng": item.expected_units,
            "Giá bán dự kiến": round(item.expected_sell_price, 1),
            "Lợi nhuận": round(item.expected_profit, 1),
            "Điểm": None if item.score == float("-inf") else round(item.score, 1),
            "Kịp mùa": "Có" if item.feasible else "Không",
            "Đối thủ sẵn sàng bán": int(analysis.economy.opponent_visible_supply.get(item.crop, 0)),
        }
        for rank, item in enumerate(analysis.economy.crop_opportunities, start=1)
    ]


def _intent_rows(analysis: TurnAnalysis) -> list[dict[str, Any]]:
    proposed = [intent.command for intent in analysis.plan.market_intents]
    accepted = Counter(analysis.final.market_commands)
    rows: list[dict[str, Any]] = []
    for command in proposed:
        is_accepted = accepted[command] > 0
        if is_accepted:
            accepted[command] -= 1
        rows.append(
            {
                "Lệnh đề xuất": _command_text(command),
                "Kiểm tra cuối": "Chấp nhận" if is_accepted else "Từ chối",
            }
        )
    return rows


def _why_text(analysis: TurnAnalysis) -> list[str]:
    messages: list[str] = []
    selected = analysis.plan.selected_crop
    if selected:
        messages.append(f"Bộ phận kinh tế đang xếp {_item_text(selected)} là cây khả thi tốt nhất.")
        buys_selected = any(
            command[0] == "BUY_SEED" and len(command) > 1 and command[1] == selected
            for command in analysis.final.market_commands
        )
        if not buys_selected and not analysis.farm.empty_tiles:
            messages.append(
                f"Không mua hạt {_item_text(selected)} vì trang trại không còn ô trống."
            )
    hire_count = sum(command[0] == "HIRE" for command in analysis.final.market_commands)
    if hire_count:
        messages.append(
            f"Thuê {hire_count} người vì bộ phận trang trại báo có "
            f"{analysis.farm.urgent_count} việc khẩn cấp."
        )
    if analysis.snapshot.shed and not analysis.economy.market_intents:
        messages.append("Hàng tiếp tục nằm trong kho vì chưa thỏa điều kiện bán.")
    if not analysis.snapshot.shed:
        messages.append("Không có lệnh bán (SELL) vì kho đang trống.")
    return messages


def _render_observation(analysis: TurnAnalysis) -> None:
    crop_rows = _growing_crop_rows(analysis)
    own, opponent = st.columns(2)
    with own:
        st.subheader("Trang trại của mình")
        st.dataframe(_board_table(analysis.state.me), width="stretch", height=390)
    with opponent:
        st.subheader("Trang trại đối thủ (chỉ dữ liệu công khai)")
        st.dataframe(_board_table(analysis.state.opponent), width="stretch", height=390)
    st.caption(
        "🧑 người làm · 🔒 đất chưa mua · 🌿 cỏ dại · số cạnh biểu tượng là "
        "yield_units hiện tại của ô. Ví dụ 🍈5 = một ô Melon có yield_units=5, "
        "không phải 5 cây."
    )

    st.subheader("Cây đang trồng trên farm của mình")
    if crop_rows:
        st.dataframe(crop_rows, width="stretch", hide_index=True)
        st.info(
            "`Model units/ô` là sản lượng Economy dùng để dự báo khi cây được chăm đúng "
            "giả định. Con số này đến từ luật crop, không đến từ số hạt giống đang giữ."
        )
    else:
        st.write("Chưa có cây nào đang trồng.")

    market, private = st.columns([3, 2])
    with market:
        st.subheader("Chợ và thị trấn")
        st.dataframe(_market_rows(analysis), width="stretch", hide_index=True)
        shops = list(analysis.snapshot.unlocked_shops)
        st.write(
            "Cửa hàng đã mở:",
            [_shop_text(shop) for shop in shops] if shops else "Chưa có cửa hàng",
        )
    with private:
        st.subheader("Tài sản của mình")
        st.write("Kho:", _inventory_text(analysis.snapshot.shed))
        st.write("Hạt giống chưa trồng:", _inventory_text(analysis.snapshot.seeds))
        st.write("Cây đang trồng:", _growing_crop_text(crop_rows))
        st.write("Hàng người làm đang cầm:", _combined_inventory_text(analysis.state.inventories))
        st.write(f"Mức sử dụng kho: {analysis.snapshot.shed_usage_ratio:.0%}")
        st.caption(
            "Hạt giống, cây trên farm và sản phẩm thu hoạch là ba loại tài sản khác nhau. "
            "Farm board là công khai; kho, hạt giống và đồ người làm đang cầm là private."
        )
        st.subheader("Thông tin đối thủ nhìn thấy")
        st.write("Cây đang trồng:", _counts_text(analysis.snapshot.opponent_crop_counts))
        st.write(
            "Sản lượng sẵn sàng:",
            _counts_text(analysis.snapshot.opponent_visible_supply),
        )
        st.caption("Bot không được xem kho, hạt giống hay đồ người làm đối thủ đang cầm.")


def _render_economy(analysis: TurnAnalysis) -> None:
    with st.expander("Bản đồ công thức: đã làm gì và còn thiếu gì?"):
        st.dataframe(
            [
                {
                    "Bài toán": "Giá trong chợ",
                    "Trạng thái": "Đúng công thức chính thức",
                    "Đầu vào chính": "Lượng hàng trong chợ và tham số chính thức",
                },
                {
                    "Bài toán": "Nhu cầu thị trấn",
                    "Trạng thái": ("Chính xác với cửa hàng đã mở; dự báo cửa hàng tương lai"),
                    "Đầu vào chính": "Danh sách cửa hàng và chu kỳ tiêu thụ",
                },
                {
                    "Bài toán": "Giá trị cây trồng",
                    "Trạng thái": "Đã có dự báo cơ bản",
                    "Đầu vào chính": "Giá tương lai, sản lượng và giá hạt",
                },
                {
                    "Bài toán": "Bán hay giữ hàng",
                    "Trạng thái": "Đã so sánh với giữ thêm một ngày",
                    "Đầu vào chính": "Giá từng đơn vị, nhu cầu và sức chứa kho",
                },
                {
                    "Bài toán": "Thuê người",
                    "Trạng thái": ("Đúng giá thuê; cần bộ phận trang trại báo khối lượng việc"),
                    "Đầu vào chính": "Giá Fibonacci và việc khẩn cấp",
                },
                {
                    "Bài toán": "Mua đất",
                    "Trạng thái": "Định giá một vụ và tác động lên giá bán",
                    "Đầu vào chính": "25 ô, tiền hạt, doanh thu và giá đất",
                },
                {
                    "Bài toán": "Đối thủ",
                    "Trạng thái": "Mới dùng sản lượng công khai đã sẵn sàng",
                    "Đầu vào chính": "Trang trại công khai của đối thủ",
                },
                {
                    "Bài toán": "Động vật và phân bón",
                    "Trạng thái": "Chưa bật",
                    "Đầu vào chính": "Cần trang trại hỗ trợ xây, đặt và cho ăn",
                },
            ],
            width="stretch",
            hide_index=True,
        )
    st.subheader("Xếp hạng cây trồng")
    st.dataframe(_crop_rows(analysis), width="stretch", hide_index=True)

    default_crop = analysis.plan.selected_crop or analysis.economy.crop_opportunities[0].crop
    crop_names = [item.crop for item in analysis.economy.crop_opportunities]
    crop = st.selectbox(
        "Chọn cây để xem cách tính",
        crop_names,
        index=crop_names.index(default_crop),
    )
    detail = crop_score_breakdown(analysis, crop)
    st.code(
        "\n".join(
            [
                f"Giá hiện tại                                  = {detail.current_price:.0f}",
                "Lượng hàng hiện tại trong chợ                 "
                f"= {detail.current_market_inventory}",
                "Thị trấn dự kiến tiêu thụ                      "
                f"= {detail.projected_town_consumption:.1f}",
                "  ├─ Từ trung tâm và cửa hàng đã biết         "
                f"= {detail.known_town_consumption:.1f}",
                "  └─ Kỳ vọng từ cửa hàng ngẫu nhiên tương lai "
                f"= {detail.expected_future_shop_consumption:.1f}",
                f"Hàng mình đang chờ đưa ra chợ                 = {detail.own_supply_assumption}",
                "Hàng sẵn sàng nhìn thấy của đối thủ            "
                f"= {detail.opponent_supply_assumption}",
                "Lượng hàng dự kiến trong chợ                   "
                f"= {detail.current_market_inventory} − "
                f"{detail.projected_town_consumption:.1f} + "
                f"{detail.own_supply_assumption} + "
                f"{detail.opponent_supply_assumption} = "
                f"{detail.projected_market_inventory:.1f}",
                f"Những ngày cây tạo sản phẩm                   = {list(detail.yield_days)}",
                f"Sản lượng dự kiến                             = {detail.expected_units}",
                "Giá bán dự kiến của từng đơn vị                = "
                f"{list(detail.expected_unit_prices)}",
                "Giá bán dự kiến trung bình                     "
                f"= {detail.expected_sell_price:.1f}",
                f"Doanh thu dự kiến                             = {detail.expected_revenue:.0f}",
                f"Giá hạt giống                                 = {detail.seed_cost}",
                "Lợi nhuận dự kiến                              "
                f"= {detail.expected_revenue:.0f} − {detail.seed_cost} "
                f"= {detail.expected_profit:.0f}",
                f"Số ngày chiếm đất                             = {detail.occupied_days}",
                "Điểm = lợi nhuận mỗi ngày chiếm đất            "
                f"= {detail.expected_profit:.0f} / {detail.occupied_days} "
                f"= {detail.score:.1f}",
                "Có kịp trước cuối mùa                          "
                f"= {'Có' if detail.feasible else 'Không'}",
            ]
        )
    )
    curve = detail.price_curve
    sign = "+" if curve.side == "scarcity" else "−"
    side_vi = "khan hiếm" if curve.side == "scarcity" else "dư cung"
    with st.expander("Công thức giá chính thức của chợ"):
        st.code(
            "\n".join(
                [
                    f"Sản phẩm                                   = {_item_text(curve.item)}",
                    f"Lượng hàng dự kiến                         = {curve.inventory:.1f}",
                    "Mốc cân bằng I0                             "
                    f"= {curve.equilibrium_inventory:.0f}",
                    f"Trạng thái thị trường                       = {side_vi}",
                    f"Khoảng cách x = |lượng hàng − I0|          = {curve.distance:.1f}",
                    f"Hàm hình dạng f                             = {curve.function}",
                    f"Sản lượng chuẩn T                           = {curve.throughput:.0f}",
                    f"Mức thay đổi mục tiêu                       = {curve.target:.2f}",
                    f"Biên độ = mục tiêu × giá gốc / f(T)         = {curve.amplitude:.4f}",
                    f"Giá thô = giá gốc {sign} biên độ × f(x)        = {curve.raw_price:.2f}",
                    f"Giá chính thức sau làm tròn và chặn đáy    = {curve.quoted_price}",
                ]
            )
        )
    st.caption(
        "Dự báo giả sử thị trấn mua đúng lịch, đối thủ bán lượng hàng đang nhìn thấy một "
        "lần và chưa đoán thêm sản lượng tương lai bị ẩn của đối thủ."
    )
    opponent_ready = int(analysis.economy.opponent_visible_supply.get(crop, 0))
    if opponent_ready:
        st.warning(
            f"Đối thủ đang có {opponent_ready} {_item_text(crop)} sẵn sàng. "
            "Dự báo giả sử lượng nhìn thấy này được bán một lần trước khi mình thu hoạch."
        )

    st.subheader("Bán ngay hay giữ hàng?")
    if analysis.economy.sell_opportunities:
        st.dataframe(
            [
                {
                    "Sản phẩm": _item_text(item.item),
                    "Số lượng": item.quantity,
                    "Doanh thu bán ngay": item.immediate_revenue,
                    f"Giữ thêm {item.hold_days} ngày": item.hold_revenue,
                    "Quyết định": "BÁN" if item.recommend_sell else "GIỮ",
                    "Lý do": _reason_vi(item.reason),
                }
                for item in analysis.economy.sell_opportunities
            ],
            width="stretch",
            hide_index=True,
        )
        selected_sell = analysis.economy.sell_opportunities[0]
        with st.expander(f"Cách tính bán {_item_text(selected_sell.item)}"):
            st.code(
                "\n".join(
                    [
                        f"Số lượng                                    = {selected_sell.quantity}",
                        "Giá bán ngay của từng đơn vị                "
                        f"= {list(selected_sell.immediate_unit_prices)}",
                        "Doanh thu nếu bán ngay                      "
                        f"= {selected_sell.immediate_revenue:.0f}",
                        "Thị trấn tiêu thụ trong lúc giữ             "
                        f"= {selected_sell.projected_town_consumption:.1f}",
                        "Giả định hàng sẵn sàng của đối thủ          "
                        f"= {selected_sell.opponent_supply_assumption}",
                        "Lượng hàng dự kiến sau khi chờ              "
                        f"= {selected_sell.projected_inventory_after_wait:.1f}",
                        "Giá từng đơn vị nếu giữ                     "
                        f"= {list(selected_sell.hold_unit_prices)}",
                        "Doanh thu nếu giữ                           "
                        f"= {selected_sell.hold_revenue:.0f}",
                        "Quyết định                                  "
                        f"= {'BÁN' if selected_sell.recommend_sell else 'GIỮ'}",
                        "Lý do                                      "
                        f"= {_reason_vi(selected_sell.reason)}",
                    ]
                )
            )
    else:
        st.info("Kho đang trống nên lượt này chưa cần quyết định bán hay giữ.")

    st.subheader("Đầu tư nhân công và đất")
    hires = [item for item in analysis.economy.investment_intents if item.command[0] == "HIRE"]
    if hires:
        st.write(
            "Giá thuê theo dãy Fibonacci:",
            [int(item.estimated_cost) for item in hires],
        )
        st.caption(
            "Bộ phận kinh tế chỉ báo giá. Chiến thuật chung dùng khối lượng "
            "việc của trang trại để quyết định mỗi người được thuê có tạo giá trị "
            "lớn hơn chi phí hay không."
        )
    land = analysis.economy.land_opportunity
    if land is not None:
        with st.expander("Cách tính giá trị mua thêm 25 ô đất"):
            st.code(
                "\n".join(
                    [
                        f"Cây dùng để ước tính                        = {_item_text(land.crop)}",
                        f"Số ô đất mới                                = {land.new_tiles}",
                        f"Giá đất                                     = {land.land_cost:.0f}",
                        f"Tổng tiền hạt giống                         = {land.seed_cost:.0f}",
                        f"Sản lượng dự kiến trong một vụ             = {land.expected_units}",
                        "Doanh thu sau khi tính tác động lên giá     "
                        f"= {land.expected_revenue:.0f}",
                        "Lợi nhuận trước khi trừ giá đất             "
                        f"= {land.expected_profit_before_land:.0f}",
                        "Giá trị ròng sau khi trừ giá đất            "
                        f"= {land.expected_profit_before_land:.0f} − "
                        f"{land.land_cost:.0f} = {land.net_value_after_land:.0f}",
                        "Thời gian hoàn vốn ước tính                 "
                        f"= {land.payback_days:.1f} ngày",
                    ]
                )
            )
            st.caption(
                "Đây là một chu kỳ trồng và đã tính tác động khi chính 25 ô mới cùng bán. "
                "Chiến thuật chung vẫn phải kiểm tra đất hiện tại có đầy và trang trại "
                "có đủ người."
            )
    else:
        st.info("Không còn lựa chọn đất mới hoặc không đủ thời gian để định giá một chu kỳ.")


def _render_decision(analysis: TurnAnalysis) -> None:
    st.subheader("Kinh tế → Trang trại → Chiến thuật chung → Kiểm tra cuối")
    selected_crop = (
        _item_text(analysis.plan.selected_crop) if analysis.plan.selected_crop else "không có cây"
    )
    st.write(
        f"Kinh tế chọn **{selected_crop}**; "
        f"trang trại báo **{analysis.farm.urgent_count} việc khẩn cấp**, "
        f"**{len(analysis.farm.empty_tiles)} ô trống**, "
        f"sử dụng đất **{analysis.farm.utilization:.0%}**."
    )
    for message in _why_text(analysis):
        st.write("•", message)

    rows = _intent_rows(analysis)
    st.subheader("Lệnh giao dịch")
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Không có lệnh giao dịch ở lượt này.")

    planned, replayed = st.columns(2)
    with planned:
        st.subheader("Quyết định được tính lại")
        st.code(json.dumps(analysis.expected_action, indent=2), language="json")
    with replayed:
        st.subheader("Hành động đã ghi trong trận")
        if analysis.recorded_action is None:
            st.info("Đây là trạng thái kết thúc nên không có hành động kế tiếp.")
        else:
            st.code(json.dumps(analysis.recorded_action, indent=2), language="json")

    if analysis.recorded_action is None:
        st.caption(
            "Vẫn có thể phân tích dữ liệu, nhưng Kaggle không gọi bot sau khi trận kết thúc."
        )
    elif analysis.expected_action == analysis.recorded_action:
        st.success("Hai hành động giống nhau: màn hình đang giải thích đúng quyết định của bot.")
    else:
        st.warning(
            "Hành động khác trận đã ghi; hãy kiểm tra trận này được tạo bằng phiên bản code nào."
        )


def main() -> None:
    st.set_page_config(page_title="Phòng phân tích Kaggriculture", layout="wide")
    st.title("Phòng phân tích Kaggriculture")
    st.caption("Chạy hoàn toàn trên máy bạn; không kết nối hoặc gửi bài lên Kaggle.")

    with st.form("match-controls"):
        seed_col, opponent_col, player_col, run_col = st.columns([2, 2, 2, 1])
        with seed_col:
            seed = int(
                st.number_input(
                    "Mã ngẫu nhiên (seed)",
                    value=20260822,
                    step=1,
                    help="Cùng mã và cùng code sẽ tạo lại cùng một trận trên máy.",
                )
            )
        with opponent_col:
            opponent = st.selectbox("Bot đối thủ", ("starter", "random", "pass"))
        with player_col:
            player = int(
                st.selectbox(
                    "Vị trí bot của mình",
                    (0, 1),
                    help="Chỉ đổi vị trí 0 hoặc 1 của bot mình trong trận trên máy.",
                )
            )
        with run_col:
            submitted = st.form_submit_button("Chạy trận", width="stretch")

    params = (seed, opponent, player)
    if submitted or "replay" not in st.session_state:
        with st.spinner("Đang chạy trận 720 lượt trên máy..."):
            st.session_state.replay = _load_match(*params, REPLAY_CACHE_VERSION)
            st.session_state.match_params = params
            st.session_state.turn = min(240, st.session_state.replay.turn_count - 1)

    replay: LocalReplay = st.session_state.replay
    active_params = st.session_state.match_params
    if params != active_params:
        st.info("Bạn đã đổi cấu hình. Bấm Chạy trận để tạo trận mới.")

    turn = st.slider(
        "Lượt",
        min_value=0,
        max_value=replay.turn_count - 1,
        key="turn",
        help="Kéo để xem trạng thái và quyết định ở thời điểm khác trong cùng trận.",
    )
    analysis = analyze_turn(replay, turn)

    if not _economy_schema_is_current(analysis):
        st.error(
            "Streamlit đang giữ phiên bản bộ phận kinh tế cũ trong bộ nhớ. "
            "Hãy dừng chương trình rồi chạy lại để nạp cấu trúc dữ liệu mới."
        )
        st.code(
            "Ctrl+C\nstreamlit run dashboard/app.py",
            language="bash",
        )
        st.stop()

    time_metric, money_metric, farm_metric = st.columns(3)
    with time_metric:
        st.metric("Thời gian", f"Ngày {analysis.state.day} · Giờ {analysis.state.hour}")
    with money_metric:
        difference = analysis.snapshot.money - analysis.snapshot.opponent_money
        st.metric(
            "Tiền",
            f"{analysis.snapshot.money:.0f}",
            delta=f"{difference:+.0f} so với đối thủ",
        )
    with farm_metric:
        st.metric(
            "Khối lượng việc trang trại",
            f"{analysis.farm.urgent_count} việc khẩn cấp",
            delta=f"Đã dùng {analysis.farm.utilization:.0%} đất",
            delta_color="off",
        )

    observation_tab, economy_tab, decision_tab = st.tabs(
        ("1 · Quan sát", "2 · Phân tích kinh tế", "3 · Quyết định cuối")
    )
    with observation_tab:
        _render_observation(analysis)
    with economy_tab:
        _render_economy(analysis)
    with decision_tab:
        _render_decision(analysis)

    st.caption(
        f"Trận hiện tại: mã ngẫu nhiên={replay.seed}, đối thủ={replay.opponent}, "
        f"vị trí bot mình={replay.player}, số trạng thái={replay.turn_count}, "
        f"tiền cuối trận={replay.final_rewards}, trạng thái={replay.final_statuses}"
    )


if __name__ == "__main__":
    main()
