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


def calc_single(stock_mm, min_pipette, needed_vol, targets_text):
    if stock_mm <= 0:
        return None, "母液浓度必须大于 0"
    if needed_vol <= 0:
        return None, "每管实验需用量必须大于 0"

    try:
        raw_targets = targets_text.replace("，", ",").split(",")
        targets = sorted({float(x) for x in raw_targets if x.strip()}, reverse=True)
    except ValueError:
        return None, "请输入有效数字，注意单位换算"

    has_zero = False
    if 0 in targets:
        targets.remove(0)
        has_zero = True

    if not targets and not has_zero:
        return None, "请输入至少一个目标浓度"

    stock_um = stock_mm * 1000

    transfer_needs = {t: 0 for t in targets}
    results = []

    calc_data = []
    for i, current_c in enumerate(targets):
        is_highest = i == 0
        if is_highest:
            source_c = stock_um
            source_name = "母液 Stock"
        else:
            source_c = targets[i - 1]
            source_name = f"上一管 ({source_c} μM)"
        calc_data.append(
            {
                "conc": current_c,
                "source_c": source_c,
                "source_name": source_name,
                "is_stock": is_highest,
            }
        )

    for i in range(len(calc_data) - 1, -1, -1):
        item = calc_data[i]
        conc = item["conc"]
        source_c = item["source_c"]

        total_make_vol = needed_vol + transfer_needs.get(conc, 0)
        vol_take = (conc * total_make_vol) / source_c

        if item["is_stock"] and vol_take < min_pipette:
            factor = min_pipette / vol_take
            vol_take = min_pipette
            total_make_vol = total_make_vol * factor
            note = " (已扩大体积以满足母液取样)"
        else:
            note = ""

        if not item["is_stock"]:
            transfer_needs[source_c] = vol_take

        vol_media = total_make_vol - vol_take

        item.update(
            {
                "vol_take": vol_take,
                "vol_media": vol_media,
                "final_total": total_make_vol,
                "note": note,
            }
        )
        results.append(item)

    results.reverse()

    rows = []
    for res in results:
        rows.append(
            {
                "目标浓度 (μM)": res["conc"],
                "取液来源": res["source_name"],
                "取液体积 (μL)": f"{res['vol_take']:.2f}",
                "加培养基 (μL)": f"{res['vol_media']:.1f}",
                "该管配制总量 (μL)": f"{res['final_total']:.1f}{res['note']}",
            }
        )

    if has_zero:
        rows.append(
            {
                "目标浓度 (μM)": 0,
                "取液来源": "不加药",
                "取液体积 (μL)": "0",
                "加培养基 (μL)": f"{needed_vol:.1f}",
                "该管配制总量 (μL)": f"{needed_vol:.1f}",
            }
        )

    return rows, None


def calc_double(stock_a_mm, stock_b_mm, total_vol, content):
    if stock_a_mm <= 0 or stock_b_mm <= 0:
        return None, "母液浓度必须大于 0"
    if total_vol <= 0:
        return None, "每管配制体积必须大于 0"

    stock_a_um = stock_a_mm * 1000
    stock_b_um = stock_b_mm * 1000

    content = content.strip()
    if not content:
        return [], None

    rows = []
    for line in content.split("\n"):
        line = line.replace("，", ",").strip()
        if not line or "," not in line:
            continue

        parts = line.split(",")
        if len(parts) < 2:
            continue

        try:
            target_a = float(parts[0].strip())
            target_b = float(parts[1].strip())
        except ValueError:
            continue

        vol_a = (target_a * total_vol) / stock_a_um
        vol_b = (target_b * total_vol) / stock_b_um
        vol_media = total_vol - vol_a - vol_b

        if vol_media < 0:
            rows.append(
                {
                    "药A终浓度 (μM)": target_a,
                    "药B终浓度 (μM)": target_b,
                    "取药A (μL)": "Error",
                    "取药B (μL)": "Error",
                    "加培养基 (μL)": "浓度过高(母液不足)",
                }
            )
        else:
            rows.append(
                {
                    "药A终浓度 (μM)": target_a,
                    "药B终浓度 (μM)": target_b,
                    "取药A (μL)": f"{vol_a:.3f}",
                    "取药B (μL)": f"{vol_b:.3f}",
                    "加培养基 (μL)": f"{vol_media:.1f}",
                }
            )

    return rows, None


st.set_page_config(
    page_title="MTT 实验全能助手",
    page_icon="🧪",
    layout="centered",
)

st.title("MTT 实验全能助手 (计数 + 配液)")
st.caption("基于 Streamlit 的手机友好版本，输入参数后点击按钮即可获得配液方案。")

(tab1, tab2, tab3) = st.tabs(
    ["1. 细胞计数与铺板", "2. 单药梯度配制", "3. 双药混合配制(A+B)"]
)

with tab1:
    st.subheader("细胞计数与铺板")
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
            value=5000.0,
            step=100.0,
        )
        well_vol_ml = st.number_input(
            "每孔体积 (mL)",
            min_value=0.0,
            value=0.09,
            step=0.01,
            format="%.2f",
        )
        wells_per_plate = st.number_input(
            "每块实际使用孔数",
            min_value=1.0,
            max_value=96.0,
            value=72.0,
            step=1.0,
            format="%.0f",
        )
        plate_num = st.number_input(
            "计划铺板数量 (块)",
            min_value=1.0,
            value=1.0,
            step=1.0,
            format="%.0f",
        )
        seed_safety = st.number_input(
            "配液余量 (mL)",
            min_value=0.0,
            value=2.0,
            step=0.5,
            format="%.1f",
        )
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

        st.markdown("**体积设置**")
        s1_needed_vol = st.number_input(
            "每管实验需用量 (μL)",
            min_value=0.0,
            value=1000.0,
            step=10.0,
        )
        st.caption("程序会自动计算所需的额外传递体积")

        st.markdown("**浓度梯度设置 (μM) - 自动按高到低稀释**")
        s1_targets = st.text_input(
            "输入目标浓度 (逗号分隔)",
            value="0, 1, 5, 10, 50, 100",
        )

        single_submit = st.form_submit_button("计算连续稀释方案")

    if single_submit:
        rows, error = calc_single(s1_stock, min_pipette, s1_needed_vol, s1_targets)
        if error:
            st.error(error)
        elif rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("暂无有效结果")

with tab3:
    st.subheader("双药混合配制 (A+B)")
    st.warning("此模式用于计算单孔/单管中同时加入药A和药B (如 Synergy Matrix)")

    if "matrix_input" not in st.session_state:
        st.session_state.matrix_input = "0, 0\n10, 0\n0, 20\n10, 20\n5, 50\n"

    if st.button("清空列表"):
        st.session_state.matrix_input = ""

    with st.form("double_form"):
        st.markdown("**母液设置 (输入 mM，计算自动转为 μM)**")
        d_stock_a = st.number_input(
            "药A 母液 (mM)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            format="%.2f",
        )
        d_stock_b = st.number_input(
            "药B 母液 (mM)",
            min_value=0.0,
            value=10.0,
            step=0.1,
            format="%.2f",
        )
        d_total_vol = st.number_input(
            "每管配制体积 (μL)",
            min_value=0.0,
            value=1000.0,
            step=10.0,
        )

        st.markdown("**Matrix 浓度组合清单 (μM)**")
        st.caption("输入格式：药A浓度, 药B浓度 (一行一个组合)；可从 Excel 直接粘贴。")
        matrix_input = st.text_area(
            "浓度组合",
            key="matrix_input",
            height=200,
        )

        double_submit = st.form_submit_button("计算 Matrix 配液方案")

    if double_submit:
        rows, error = calc_double(d_stock_a, d_stock_b, d_total_vol, matrix_input)
        if error:
            st.error(error)
        elif rows:
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("暂无有效结果")
