from __future__ import annotations

import math

import pandas as pd
import streamlit as st


def calc_seeding(n, sq, df, target_per_well, vol_per_well, plates, safety, wells_per_plate):
    if sq <= 0:
        return None, "计数的格数必须大于 0"
    if wells_per_plate <= 0:
        return None, "每块使用孔数必须大于 0"

    conc_cells_ml = (n / sq) * 10000 * df
    if conc_cells_ml == 0:
        return None, "错误：细胞计数为 0"

    total_wells = wells_per_plate * plates
    total_prep_vol = (total_wells * vol_per_well) + safety
    target_conc = target_per_well / vol_per_well
    vol_cell_stock = (target_conc * total_prep_vol) / conc_cells_ml
    vol_medium = total_prep_vol - vol_cell_stock

    result = (
        "【计算结果】\n"
        f"1. 原液细胞密度: {conc_cells_ml / 10000:.2f} x 10^4 /mL\n"
        f"2. 铺板液目标密度: {target_conc / 10000:.2f} x 10^4 /mL\n"
        f"3. 需配制总体积: {total_prep_vol:.1f} mL (含余量)\n\n"
        "👉 操作方案:\n"
        f"   取细胞悬液: {vol_cell_stock:.2f} mL ({vol_cell_stock * 1000:.1f} μL)\n"
        f"   + 培养基  : {vol_medium:.2f} mL"
    )
    return result, None


def _round_ml_step(value_ul: float, step_ml: float = 0.5) -> float:
    """Round to human-friendly mL increments (e.g., 0.5 / 1.0 / 2.5)."""
    ml = value_ul / 1000
    return round(ml / step_ml) * step_ml


def _format_conc(value: float) -> str:
    return f"{value:g}"


def _match_friendly_total_volume(value_ml: float) -> float:
    friendly_volumes = [2.0, 3.0, 4.0, 5.0, 10.0, 15.0, 20.0]
    for volume in friendly_volumes:
        if volume >= value_ml:
            return volume
    return float(math.ceil(value_ml))


def _round_up_practical(value: float, minimum: float = 0.0) -> float:
    practical_steps = [1, 2, 4, 5]
    target = max(value, minimum)
    if target <= 0:
        return minimum

    exponent = math.floor(math.log10(target))
    for power in range(exponent - 1, exponent + 6):
        base = 10 ** power
        for step in practical_steps:
            candidate = step * base
            if candidate >= target and candidate >= minimum:
                return float(candidate)
    return float(target)


def _format_volume_ml(value_ml: float, digits: int = 2) -> str:
    return f"{value_ml:.{digits}f} mL"


def _format_volume_ul(value_ul: float, digits: int = 0) -> str:
    return f"{value_ul:.{digits}f} μL"


def _split_parallel_10x_chains(final_targets_nm: list[float]) -> list[dict[str, object]]:
    chain_map: dict[float, list[float]] = {}
    for target in final_targets_nm:
        exponent = math.floor(math.log10(target))
        mantissa = target / (10 ** exponent)
        mantissa_key = round(mantissa, 6)
        chain_map.setdefault(mantissa_key, []).append(target)

    chains = []
    for idx, (_, targets) in enumerate(
        sorted(chain_map.items(), key=lambda item: max(item[1]), reverse=True)
    ):
        sorted_targets = sorted(set(targets), reverse=True)
        chains.append(
            {
                "chain_id": f"Chain {chr(65 + idx)}",
                "final_targets_nm": sorted_targets,
                "working_targets_nm": [target * 2 for target in sorted_targets],
            }
        )
    return chains


def calc_single_dual_chain(
    stock_mm: float,
    min_pipette_ul: float,
    reserve_ul: float,
    targets_text: str,
    unit_label: str = "nM",
    unit_to_nm: float = 1.0,
    work_conc_factor: float = 2.0,
    trigger_ratio: float = 100.0,
) -> tuple[dict[str, object] | None, str | None]:
    if stock_mm <= 0:
        return None, "母液浓度必须大于 0"
    if min_pipette_ul <= 0:
        return None, "最小移液量必须大于 0"
    if reserve_ul <= 0:
        return None, "最终保留体积必须大于 0"
    if unit_to_nm <= 0 or work_conc_factor <= 0:
        return None, "浓度换算参数无效"

    try:
        raw_targets = targets_text.replace("，", ",").split(",")
        parsed_targets = sorted({float(x) for x in raw_targets if x.strip()}, reverse=True)
    except ValueError:
        return None, "请输入有效数字，注意单位换算"

    has_zero = 0 in parsed_targets
    positive_targets = [target for target in parsed_targets if target > 0]
    if not positive_targets and not has_zero:
        return None, "请输入至少一个目标浓度"

    positive_targets_nm = [target * unit_to_nm for target in positive_targets]
    chains = _split_parallel_10x_chains(positive_targets_nm)
    stock_nm = stock_mm * 1_000_000
    highest_working_nm = max((max(chain["working_targets_nm"]) for chain in chains), default=0.0)

    if highest_working_nm <= 0:
        return None, "未检测到有效的正浓度"
    if highest_working_nm > stock_nm:
        return None, "最高 2× 工作液浓度高于母液浓度，无法配制"

    use_intermediate = (stock_nm / highest_working_nm) > trigger_ratio
    intermediate_nm = stock_nm / 1000 if use_intermediate else stock_nm
    if use_intermediate and highest_working_nm > intermediate_nm:
        return None, "按 1000× 规则生成的中间母液浓度不足以覆盖最高工作浓度，请提高母液浓度或降低最高目标浓度"

    reserve_ml = reserve_ul / 1000
    dead_volume_ml = 1.5
    target_volume_ml = reserve_ml + dead_volume_ml
    min_prep_volume_ml = target_volume_ml / 0.9
    practical_tube_ml = _match_friendly_total_volume(min_prep_volume_ml)
    propagation_take_ml = practical_tube_ml / 10
    propagation_medium_ml = practical_tube_ml * 0.9

    step1_rows = []
    total_intermediate_needed_ml = 0.0
    chain_summaries = []

    for chain in chains:
        root_final_nm = chain["final_targets_nm"][0]
        root_working_nm = chain["working_targets_nm"][0]
        root_take_ml = practical_tube_ml * root_working_nm / intermediate_nm
        root_media_ml = practical_tube_ml - root_take_ml
        downstream_take_ml = propagation_take_ml if len(chain["final_targets_nm"]) > 1 else 0.0
        usable_after_transfer_ml = practical_tube_ml - downstream_take_ml
        total_intermediate_needed_ml += root_take_ml

        chain_display = " → ".join(
            f"{_format_conc(target_nm / unit_to_nm)} {unit_label}"
            for target_nm in chain["final_targets_nm"]
        )
        chain_summaries.append(f"{chain['chain_id']}: {chain_display}")

        step1_rows.append(
            {
                "步骤": "第 1 步",
                "链": chain["chain_id"],
                f"链头终浓度 ({unit_label})": root_final_nm / unit_to_nm,
                f"链头工作液浓度 ({unit_label}, 2×)": root_working_nm / unit_to_nm,
                "取液来源": "10 μM 中间母液" if use_intermediate else f"{stock_mm:.2f} mM 母液",
                "取液操作": _format_volume_ml(root_take_ml, 2),
                "预加培养基": _format_volume_ml(root_media_ml, 2),
                "该管配制总量": _format_volume_ml(practical_tube_ml, 2),
                "预计加板可用量": _format_volume_ml(usable_after_transfer_ml, 2),
                "备注": "链头母管",
            }
        )

    step0_rows = []
    if use_intermediate:
        minimum_intermediate_ml = float(math.ceil(min_pipette_ul))
        practical_intermediate_ml = float(
            math.ceil(max(total_intermediate_needed_ml, minimum_intermediate_ml))
        )
        intermediate_stock_ul = practical_intermediate_ml
        intermediate_medium_ml = practical_intermediate_ml - intermediate_stock_ul / 1000
        step0_rows.append(
            {
                "步骤": "第 0 步",
                "对象": "10 μM 中间母液",
                "取液来源": f"{stock_mm:.2f} mM 母液",
                "取液操作": _format_volume_ul(intermediate_stock_ul, 0),
                "预加培养基": _format_volume_ml(intermediate_medium_ml, 3),
                "该步得到总量": _format_volume_ml(practical_intermediate_ml, 2),
                "备注": "1000× 中间母液；实验上可近似视作加到整数 mL",
            }
        )
    else:
        practical_intermediate_ml = 0.0

    step2_rows = []
    for chain in chains:
        final_targets_chain = chain["final_targets_nm"]
        working_targets_chain = chain["working_targets_nm"]
        for idx in range(1, len(final_targets_chain)):
            source_working_nm = working_targets_chain[idx - 1]
            target_final_nm = final_targets_chain[idx]
            target_working_nm = working_targets_chain[idx]
            usable_after_transfer_ml = (
                practical_tube_ml - propagation_take_ml
                if idx < len(final_targets_chain) - 1
                else practical_tube_ml
            )
            step2_rows.append(
                {
                    "步骤": "第 2 步",
                    "链": chain["chain_id"],
                    f"目标终浓度 ({unit_label})": target_final_nm / unit_to_nm,
                    f"对应工作液浓度 ({unit_label}, 2×)": target_working_nm / unit_to_nm,
                    "取液来源": f"上一管 ({_format_conc(source_working_nm / unit_to_nm)} {unit_label}, 2×)",
                    "取液操作": _format_volume_ul(propagation_take_ml * 1000, 0),
                    "预加培养基": _format_volume_ml(propagation_medium_ml, 1),
                    "该管配制总量": _format_volume_ml(practical_tube_ml, 2),
                    "预计加板可用量": _format_volume_ml(usable_after_transfer_ml, 2),
                    "备注": "严格 1:9 体积稀释",
                }
            )

    if has_zero:
        step2_rows.append(
            {
                "步骤": "第 2 步",
                "链": "Control",
                f"目标终浓度 ({unit_label})": 0,
                f"对应工作液浓度 ({unit_label}, 2×)": 0,
                "取液来源": "不加药",
                "取液操作": _format_volume_ul(0, 0),
                "预加培养基": _format_volume_ml(practical_tube_ml, 1),
                "该管配制总量": _format_volume_ml(practical_tube_ml, 2),
                "预计加板可用量": _format_volume_ml(practical_tube_ml, 2),
                "备注": "阴性/载体对照",
            }
        )

    plan = {
        "chain_summary": chain_summaries,
        "practical_tube_ml": practical_tube_ml,
        "reserve_ml": reserve_ml,
        "dead_volume_ml": dead_volume_ml,
        "target_volume_ml": target_volume_ml,
        "min_prep_volume_ml": min_prep_volume_ml,
        "propagation_take_ml": propagation_take_ml,
        "propagation_medium_ml": propagation_medium_ml,
        "step0_df": pd.DataFrame(step0_rows),
        "step1_df": pd.DataFrame(step1_rows),
        "step2_df": pd.DataFrame(step2_rows),
        "used_intermediate": use_intermediate,
        "intermediate_total_ml": practical_intermediate_ml,
        "total_intermediate_needed_ml": total_intermediate_needed_ml,
    }
    return plan, None


def calc_single(
    stock_mm,
    min_pipette,
    target_prep_vol,
    targets_text,
    work_conc_factor=1.0,
    unit_factor=1.0,
    unit_label="μM",
    max_dilution=10.0,
    work_label=None,
    uniform_dilution=True,
):
    if stock_mm <= 0:
        return None, "母液浓度必须大于 0", None
    if target_prep_vol <= 0:
        return None, "每管实验需用量必须大于 0", None
    if work_conc_factor <= 0:
        return None, "工作液倍数必须大于 0", None
    if unit_factor <= 0:
        return None, "浓度单位换算因子必须大于 0", None
    if max_dilution <= 0:
        return None, "最大稀释倍数必须大于 0", None

    try:
        raw_targets = targets_text.replace("，", ",").split(",")
        final_targets = sorted({float(x) for x in raw_targets if x.strip()}, reverse=True)
    except ValueError:
        return None, "请输入有效数字，注意单位换算", None

    has_zero = False
    if 0 in final_targets:
        final_targets.remove(0)
        has_zero = True

    if not final_targets and not has_zero:
        return None, "请输入至少一个目标浓度", None

    targets = [t * work_conc_factor * unit_factor for t in final_targets]
    stock_um = stock_mm * 1000
    if targets and targets[0] > stock_um:
        return None, "最高配液浓度高于母液浓度，无法配制", None

    results = []
    scale_notes = []
    large_step_notes = []
    downstream_transfer = 0.0

    for i in range(len(targets) - 1, -1, -1):
        current_c = targets[i]
        source_c = stock_um if i == 0 else targets[i - 1]
        dilution_factor = source_c / current_c
        source_name = "母液 Stock" if i == 0 else f"上一管 ({_format_conc(source_c / unit_factor)} {unit_label})"

        total_make_vol = target_prep_vol + downstream_transfer
        vol_take = (current_c * total_make_vol) / source_c
        note = ""

        if 0 < vol_take < min_pipette:
            total_make_vol = min_pipette * source_c / current_c
            vol_take = min_pipette
            note = " (已扩大体积以满足最小取样)"
            scale_notes.append(
                f"{_format_conc(current_c / work_conc_factor / unit_factor)} {unit_label}"
            )

        if dilution_factor > max_dilution:
            source_label = "母液 Stock" if i == 0 else f"{_format_conc(source_c / unit_factor)} {unit_label}"
            target_label = f"{_format_conc(current_c / unit_factor)} {unit_label}"
            large_step_notes.append(
                f"{source_label} → {target_label} = {dilution_factor:.2f}×"
            )

        vol_media = total_make_vol - vol_take
        final_reserve = total_make_vol - downstream_transfer

        results.append(
            {
                "conc": current_c,
                "source_c": source_c,
                "source_name": source_name,
                "is_stock": i == 0,
                "vol_take": vol_take,
                "vol_media": vol_media,
                "final_total": total_make_vol,
                "downstream_transfer": downstream_transfer,
                "final_reserve": final_reserve,
                "dilution_factor": dilution_factor,
                "note": note,
            }
        )
        downstream_transfer = vol_take

    results.reverse()

    rows = []
    work_label = work_label or f"{work_conc_factor:.0f}×"
    for res in results:
        final_conc = res["conc"] / work_conc_factor / unit_factor
        working_conc = res["conc"] / unit_factor
        media_ml = res["vol_media"] / 1000
        total_ml = res["final_total"] / 1000
        downstream_ml = res.get("downstream_transfer", 0) / 1000
        reserve_ml = res["final_reserve"] / 1000
        rows.append(
            {
                f"终浓度 ({unit_label})": final_conc,
                f"工作液浓度 ({unit_label}, {work_label})": working_conc,
                "取液来源": res["source_name"],
                "单步稀释倍数": f"{res['dilution_factor']:.2f}×",
                "取液操作 (μL)": f"{res['vol_take']:.2f}",
                "预加培养基 (mL)": f"{media_ml:.2f}",
                "该管配制总量 (mL)": f"{total_ml:.2f}{res['note']}",
                "给下游取走 (mL)": f"{downstream_ml:.2f}",
                "加板可用量 (mL)": f"{reserve_ml:.2f}",
            }
        )

    if has_zero:
        reserve_ml = target_prep_vol / 1000
        rows.append(
            {
                f"终浓度 ({unit_label})": 0,
                f"工作液浓度 ({unit_label}, {work_label})": 0,
                "取液来源": "不加药",
                "单步稀释倍数": "-",
                "取液操作 (μL)": "0",
                "预加培养基 (mL)": f"{reserve_ml:.2f}",
                "该管配制总量 (mL)": f"{reserve_ml:.2f}",
                "给下游取走 (mL)": "0.00",
                "加板可用量 (mL)": f"{reserve_ml:.2f}",
            }
        )

    notes = []
    if len(results) > 1:
        notes.append("当前按相邻高浓度 → 低浓度逐级连续稀释，不再跳级取样。")
    if scale_notes:
        notes.append(
            "以下浓度已自动扩大量程以满足最小取样量: "
            + ", ".join(scale_notes)
            + "。"
        )
    if large_step_notes:
        notes.append(
            f"以下单步稀释超过提醒阈值 {max_dilution:.2f}×，建议先配中间母液或重新设计梯度: "
            + "; ".join(large_step_notes)
            + "。"
        )

    return rows, None, " ".join(notes) if notes else None


def calc_practical_matrix_drug(
    stock_mm,
    min_pipette,
    targets,
    prep_factor,
    wells_per_conc,
    add_vol_ul,
    plates,
    dead_vol_ml,
    keep_reserve_ml,
    unit_label,
    unit_factor,
    max_dilution,
):
    if not targets:
        return None, "请提供至少一个梯度浓度", 0

    base_usage_ul = (wells_per_conc * add_vol_ul * plates) + (dead_vol_ml * 1000)
    target_prep_vol = base_usage_ul + keep_reserve_ml * 1000
    targets_text = ",".join(f"{t}" for t in targets)

    rows, error, notes = calc_single(
        stock_mm,
        min_pipette,
        target_prep_vol,
        targets_text,
        work_conc_factor=prep_factor,
        unit_factor=unit_factor,
        unit_label=unit_label,
        max_dilution=max_dilution,
        work_label=f"{prep_factor:.0f}×",
    )
    if error:
        return None, error, base_usage_ul / 1000
    if notes:
        rows = [dict(row, 备注=notes if idx == 0 else "") for idx, row in enumerate(rows)]

    return rows, None, target_prep_vol / 1000


def calc_combo_mix(
    stock_a_mm,
    stock_b_mm,
    min_pipette,
    targets_a,
    targets_b,
    prep_factor,
    target_prep_vol,
    unit_label,
    unit_factor,
):
    if len(targets_a) != len(targets_b):
        return None, "Combo 的 A/B 梯度数量不一致"
    if not targets_a:
        return None, "请提供至少一个 Combo 梯度"
    stock_um_a = stock_a_mm * 1000
    stock_um_b = stock_b_mm * 1000

    # 转为 μM 计算，输出再带单位
    prep_targets_a = [t * prep_factor * unit_factor for t in targets_a]
    prep_targets_b = [t * prep_factor * unit_factor for t in targets_b]

    transfer_needs = {c: 0 for c in prep_targets_a}
    results = []

    calc_data = []
    for i, conc_a in enumerate(prep_targets_a):
        conc_b = prep_targets_b[i]
        if conc_a == 0 and conc_b == 0:
            continue
        if i == 0:
            source_name = "Stock A + Stock B"
            source_c_a = stock_um_a
            source_c_b = stock_um_b
            is_top = True
        else:
            source_c_a = prep_targets_a[i - 1]
            source_c_b = prep_targets_b[i - 1]
            source_name = f"上一管 (A:{source_c_a / unit_factor:.2g}/{unit_label} B:{source_c_b / unit_factor:.2g})"
            is_top = False
        calc_data.append(
            {
                "conc_a": conc_a,
                "conc_b": conc_b,
                "source_c_a": source_c_a,
                "source_c_b": source_c_b,
                "source_name": source_name,
                "is_top": is_top,
            }
        )

    for i in range(len(calc_data) - 1, -1, -1):
        item = calc_data[i]
        conc_a = item["conc_a"]
        conc_b = item["conc_b"]
        source_c_a = item["source_c_a"]

        take_from_me = transfer_needs.get(conc_a, 0)
        total_make_vol = target_prep_vol + take_from_me

        note = ""
        if item["is_top"]:
            vol_take_a = (conc_a * total_make_vol) / stock_um_a
            vol_take_b = (conc_b * total_make_vol) / stock_um_b
            min_take = min(vol_take_a, vol_take_b)
            if min_take < min_pipette and min_take > 0:
                factor = min_pipette / min_take
                total_make_vol *= factor
                vol_take_a *= factor
                vol_take_b *= factor
                note = " (已扩大以满足母液取样)"
            vol_media = total_make_vol - vol_take_a - vol_take_b
            take_display = f"A:{vol_take_a:.2f} μL + B:{vol_take_b:.2f} μL"
        else:
            vol_take = (conc_a * total_make_vol) / source_c_a
            transfer_needs[source_c_a] = vol_take
            vol_media = total_make_vol - vol_take
            take_display = f"⬇️ {vol_take:.2f} μL"

        final_reserve = total_make_vol - take_from_me

        item.update(
            {
                "vol_media": vol_media,
                "final_total": total_make_vol,
                "final_reserve": final_reserve,
                "take_display": take_display,
                "note": note,
            }
        )
        results.append(item)

    results.reverse()

    rows = []
    work_label = f"{prep_factor:.0f}×"
    for res in results:
        media_ml = _round_ml_step(res["vol_media"])
        total_ml = _round_ml_step(res["final_total"])
        reserve_ml = _round_ml_step(res["final_reserve"])
        rows.append(
            {
                f"A终浓度 ({unit_label})": res["conc_a"] / prep_factor / unit_factor,
                f"B终浓度 ({unit_label})": res["conc_b"] / prep_factor / unit_factor,
                f"管内浓度 ({unit_label}, {work_label})": f"A:{res['conc_a']/unit_factor:.2g}; B:{res['conc_b']/unit_factor:.2g}",
                "取液来源": res["source_name"],
                "取液操作": res["take_display"],
                "预加培养基 (mL)": f"{media_ml:.2f}",
                "该管总量 (mL)": f"{total_ml:.2f}{res['note']}",
                "预计剩余 (mL)": f"{reserve_ml:.2f}",
            }
        )

    reserve_ml = _round_ml_step(target_prep_vol)
    rows.append(
        {
            f"A终浓度 ({unit_label})": 0,
            f"B终浓度 ({unit_label})": 0,
            f"管内浓度 ({unit_label}, {work_label})": "0",
            "取液来源": "-",
            "取液操作": "0",
            "预加培养基 (mL)": f"{reserve_ml:.2f}",
            "该管总量 (mL)": f"{reserve_ml:.2f}",
            "预计剩余 (mL)": f"{reserve_ml:.2f}",
        }
    )

    return rows, None, target_prep_vol / 1000


st.set_page_config(
    page_title="MTT 实验全能助手",
    page_icon="🧪",
    layout="centered",
)

st.title("MTT 实验全能助手 (计数 + 配液)")
st.caption("基于 Streamlit 的手机友好版本，输入参数后点击按钮即可获得配液方案。")

(tab1, tab2, tab3, tab4) = st.tabs(
    ["1. 细胞计数与铺板", "2. 单药梯度配制", "3. 双药混合配制(A+B)", "4. 三药协同 (Combo+C)"]
)

with tab1:
    st.subheader("细胞计数与铺板")
    mtt_timepoint = st.selectbox(
        "MTT 时间点",
        options=["72 h", "Day 5"],
        index=0,
        help="72 h 默认 2000 cells/well；Day 5 默认 1000 cells/well。",
    )
    default_target_cell = 2000.0 if mtt_timepoint == "72 h" else 1000.0
    with st.form("seed_form"):
        st.markdown("**细胞计数计算器**")
        count_num = st.number_input(
            "计数板总细胞数",
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.0f",
        )
        count_squares = st.number_input(
            "计数的格数 (大格)",
            min_value=1.0,
            value=4.0,
            step=1.0,
            format="%.0f",
        )
        dilution_factor = st.selectbox(
            "计数前稀释倍数",
            options=[1, 2, 5, 10, 20],
            index=0,
        )
        st.caption("如: 太浓了稀释 10 倍后计数则填 10")

        st.markdown("**铺板需求**")
        target_cell_per_well = st.number_input(
            "目标每孔细胞数 (个)",
            min_value=0.0,
            value=default_target_cell,
            step=100.0,
            key=f"target_cell_per_well_{mtt_timepoint}",
        )
        well_vol_ml = st.number_input(
            "每孔体积 (mL)",
            min_value=0.0,
            value=0.09,
            step=0.01,
            format="%.2f",
        )
        wells_per_plate = st.number_input(
            "每个细胞系实际使用孔数",
            min_value=1.0,
            max_value=96.0,
            value=16.0,
            step=1.0,
            format="%.0f",
        )
        plate_num = st.number_input(
            "计划细胞系/板数",
            min_value=1.0,
            value=1.0,
            step=1.0,
            format="%.0f",
        )
        seed_safety = st.number_input(
            "配液余量 (mL)",
            min_value=0.0,
            value=0.6,
            step=0.1,
            format="%.1f",
        )
        st.caption("按新 protocol：每个细胞系 8 个条件 × 2 复孔 = 16 wells；每孔 90 μL，实际建议每个细胞系配约 2 mL。")
        seed_submit = st.form_submit_button("计算铺板方案")

    if seed_submit:
        result, error = calc_seeding(
            count_num,
            count_squares,
            float(dilution_factor),
            target_cell_per_well,
            well_vol_ml,
            plate_num,
            seed_safety,
            wells_per_plate,
        )
        if error:
            st.error(error)
        else:
            st.code(result, language="text")

with tab2:
    st.subheader("单药梯度配制")
    st.caption("新 protocol：90 μL cell suspension + 90 μL 2× drug medium；final volume = 180 μL/well。按平行 10× 稀释链生成可操作的配液表。")
    with st.form("single_form"):
        st.markdown("**母液与限制**")
        s1_stock = st.number_input(
            "药物母液浓度 (mM)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            format="%.2f",
        )
        min_pipette = st.number_input(
            "母液最小取样量 (μL)",
            min_value=0.0,
            value=2.0,
            step=0.5,
            format="%.2f",
        )

        st.markdown("**孔板与体积设置**")
        s1_add_vol = st.number_input(
            "每孔加药体积 (μL) - 推荐 90 μL",
            min_value=0.0,
            value=90.0,
            step=5.0,
        )
        st.caption("默认按 90 μL 细胞悬液 + 90 μL 2× 工作液 (总 180 μL) 计算；如体系不同，可调整数值。")

        s1_cell_lines_per_plate = st.number_input(
            "每块板细胞系数",
            min_value=1.0,
            value=3.0,
            step=1.0,
            format="%.0f",
        )
        s1_replicates = st.number_input(
            "technical repeats",
            min_value=1.0,
            value=2.0,
            step=1.0,
            format="%.0f",
        )
        s1_control_reps = int(s1_cell_lines_per_plate * s1_replicates)
        s1_plate_num = st.number_input(
            "需要的板子数量",
            min_value=1.0,
            value=1.0,
            step=1.0,
            format="%.0f",
        )
        s1_extra_ratio = st.number_input(
            "额外预留比例 (%)",
            min_value=0.0,
            value=0.0,
            step=5.0,
            format="%.0f",
        )
        st.caption("按 protocol：每个浓度每块板 3 个细胞系 × 2 孔 = 6 wells；理论 540 μL，默认每浓度配 650 μL/plate。")

        st.markdown("**浓度梯度设置 - 自动按高到低稀释**")
        s1_unit = st.selectbox(
            "浓度单位",
            options=["nM", "μM", "mM"],
            index=0,
            help="选择目标终浓度的单位，程序会自动换算到 μM 计算",
        )
        s1_targets = st.text_input(
            "输入目标浓度 (逗号分隔)",
            value="0, 1, 3, 10, 30, 100, 300, 1000",
        )

        wells_per_conc_per_plate = s1_cell_lines_per_plate * s1_replicates
        base_needed = s1_add_vol * wells_per_conc_per_plate * s1_plate_num
        protocol_min = 650.0 * s1_plate_num
        suggest_min = max(base_needed * (1 + s1_extra_ratio / 100), protocol_min)
        s1_plan_vol = st.number_input(
            "每管希望最终至少保留体积 (μL)",
            min_value=0.0,
            value=float(int(suggest_min) if suggest_min > 0 else 0),
            step=50.0,
            help="程序会先加上固定 1.5 mL 排枪死体积，再按 2/3/4/5/10/15/20 mL 这些标准总量自动匹配最省料的整管体积。",
        )
        s1_max_dilution = st.number_input(
            "强制生成中间母液阈值 (倍数)",
            min_value=1.0,
            value=100.0,
            step=10.0,
            help="当母液与最高工作液的倍率超过该阈值时，强制先生成 1000× 中间母液。",
        )

        single_submit = st.form_submit_button("生成平行 10× 稀释方案")

    if single_submit:
        targets_text = s1_targets
        if "0" not in [x.strip() for x in s1_targets.replace("，", ",").split(",")]:
            if s1_control_reps > 0:
                targets_text = f"{s1_targets},0"

        extra_factor = 1 + s1_extra_ratio / 100
        theoretical_need = s1_add_vol * wells_per_conc_per_plate * s1_plate_num
        recommended_need = max(theoretical_need * extra_factor, protocol_min)

        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        unit_factor = unit_factor_map.get(s1_unit, 1.0)

        try:
            raw_targets = targets_text.replace("，", ",").split(",")
            parsed_targets = [float(x) for x in raw_targets if x.strip()]
        except ValueError:
            parsed_targets = []

        non_zero_targets = [t for t in parsed_targets if t != 0]
        has_zero = any(t == 0 for t in parsed_targets)
        total_wells = len(non_zero_targets) * wells_per_conc_per_plate * s1_plate_num
        control_wells = (s1_control_reps * s1_plate_num) if has_zero else 0
        total_wells += control_wells

        effective_target_vol = max(recommended_need, s1_plan_vol)
        shortage_warning = s1_plan_vol < recommended_need

        plan, error = calc_single_dual_chain(
            s1_stock,
            min_pipette,
            effective_target_vol,
            targets_text,
            unit_label=s1_unit,
            unit_to_nm=unit_factor * 1000,
            work_conc_factor=2.0,
            trigger_ratio=s1_max_dilution,
        )
        if error:
            st.error(error)
        elif plan:
            st.caption(
                f"理论最低 {theoretical_need:.1f} μL；含预留 {s1_extra_ratio:.0f}% 建议至少 {recommended_need:.1f} μL；"
                f"本次按 {effective_target_vol:.1f} μL 作为每个浓度最终加板可用量计算。"
                f"总共覆盖 {total_wells:.0f} 个孔"
                + (
                    f"，其中 0 {s1_unit} 阴性对照 {control_wells:.0f} 孔"
                    if control_wells
                    else ""
                )
            )
            st.caption(
                f"系统已拆分为 {len(plan['chain_summary'])} 条平行 10× 稀释链；"
                f"V_plate={plan['reserve_ml']:.2f} mL，固定 dead volume={plan['dead_volume_ml']:.2f} mL，"
                f"因此需保留 {plan['target_volume_ml']:.2f} mL；理论最小起配体积 {plan['min_prep_volume_ml']:.2f} mL，"
                f"最终匹配到 {plan['practical_tube_ml']:.1f} mL 标准总量。"
            )
            st.info("识别到的稀释链： " + " | ".join(plan["chain_summary"]))
            if shortage_warning:
                st.warning(
                    "您输入的最终保留体积小于建议值，已自动使用建议值参与整管体积规划。"
                )
            if plan["used_intermediate"]:
                st.markdown("**[第 0 步] 中间母液配制**")
                st.dataframe(plan["step0_df"], width="stretch", hide_index=True)
                st.caption(
                    f"链头合计理论需要中间母液 {plan['total_intermediate_needed_ml']:.2f} mL；"
                    f"本次按 {plan['intermediate_total_ml']:.2f} mL 中间母液规划。"
                )
                st.divider()

            st.markdown("**[第 1 步] 链源头配制**")
            st.dataframe(plan["step1_df"], width="stretch", hide_index=True)
            st.caption(
                f"链头母管先配好；如果该链后面还有更低浓度，会预留 {plan['propagation_take_ml']:.2f} mL 继续往下做 10× 稀释。"
            )
            st.divider()

            st.markdown("**[第 2 步] 平行 10 倍稀释**")
            st.dataframe(plan["step2_df"], width="stretch", hide_index=True)
            st.caption(
                f"这里统一使用 1:9 体积稀释逻辑；当前总量 {plan['practical_tube_ml']:.1f} mL，"
                f"因此每步都是取 {plan['propagation_take_ml'] * 1000:.0f} μL 上一级 + {plan['propagation_medium_ml']:.2f} mL 培养基。"
            )
        else:
            st.info("暂无有效结果")

with tab3:
    st.subheader("双药联合矩阵 (Checkerboard) - 4× 配液管")
    st.caption(
        "按照 90 μL 细胞 + 45 μL 药A + 45 μL 药B 的常见 180 μL 体系设计，"
        "配液管浓度默认为终浓度的 4×。"
    )

    with st.form("matrix_form"):
        st.markdown("**体系与体积**")
        m_cell_vol = st.number_input("孔内细胞体积 (μL)", min_value=0.0, value=90.0, step=5.0)
        m_add_a = st.number_input("每孔加药A体积 (μL)", min_value=0.0, value=45.0, step=1.0)
        m_add_b = st.number_input("每孔加药B体积 (μL)", min_value=0.0, value=45.0, step=1.0)

        st.markdown("**矩阵与用量**")
        m_rows = st.number_input("矩阵行数 (A 梯度数)", min_value=2, value=6, step=1)
        m_cols = st.number_input("矩阵列数 (B 梯度数)", min_value=2, value=6, step=1)
        m_reps = st.number_input("每组合复孔数", min_value=1, value=2, step=1, format="%.0f")
        m_plates = st.number_input("板子数量", min_value=1, value=7, step=1, format="%.0f")
        m_keep_reserve = st.number_input(
            "希望每管至少保留安全余量 (mL)",
            min_value=0.0,
            value=1.0,
            step=0.5,
            help="这是做完所有板、扣除传递后仍希望留在该管中的安全余量，不需要丢弃。",
        )

        st.markdown("**浓度梯度**")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            m_stock_a = st.number_input("药A 母液 (mM)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        with c2:
            m_high_a = st.number_input("药A 最高浓度", min_value=0.0, value=1000.0, step=10.0)
        with c3:
            m_fold_a = st.number_input("药A 梯度倍数", min_value=1.0, value=4.0, step=0.5)
        with c4:
            m_unit_a = st.selectbox("药A 单位", options=["nM", "μM", "mM"], index=0)

        d1, d2, d3, d4 = st.columns(4)
        with d1:
            m_stock_b = st.number_input("药B 母液 (mM)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        with d2:
            m_high_b = st.number_input("药B 最高浓度", min_value=0.0, value=1000.0, step=10.0)
        with d3:
            m_fold_b = st.number_input("药B 梯度倍数", min_value=1.0, value=4.0, step=0.5)
        with d4:
            m_unit_b = st.selectbox("药B 单位", options=["nM", "μM", "mM"], index=0)

        m_min_pipette = st.number_input("母液最小取样量 (μL)", min_value=0.0, value=2.0, step=0.5, format="%.1f")
        m_max_dilution = st.number_input(
            "单步最大稀释倍数提醒", min_value=1.0, value=10.0, step=1.0, help="仅用于提醒某一步稀释是否过大；当前算法始终按相邻高浓度逐级连续稀释。"
        )

        matrix_submit = st.form_submit_button("生成 Checkerboard 配液方案")

    if matrix_submit:
        total_vol = m_cell_vol + m_add_a + m_add_b
        prep_factor = total_vol / m_add_a if m_add_a > 0 else 0
        prep_factor_b = total_vol / m_add_b if m_add_b > 0 else 0
        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        unit_factor_a = unit_factor_map.get(m_unit_a, 1.0)
        unit_factor_b = unit_factor_map.get(m_unit_b, 1.0)

        targets_a = [m_high_a / (m_fold_a ** i) for i in range(max(int(m_rows) - 1, 1))]
        targets_a.append(0)
        targets_b = [m_high_b / (m_fold_b ** i) for i in range(max(int(m_cols) - 1, 1))]
        targets_b.append(0)

        wells_for_a = m_cols * m_reps
        wells_for_b = m_rows * m_reps

        rows_a, err_a, need_a = calc_practical_matrix_drug(
            m_stock_a,
            m_min_pipette,
            targets_a,
            prep_factor,
            wells_for_a,
            m_add_a,
            m_plates,
            dead_vol_ml=0.0,
            keep_reserve_ml=m_keep_reserve,
            unit_label=m_unit_a,
            unit_factor=unit_factor_a,
            max_dilution=m_max_dilution,
        )
        rows_b, err_b, need_b = calc_practical_matrix_drug(
            m_stock_b,
            m_min_pipette,
            targets_b,
            prep_factor_b,
            wells_for_b,
            m_add_b,
            m_plates,
            dead_vol_ml=0.0,
            keep_reserve_ml=m_keep_reserve,
            unit_label=m_unit_b,
            unit_factor=unit_factor_b,
            max_dilution=m_max_dilution,
        )

        st.markdown(
            f"终体积约 {total_vol:.1f} μL/孔；药A管浓度 {prep_factor:.2f}×，药B管浓度 {prep_factor_b:.2f}×。"
        )

        if err_a:
            st.error(f"药A: {err_a}")
        elif rows_a:
            st.success(f"药A：理论用量约 {need_a:.2f} mL (含保留体积)")
            st.dataframe(rows_a, width="stretch")

        st.markdown("---")

        if err_b:
            st.error(f"药B: {err_b}")
        elif rows_b:
            st.success(f"药B：理论用量约 {need_b:.2f} mL (含保留体积)")
            st.dataframe(rows_b, width="stretch")

with tab4:
    st.subheader("三药协同 (Combo A+B 与 Drug C) - 4× 组装")
    st.caption("Combo 管和 C 管分别按照 4× 逻辑配制，组合 45 μL + 45 μL + 90 μL 细胞。")

    with st.form("combo_form"):
        st.markdown("**体系与体积**")
        c_cell_vol = st.number_input("孔内细胞体积 (μL)", min_value=0.0, value=90.0, step=5.0)
        c_combo_vol = st.number_input("每孔 Combo (A+B) 体积 (μL)", min_value=0.0, value=45.0, step=1.0)
        c_c_vol = st.number_input("每孔 Drug C 体积 (μL)", min_value=0.0, value=45.0, step=1.0)

        total_combo_factor = (c_cell_vol + c_combo_vol + c_c_vol) / c_combo_vol if c_combo_vol else 0
        total_c_factor = (c_cell_vol + c_combo_vol + c_c_vol) / c_c_vol if c_c_vol else 0
        st.caption(
            f"Combo 管按 {total_combo_factor:.1f}× 配制；Drug C 管按 {total_c_factor:.1f}× 配制。"
        )

        st.markdown("**矩阵与用量**")
        c_rows = st.number_input("Combo 梯度数 (行)", min_value=2, value=6, step=1)
        c_cols = st.number_input("Drug C 梯度数 (列)", min_value=2, value=6, step=1)
        c_reps = st.number_input("复孔数", min_value=1, value=2, step=1, format="%.0f")
        c_plates = st.number_input("板子数量", min_value=1, value=7, step=1, format="%.0f")
        c_keep_reserve = st.number_input(
            "希望每管至少保留安全余量 (mL)",
            min_value=0.0,
            value=1.0,
            step=0.5,
            help="这是配完所有板、完成传递后仍希望留在管中的安全余量，不需要丢弃。",
        )
        c_min_pipette = st.number_input("母液最小取样量 (μL)", min_value=0.0, value=2.0, step=0.5, format="%.1f")
        c_max_dilution = st.number_input(
            "单步最大稀释倍数",
            min_value=1.0,
            value=10.0,
            step=1.0,
            help="控制跳跃稀释上限，避免过多中间管。",
        )

        st.markdown("**Combo (A+B) 设置**")
        ca1, ca2, ca3, ca4 = st.columns(4)
        with ca1:
            c_stock_a = st.number_input("药A 母液 (mM)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        with ca2:
            c_high_a = st.number_input("药A 最高终浓度", min_value=0.0, value=1000.0, step=10.0)
        with ca3:
            c_stock_b = st.number_input("药B 母液 (mM)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        with ca4:
            c_high_b = st.number_input("药B 最高终浓度", min_value=0.0, value=500.0, step=10.0)

        cb1, cb2 = st.columns(2)
        with cb1:
            c_fold_combo = st.number_input("Combo 稀释倍数", min_value=1.0, value=4.0, step=0.5)
        with cb2:
            c_unit_combo = st.selectbox("Combo 单位", options=["nM", "μM", "mM"], index=0)

        st.markdown("**Drug C 设置**")
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1:
            c_stock_c = st.number_input("Drug C 母液 (mM)", min_value=0.0, value=10.0, step=0.5, format="%.2f")
        with cc2:
            c_high_c = st.number_input("Drug C 最高终浓度", min_value=0.0, value=2000.0, step=20.0)
        with cc3:
            c_fold_c = st.number_input("Drug C 稀释倍数", min_value=1.0, value=4.0, step=0.5)
        with cc4:
            c_unit_c = st.selectbox("Drug C 单位", options=["nM", "μM", "mM"], index=0)

        combo_submit = st.form_submit_button("生成 Combo + C 配液方案")

    if combo_submit:
        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        unit_factor_combo = unit_factor_map.get(c_unit_combo, 1.0)
        unit_factor_c = unit_factor_map.get(c_unit_c, 1.0)

        targets_a = [c_high_a / (c_fold_combo ** i) for i in range(max(int(c_rows) - 1, 1))]
        targets_a.append(0)
        targets_b = [c_high_b / (c_fold_combo ** i) for i in range(max(int(c_rows) - 1, 1))]
        targets_b.append(0)
        targets_c = [c_high_c / (c_fold_c ** i) for i in range(max(int(c_cols) - 1, 1))]
        targets_c.append(0)

        wells_combo = c_cols * c_reps * c_plates
        wells_c = c_rows * c_reps * c_plates

        base_combo_ul = (wells_combo * c_combo_vol) + 0
        base_c_ul = (wells_c * c_c_vol) + 0
        target_combo_vol = base_combo_ul + c_keep_reserve * 1000
        target_c_vol = base_c_ul + c_keep_reserve * 1000

        rows_combo, err_combo, need_combo = calc_combo_mix(
            c_stock_a,
            c_stock_b,
            c_min_pipette,
            targets_a,
            targets_b,
            total_combo_factor,
            target_combo_vol,
            c_unit_combo,
            unit_factor_combo,
        )

        targets_c_text = ",".join(str(t) for t in targets_c)
        rows_c, err_c, notes_c = calc_single(
            c_stock_c,
            c_min_pipette,
            target_c_vol,
            targets_c_text,
            work_conc_factor=total_c_factor,
            unit_factor=unit_factor_c,
            unit_label=c_unit_c,
            max_dilution=c_max_dilution,
            work_label=f"{total_c_factor:.0f}×",
        )

        st.markdown(
            f"终体积 {c_cell_vol + c_combo_vol + c_c_vol:.1f} μL/孔；Combo 管 {total_combo_factor:.1f}×，Drug C 管 {total_c_factor:.1f}×。"
        )

        if err_combo:
            st.error(err_combo)
        elif rows_combo:
            st.success(f"Combo：理论用量约 {need_combo:.2f} mL (含保留体积)")
            st.dataframe(rows_combo, width="stretch")

        st.markdown("---")

        if err_c:
            st.error(err_c)
        elif rows_c:
            st.success(f"Drug C：理论用量约 {target_c_vol/1000:.2f} mL (含保留体积)")
            if notes_c:
                st.warning(notes_c)
            st.dataframe(rows_c, width="stretch")
