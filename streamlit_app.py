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
):
    if stock_mm <= 0:
        return None, "母液浓度必须大于 0"
    if target_prep_vol <= 0:
        return None, "每管实验需用量必须大于 0"
    if work_conc_factor <= 0:
        return None, "工作液倍数必须大于 0"
    if unit_factor <= 0:
        return None, "浓度单位换算因子必须大于 0"
    if max_dilution <= 0:
        return None, "最大稀释倍数必须大于 0"

    try:
        raw_targets = targets_text.replace("，", ",").split(",")
        final_targets = sorted({float(x) for x in raw_targets if x.strip()}, reverse=True)
    except ValueError:
        return None, "请输入有效数字，注意单位换算"

    has_zero = False
    if 0 in final_targets:
        final_targets.remove(0)
        has_zero = True

    if not final_targets and not has_zero:
        return None, "请输入至少一个目标浓度"

    targets = [t * work_conc_factor * unit_factor for t in final_targets]
    stock_um = stock_mm * 1000

    transfer_needs = {t: 0 for t in targets}
    results = []

    calc_data = []
    # 智能选择来源：优先选稀释倍数最大但<max的
    for i, current_c in enumerate(targets):
        is_highest = i == 0
        if is_highest:
            source_c = stock_um
            source_name = "母液 Stock"
        else:
            best_source = None
            best_factor = 0
            for candidate in targets[:i]:
                factor = candidate / current_c
                if factor <= max_dilution and factor > best_factor:
                    best_source = candidate
                    best_factor = factor
            if best_source is None:
                best_source = targets[i - 1]
                best_factor = best_source / current_c
            source_c = best_source
            source_name = f"上一管 ({source_c / unit_factor:.3g} {unit_label})，稀释 {best_factor:.2f}×"
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

        take_from_me = transfer_needs.get(conc, 0)
        total_make_vol = target_prep_vol + take_from_me
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
        final_reserve = total_make_vol - take_from_me

        item.update(
            {
                "vol_take": vol_take,
                "vol_media": vol_media,
                "final_total": total_make_vol,
                "final_reserve": final_reserve,
                "note": note,
            }
        )
        results.append(item)

    results.reverse()

    rows = []
    work_label = work_label or f"{work_conc_factor:.0f}×"
    for res in results:
        final_conc = res["conc"] / work_conc_factor / unit_factor
        working_conc = res["conc"] / unit_factor
        rows.append(
            {
                f"终浓度 ({unit_label})": final_conc,
                f"工作液浓度 ({unit_label}, {work_label})": working_conc,
                "取液来源": res["source_name"],
                "取液体积 (μL)": f"{res['vol_take']:.2f}",
                "加培养基 (μL)": f"{res['vol_media']:.1f}",
                "该管配制总量 (μL)": f"{res['final_total']:.1f}{res['note']}",
                "预计剩余 (μL)": f"{res['final_reserve']:.1f}",
            }
        )

    if has_zero:
        rows.append(
            {
                f"终浓度 ({unit_label})": 0,
                f"工作液浓度 ({unit_label}, {work_label})": 0,
                "取液来源": "不加药",
                "取液体积 (μL)": "0",
                "加培养基 (μL)": f"{target_prep_vol:.1f}",
                "该管配制总量 (μL)": f"{target_prep_vol:.1f}",
                "预计剩余 (μL)": f"{target_prep_vol:.1f}",
            }
        )

    return rows, None


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

    rows, error = calc_single(
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
        rows.append(
            {
                f"A终浓度 ({unit_label})": res["conc_a"] / prep_factor / unit_factor,
                f"B终浓度 ({unit_label})": res["conc_b"] / prep_factor / unit_factor,
                f"管内浓度 ({unit_label}, {work_label})": f"A:{res['conc_a']/unit_factor:.2g}; B:{res['conc_b']/unit_factor:.2g}",
                "取液来源": res["source_name"],
                "取液操作": res["take_display"],
                "加培养基 (μL)": f"{res['vol_media']:.1f}",
                "该管总量 (μL)": f"{res['final_total']:.1f}{res['note']}",
                "预计剩余 (μL)": f"{res['final_reserve']:.1f}",
            }
        )

    rows.append(
        {
            f"A终浓度 ({unit_label})": 0,
            f"B终浓度 ({unit_label})": 0,
            f"管内浓度 ({unit_label}, {work_label})": "0",
            "取液来源": "-",
            "取液操作": "0",
            "加培养基 (μL)": f"{target_prep_vol:.1f}",
            "该管总量 (μL)": f"{target_prep_vol:.1f}",
            "预计剩余 (μL)": f"{target_prep_vol:.1f}",
        }
    )

    return rows, None, target_prep_vol / 1000


# ================== 界面部分 ==================

st.set_page_config(
    page_title="MTT 实验全能助手",
    page_icon="🧪",
    layout="centered",
)

# 标题移到 Tab 之前
st.title("MTT 实验全能助手 (计数 + 配液)")
st.caption("基于 Streamlit 的手机友好版本，输入参数后点击按钮即可获得配液方案。")

(tab1, tab2, tab3, tab4) = st.tabs(
    ["1. 细胞计数与铺板", "2. 单药梯度配制", "3. 双药混合配制(A+B)", "4. 三药协同 (Combo+C)"]
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
        st.markdown("**1. 基础信息**")
        s1_stock = st.number_input("药物母液浓度 (mM)", value=10.0, step=0.1, format="%.2f")
        s1_min_pipette = st.number_input("母液最小取样量 (μL)", value=2.0, step=0.5)

        st.markdown("**2. 浓度梯度 (高→低)**")
        # 默认单位设为 nM (index=0)
        s1_unit = st.selectbox("单位", options=["nM", "μM", "mM"], index=0)
        s1_targets = st.text_input("输入目标浓度 (逗号分隔)", value="100, 50, 10, 5, 1, 0")
        
        st.markdown("**3. 配液保留量**")
        s1_plan_vol = st.number_input(
            "每管做完后至少保留 (μL)", 
            value=6000.0, 
            step=500.0,
            help="稀释完成后，每管里剩下的液体体积 (程序会自动倒推计算第一管需要配多少才够)。"
        )
        
        # 将复孔、板数等参数折叠隐藏
        with st.expander("⚙️ 更多参数设置 (点击展开)"):
            s1_add_vol = st.number_input("每孔加药体积 (μL)", value=90.0)
            # 默认复孔为 2，且不常显示
            s1_replicates = st.number_input("每浓度复孔数", value=2.0, step=1.0)
            s1_control_reps = st.number_input("阴性对照复孔数", value=2.0, step=1.0)
            s1_plate_num = st.number_input("板子数量", value=1.0)
            s1_extra_ratio = st.number_input("理论用量额外预留 (%)", value=10.0)
            s1_max_dilution = st.number_input("单步最大稀释倍数", value=10.0)

        single_submit = st.form_submit_button("计算连续稀释方案")

    if single_submit:
        # 处理阴性对照
        targets_text = s1_targets
        if "0" not in [x.strip() for x in s1_targets.replace("，", ",").split(",")]:
            if s1_control_reps > 0:
                targets_text = f"{s1_targets},0"

        # 计算理论最低需求
        base_needed = s1_add_vol * s1_replicates * s1_plate_num
        recommended_need = base_needed * (1 + s1_extra_ratio / 100)
        
        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        unit_factor = unit_factor_map.get(s1_unit, 1.0)

        # 确保输入体积足够
        effective_target_vol = max(recommended_need, s1_plan_vol)
        shortage_warning = s1_plan_vol < recommended_need

        rows, error = calc_single(
            s1_stock,
            s1_min_pipette,
            effective_target_vol,
            targets_text,
            work_conc_factor=2.0, # 默认2X工作液
            unit_factor=unit_factor,
            unit_label=s1_unit,
            max_dilution=s1_max_dilution,
        )
        
        if error:
            st.error(error)
        elif rows:
            st.caption(f"理论铺板需 {base_needed:.0f} μL/管。本次按保留 {effective_target_vol:.0f} μL 计算。")
            if shortage_warning:
                st.warning(f"注意：您设定的保留体积小于理论需求 ({recommended_need:.0f} μL)，已自动增加配液量。")
            st.dataframe(rows, use_container_width=True)
        else:
            st.info("暂无有效结果")

with tab3:
    st.subheader("双药联合矩阵 (Checkerboard) - 4× 配液管")
    st.caption("50 μL 细胞 + 25 μL 药A + 25 μL 药B。")

    with st.form("matrix_form"):
        st.markdown("**1. 矩阵设置**")
        c1, c2 = st.columns(2)
        with c1:
            m_rows = st.number_input("A 梯度数 (行)", value=6)
            m_stock_a = st.number_input("药A 母液 (mM)", value=10.0)
            m_high_a = st.number_input("药A 最高浓度", value=1000.0)
            # 默认单位 nM
            m_unit_a = st.selectbox("药A 单位", ["nM", "μM", "mM"], index=0)
            m_fold_a = st.number_input("药A 稀释倍数", value=4.0)
        with c2:
            m_cols = st.number_input("B 梯度数 (列)", value=6)
            m_stock_b = st.number_input("药B 母液 (mM)", value=10.0)
            m_high_b = st.number_input("药B 最高浓度", value=1000.0)
            # 默认单位 nM
            m_unit_b = st.selectbox("药B 单位", ["nM", "μM", "mM"], index=0)
            m_fold_b = st.number_input("药B 稀释倍数", value=4.0)

        st.markdown("**2. 保留体积**")
        m_keep_reserve = st.number_input("每管保留体积 (mL)", value=8.0, step=0.5)

        with st.expander("⚙️ 更多参数 (复孔/板数/死体积)"):
            m_reps = st.number_input("复孔数", value=2.0)
            m_plates = st.number_input("板子数量", value=7.0)
            m_dead_vol = st.number_input("死体积 (mL)", value=2.0)
            m_cell_vol = st.number_input("细胞体积 (μL)", value=50.0)
            m_add_a = st.number_input("药A体积 (μL)", value=25.0)
            m_add_b = st.number_input("药B体积 (μL)", value=25.0)
            m_min_pipette = st.number_input("最小取样 (μL)", value=2.0)
            m_max_dilution = st.number_input("最大稀释步长", value=10.0)

        matrix_submit = st.form_submit_button("生成配液方案")

    if matrix_submit:
        total_vol = m_cell_vol + m_add_a + m_add_b
        prep_factor = total_vol / m_add_a if m_add_a > 0 else 0
        prep_factor_b = total_vol / m_add_b if m_add_b > 0 else 0
        
        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        
        # 修正之前的括号错误
        targets_a = [m_high_a / (m_fold_a ** i) for i in range(max(int(m_rows) - 1, 1))]
        targets_a.append(0)
        targets_b = [m_high_b / (m_fold_b ** i) for i in range(max(int(m_cols) - 1, 1))]
        targets_b.append(0)

        wells_for_a = m_cols * m_reps
        wells_for_b = m_rows * m_reps

        rows_a, err_a, need_a = calc_practical_matrix_drug(
            m_stock_a, m_min_pipette, targets_a, prep_factor, wells_for_a, m_add_a,
            m_plates, m_dead_vol, m_keep_reserve, m_unit_a, unit_factor_map[m_unit_a], m_max_dilution
        )
        rows_b, err_b, need_b = calc_practical_matrix_drug(
            m_stock_b, m_min_pipette, targets_b, prep_factor_b, wells_for_b, m_add_b,
            m_plates, m_dead_vol, m_keep_reserve, m_unit_b, unit_factor_map[m_unit_b], m_max_dilution
        )

        if err_a: st.error(err_a)
        else: 
            st.success(f"🟠 药A ({m_unit_a}) - 4X 浓缩液")
            st.dataframe(rows_a, use_container_width=True)

        if err_b: st.error(err_b)
        else: 
            st.success(f"🔵 药B ({m_unit_b}) - 4X 浓缩液")
            st.dataframe(rows_b, use_container_width=True)

with tab4:
    st.subheader("三药协同 (Combo+C) - 4× 组装")
    
    with st.form("combo_form"):
        st.markdown("**1. 药物设置**")
        st.markdown("*Combo (A+B)*")
        ca1, ca2, ca3 = st.columns(3)
        with ca1: c_stock_a = st.number_input("A母液(mM)", value=10.0)
        with ca2: c_high_a = st.number_input("A最高", value=1000.0)
        # 默认单位 nM
        with ca3: c_unit_combo = st.selectbox("Combo单位", ["nM", "μM"], index=0)
        
        cb1, cb2, cb3 = st.columns(3)
        with cb1: c_stock_b = st.number_input("B母液(mM)", value=10.0)
        with cb2: c_high_b = st.number_input("B最高", value=500.0)
        with cb3: c_fold_combo = st.number_input("Combo倍数", value=4.0)

        st.markdown("*Drug C*")
        cc1, cc2, cc3, cc4 = st.columns(4)
        with cc1: c_stock_c = st.number_input("C母液", value=10.0)
        with cc2: c_high_c = st.number_input("C最高", value=2000.0)
        with cc3: c_fold_c = st.number_input("C倍数", value=4.0)
        # 默认单位 nM
        with cc4: c_unit_c = st.selectbox("C单位", ["nM", "μM"], index=0)

        st.markdown("**2. 保留体积**")
        c_keep_reserve = st.number_input("每管保留 (mL)", value=6.0, step=0.5)

        with st.expander("⚙️ 更多参数"):
            c_rows = st.number_input("Combo行数", value=6)
            c_cols = st.number_input("C列数", value=6)
            c_reps = st.number_input("复孔", value=2.0)
            c_plates = st.number_input("板数", value=7.0)
            c_combo_vol = st.number_input("Combo体积", value=25.0)
            c_c_vol = st.number_input("C体积", value=25.0)
            c_cell_vol = st.number_input("细胞体积", value=50.0)
            c_dead_vol = st.number_input("死体积", value=2.0)
            c_min_pipette = st.number_input("最小取样", value=2.0)
            c_max_dilution = st.number_input("最大步长", value=10.0)

        combo_submit = st.form_submit_button("生成方案")

    if combo_submit:
        unit_factor_map = {"nM": 0.001, "μM": 1.0, "mM": 1000.0}
        
        # 计算因子
        total_combo_factor = (c_cell_vol + c_combo_vol + c_c_vol) / c_combo_vol
        total_c_factor = (c_cell_vol + c_combo_vol + c_c_vol) / c_c_vol
        
        # 梯度生成
        targets_a = [c_high_a / (c_fold_combo ** i) for i in range(max(int(c_rows) - 1, 1))]
        targets_a.append(0)
        targets_b = [c_high_b / (c_fold_combo ** i) for i in range(max(int(c_rows) - 1, 1))]
        targets_b.append(0)
        targets_c = [c_high_c / (c_fold_c ** i) for i in range(max(int(c_cols) - 1, 1))]
        targets_c.append(0)

        # 用量计算
        wells_combo = c_cols * c_reps * c_plates
        wells_c = c_rows * c_reps * c_plates
        
        base_combo = (wells_combo * c_combo_vol) + (c_dead_vol * 1000)
        target_combo = base_combo + c_keep_reserve * 1000
        
        base_c = (wells_c * c_c_vol) + (c_dead_vol * 1000)
        target_c = base_c + c_keep_reserve * 1000

        # Combo 计算
        rows_combo, err_combo, need_combo = calc_combo_mix(
            c_stock_a, c_stock_b, c_min_pipette, targets_a, targets_b,
            total_combo_factor, target_combo, c_unit_combo, unit_factor_map[c_unit_combo]
        )

        # C 计算
        rows_c, err_c = calc_single(
            c_stock_c, c_min_pipette, target_c, ",".join(str(t) for t in targets_c),
            work_conc_factor=total_c_factor, unit_factor=unit_factor_map[c_unit_c],
            unit_label=c_unit_c, max_dilution=c_max_dilution
        )

        if err_combo: st.error(err_combo)
        else:
            st.success(f"🔴 Combo A+B ({c_unit_combo}) - 4X")
            st.dataframe(rows_combo, use_container_width=True)

        if err_c: st.error(err_c)
        else:
            st.success(f"🔵 Drug C ({c_unit_c}) - 4X")
            st.dataframe(rows_c, use_container_width=True)
