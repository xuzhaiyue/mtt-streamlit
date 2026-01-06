diff --git a/streamlit_app.py b/streamlit_app.py
index 523ddf40d4849926fdd47e68db69cd7aade30131..13e6c53377d6614d339ec903ab2857a78f883aa9 100644
b/streamlit_app.py
@@ -317,57 +317,57 @@ def calc_combo_mix(
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
 
-st.title("MTT 实验全能助手 (计数 + 配液)")
-st.caption("基于 Streamlit 的手机友好版本，输入参数后点击按钮即可获得配液方案。")
-
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
 
@@ -431,84 +431,73 @@ with tab2:
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

        s1_replicates = 2
        s1_control_reps = 2
        st.caption("复孔与 0 μM 阴性对照默认各 2 孔/板，如需调整请在复制后自行修改参数。")
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
             value=10.0,
             step=5.0,
             format="%.0f",
         )
 
         st.markdown("**浓度梯度设置 - 自动按高到低稀释**")
         s1_unit = st.selectbox(
             "浓度单位",
             options=["nM", "μM", "mM"],
           index=0,
             help="选择目标终浓度的单位，程序会自动换算到 μM 计算",
         )
         s1_targets = st.text_input(
             "输入目标浓度 (逗号分隔)",
             value="0, 1, 5, 10, 50, 100",
         )
 
         base_needed = s1_add_vol * s1_replicates * s1_plate_num
         suggest_min = base_needed * (1 + s1_extra_ratio / 100)
         s1_plan_vol = st.number_input(
             "每管希望最终至少保留体积 (μL)",
             min_value=0.0,
             value=float(int(suggest_min) if suggest_min > 0 else 0),
             step=50.0,
             help="填写完成稀释后希望每管至少剩余的体积（不含被后续取走的体积）。建议略高于理论最小值。",
         )
         s1_max_dilution = st.number_input(
             "单步最大稀释倍数 (默认 10×，越大跳跃越多)",
             min_value=1.0,
             value=10.0,
             step=1.0,
             help="选择上一管时优先选稀释倍数最大的（不超过此值），以减少传递步骤，例如 100→10，50→5。",
         )
 
         single_submit = st.form_submit_button("计算连续稀释方案")
@@ -586,61 +575,61 @@ with tab3:
         m_add_b = st.number_input("每孔加药B体积 (μL)", min_value=0.0, value=25.0, step=1.0)
 
         st.markdown("**矩阵与用量**")
         m_rows = st.number_input("矩阵行数 (A 梯度数)", min_value=2, value=6, step=1)
         m_cols = st.number_input("矩阵列数 (B 梯度数)", min_value=2, value=6, step=1)
         m_reps = st.number_input("每组合复孔数", min_value=1, value=2, step=1, format="%.0f")
         m_plates = st.number_input("板子数量", min_value=1, value=7, step=1, format="%.0f")
         m_dead_vol = st.number_input("加药槽死体积 (mL)", min_value=0.0, value=2.0, step=0.5, format="%.1f")
         m_keep_reserve = st.number_input(
             "希望每管至少剩余 (mL)",
             min_value=0.0,
             value=8.0,
             step=0.5,
             help="完成稀释后希望每管保留的体积，实际表格会显示倒推后的“预计剩余”。",
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
             "单步最大稀释倍数", min_value=1.0, value=10.0, step=1.0, help="控制跳跃稀释的上限，避免过多中间步骤。"
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
@@ -721,62 +710,62 @@ with tab4:
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
 
         base_combo_ul = (wells_combo * c_combo_vol) + (c_dead_vol * 1000)
         base_c_ul = (wells_c * c_c_vol) + (c_dead_vol * 1000)
         target_combo_vol = base_combo_ul + c_keep_reserve * 1000
         target_c_vol = base_c_ul + c_keep_reserve * 1000
 
         rows_combo, err_combo, need_combo = calc_combo_mix(
             c_stock_a,
