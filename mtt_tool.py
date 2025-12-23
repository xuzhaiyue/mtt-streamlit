import tkinter as tk
from tkinter import ttk, messagebox

class MTTLabAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("MTT 实验全能助手 (计数 + 配液)")
        self.root.geometry("700x800")

        # 创建分页 (Tabs)
        tab_control = ttk.Notebook(root)
        
        self.tab1 = ttk.Frame(tab_control)
        self.tab2 = ttk.Frame(tab_control)
        self.tab3 = ttk.Frame(tab_control)
        
        tab_control.add(self.tab1, text='1. 细胞计数与铺板')
        tab_control.add(self.tab2, text='2. 单药梯度配制')
        tab_control.add(self.tab3, text='3. 双药混合配制(A+B)')
        
        tab_control.pack(expand=1, fill="both")

        # 初始化各个模块
        self.setup_cell_counting(self.tab1)
        self.setup_single_drug(self.tab2)
        self.setup_double_drug(self.tab3)

    # =========================================================================
    # TAB 1: 细胞计数与铺板计算
    # =========================================================================
    def setup_cell_counting(self, tab):
        frame = ttk.LabelFrame(tab, text="细胞计数计算器", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        # 输入行
        ttk.Label(frame, text="计数板总细胞数:").grid(row=0, column=0, sticky="w", pady=5)
        self.count_num = tk.StringVar()
        ttk.Entry(frame, textvariable=self.count_num, width=10).grid(row=0, column=1)

        ttk.Label(frame, text="计数的格数 (大格):").grid(row=0, column=2, sticky="w", padx=10)
        self.count_squares = tk.StringVar(value="4")
        ttk.Entry(frame, textvariable=self.count_squares, width=10).grid(row=0, column=3)

        ttk.Label(frame, text="计数前稀释倍数:").grid(row=1, column=0, sticky="w", pady=5)
        self.dilution_factor = tk.StringVar(value="1")
        dilution_combo = ttk.Combobox(frame, textvariable=self.dilution_factor, width=8)
        dilution_combo['values'] = ("1", "2", "5", "10", "20")
        dilution_combo.grid(row=1, column=1)
        ttk.Label(frame, text="(如:太浓了稀释10倍后计数则填10)").grid(row=1, column=2, columnspan=2, sticky="w")

        # 铺板需求
        frame2 = ttk.LabelFrame(tab, text="铺板需求", padding=15)
        frame2.pack(fill="x", padx=10, pady=10)

        ttk.Label(frame2, text="目标每孔细胞数 (个):").grid(row=0, column=0, sticky="w", pady=5)
        self.target_cell_per_well = tk.StringVar(value="5000")
        ttk.Entry(frame2, textvariable=self.target_cell_per_well, width=10).grid(row=0, column=1)

        ttk.Label(frame2, text="每孔体积 (mL):").grid(row=0, column=2, sticky="w", padx=10)
        self.well_vol_ml = tk.StringVar(value="0.1")
        ttk.Entry(frame2, textvariable=self.well_vol_ml, width=10).grid(row=0, column=3)

        ttk.Label(frame2, text="计划铺板数量 (块):").grid(row=1, column=0, sticky="w", pady=5)
        self.plate_num = tk.StringVar(value="1")
        ttk.Entry(frame2, textvariable=self.plate_num, width=10).grid(row=1, column=1)
        
        ttk.Label(frame2, text="配液余量 (mL):").grid(row=1, column=2, sticky="w", padx=10)
        self.seed_safety = tk.StringVar(value="2.0")
        ttk.Entry(frame2, textvariable=self.seed_safety, width=10).grid(row=1, column=3)

        # 按钮与结果
        btn = ttk.Button(tab, text="计算铺板方案", command=self.calc_seeding)
        btn.pack(pady=10)

        self.seed_result_label = ttk.Label(tab, text="...", font=("Arial", 11), foreground="blue", justify="left")
        self.seed_result_label.pack(pady=10, padx=20, anchor="w")

    def calc_seeding(self):
        try:
            n = float(self.count_num.get())
            sq = float(self.count_squares.get())
            df = float(self.dilution_factor.get())
            
            target_per_well = float(self.target_cell_per_well.get())
            vol_per_well = float(self.well_vol_ml.get())
            plates = float(self.plate_num.get())
            safety = float(self.seed_safety.get())

            # 1. 计算原液浓度 (Cells/mL)
            # 公式: (N / Squares) * 10000 * Dilution
            conc_cells_ml = (n / sq) * 10000 * df
            
            # 2. 计算需要配制的总体积 (mL)
            # 96孔板按100孔算比较保险，或者按实际 (96 * plates)
            total_wells = 96 * plates
            total_prep_vol = (total_wells * vol_per_well) + safety # mL

            # 3. 计算需要的细胞总数
            # 目标浓度 (Cells/mL) = target_per_well / vol_per_well
            target_conc = target_per_well / vol_per_well
            
            # C1 * V1 = C2 * V2
            # V1 (取原液) = (Target_Conc * Total_Prep_Vol) / Stock_Conc
            if conc_cells_ml == 0:
                self.seed_result_label.config(text="错误：细胞计数为0")
                return

            vol_cell_stock = (target_conc * total_prep_vol) / conc_cells_ml
            vol_medium = total_prep_vol - vol_cell_stock

            res_text = (f"【计算结果】\n"
                        f"1. 原液细胞密度: {conc_cells_ml/10000:.2f} x 10^4 /mL\n"
                        f"2. 铺板液目标密度: {target_conc/10000:.2f} x 10^4 /mL\n"
                        f"3. 需配制总体积: {total_prep_vol:.1f} mL (含余量)\n\n"
                        f"👉 操作方案:\n"
                        f"   取细胞悬液: {vol_cell_stock:.2f} mL ({vol_cell_stock*1000:.1f} μL)\n"
                        f"   + 培养基  : {vol_medium:.2f} mL")
            self.seed_result_label.config(text=res_text)

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    # =========================================================================
    # TAB 2: 单药梯度配制 (连续稀释法 Serial Dilution) - 升级版
    # =========================================================================
    def setup_single_drug(self, tab):
        # 顶部设置区
        top_frame = ttk.Frame(tab, padding=10)
        top_frame.pack(fill="x")
        
        # 第一行：母液与限制
        ttk.Label(top_frame, text="药物母液浓度 (mM):").grid(row=0, column=0, sticky="w")
        self.s1_stock = tk.StringVar(value="10")
        ttk.Entry(top_frame, textvariable=self.s1_stock, width=8).grid(row=0, column=1, padx=5)

        ttk.Label(top_frame, text="母液最小取样量 (μL):").grid(row=0, column=2, sticky="w")
        self.min_pipette = tk.StringVar(value="2.0") # 严谨需求：至少取2ul
        ttk.Entry(top_frame, textvariable=self.min_pipette, width=8).grid(row=0, column=3, padx=5)

        # 第二行：体积设置
        ttk.Label(top_frame, text="每管实验需用量 (μL):").grid(row=1, column=0, sticky="w", pady=5)
        self.s1_needed_vol = tk.StringVar(value="1000") # 铺板用的量
        ttk.Entry(top_frame, textvariable=self.s1_needed_vol, width=8).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(top_frame, text="(程序会自动计算所需的额外传递体积)").grid(row=1, column=2, columnspan=2, sticky="w")
        
        # 浓度梯度输入
        input_frame = ttk.LabelFrame(tab, text="浓度梯度设置 (μM) - 自动按高到低稀释", padding=10)
        input_frame.pack(fill="x", padx=10)
        
        ttk.Label(input_frame, text="输入目标浓度 (逗号分隔):").pack(anchor="w")
        self.s1_targets = tk.StringVar(value="0, 1, 5, 10, 50, 100")
        ttk.Entry(input_frame, textvariable=self.s1_targets, width=60).pack(fill="x", pady=5)

        # 按钮
        ttk.Button(tab, text="计算连续稀释方案", command=self.calc_single).pack(pady=10)

        # 结果表格
        columns = ("conc", "source", "vol_source", "vol_media", "total_prep")
        self.tree1 = ttk.Treeview(tab, columns=columns, show="headings", height=10)
        self.tree1.heading("conc", text="目标浓度 (μM)")
        self.tree1.heading("source", text="取液来源")
        self.tree1.heading("vol_source", text="取液体积 (μL)")
        self.tree1.heading("vol_media", text="加培养基 (μL)")
        self.tree1.heading("total_prep", text="该管配制总量 (μL)")
        
        self.tree1.column("conc", width=100, anchor="center")
        self.tree1.column("source", width=120, anchor="center")
        self.tree1.column("vol_source", width=100, anchor="center")
        self.tree1.column("vol_media", width=100, anchor="center")
        self.tree1.column("total_prep", width=120, anchor="center")

        self.tree1.pack(fill="both", expand=True, padx=10, pady=10)

    def calc_single(self):
        # 清空
        for item in self.tree1.get_children():
            self.tree1.delete(item)
            
        try:
            stock_mm = float(self.s1_stock.get())
            stock_um = stock_mm * 1000 # 换算为 uM
            min_pipette = float(self.min_pipette.get())
            needed_vol = float(self.s1_needed_vol.get()) # 实验最终要用的量
            
            raw_targets = self.s1_targets.get().replace("，", ",").split(",")
            # 过滤空值并去重，排序从大到小
            targets = sorted(list(set([float(x) for x in raw_targets if x.strip()])), reverse=True)
            
            # 用一个字典来存储每一级“需要被下一级取走多少体积”
            # Key: 浓度, Value: 被取走的体积
            transfer_needs = {t: 0 for t in targets}
            
            # 存储计算结果，方便最后按从小到大或从大到小显示
            results = []

            # === 核心逻辑：从低浓度往高浓度倒推 ===
            # 因为低浓度是从高浓度里取走的，所以必须先算低浓度
            
            # 0浓度特殊处理（最后加）
            has_zero = False
            if 0 in targets:
                has_zero = True
                targets.remove(0)

            # 倒序遍历（从低到高：1 -> 5 -> 10 -> ...）
            # targets 现在是 [100, 50, 10, 5, 1]
            # reversed(targets) 就是 [1, 5, 10, 50, 100]
            
            prev_conc = 0 # 实际上对于低浓度，它的上级是列表中下一个大的
            
            # 我们需要构建一个链条：Source -> Target
            # 100 (Source=Stock) -> 50 (Source=100) -> 10 (Source=50) ...
            
            # 重新正向遍历来确定 Source，但计算需要反向？
            # 不，最简单的思路：
            # 1. 确定每一级的 Source 是谁
            # 2. 确定每一级需要配制的 Total Vol = Needed + (被下一级取走的量)
            
            # 让我们用列表索引操作
            calc_data = [] # 存临时数据
            for i in range(len(targets)):
                current_c = targets[i]
                is_highest = (i == 0)
                
                # 确定来源
                if is_highest:
                    source_c = stock_um
                    source_name = "母液 Stock"
                else:
                    source_c = targets[i-1] # 上一个更高的浓度
                    source_name = f"上一管 ({source_c} μM)"
                
                calc_data.append({
                    "conc": current_c,
                    "source_c": source_c,
                    "source_name": source_name,
                    "is_stock": is_highest
                })
            
            # 现在从低浓度 (List尾部) 开始往回算
            # 比如 targets = [100, 10, 1]
            # calc_data = [{100, src=Stock}, {10, src=100}, {1, src=10}]
            
            for i in range(len(calc_data)-1, -1, -1):
                item = calc_data[i]
                conc = item["conc"]
                source_c = item["source_c"]
                
                # 1. 确定这管要做多少体积
                # 基础是 needed_vol
                # 加上 被下一级取走的量 (transfer_needs)
                total_make_vol = needed_vol + transfer_needs[conc]
                
                # 2. 计算从来源取多少 (C1V1 = C2V2)
                # V_take = (Target_Conc * Total_Make_Vol) / Source_Conc
                vol_take = (conc * total_make_vol) / source_c
                
                # === 关键：母液取样限制修正 ===
                if item["is_stock"] and vol_take < min_pipette:
                    # 如果算出来只要 0.5ul，但限制是 2ul
                    # 比例因子 factor = 2.0 / 0.5 = 4倍
                    factor = min_pipette / vol_take
                    
                    # 修正：我们需要配更多的体积
                    vol_take = min_pipette
                    total_make_vol = total_make_vol * factor
                    
                    # 提示用户
                    item["note"] = " (已扩大体积以满足母液取样)"
                else:
                    item["note"] = ""

                # 3. 记录需要从上一级取走的量 (传给上一级循环用)
                if not item["is_stock"]:
                    transfer_needs[source_c] = vol_take
                
                vol_media = total_make_vol - vol_take
                
                # 存结果
                item["vol_take"] = vol_take
                item["vol_media"] = vol_media
                item["final_total"] = total_make_vol
                results.append(item)

            # 结果现在是 低->高 的顺序，我们反转回 高->低 显示，符合操作顺序
            results.reverse()
            
            # 插入 Treeview
            for res in results:
                self.tree1.insert("", "end", values=(
                    res["conc"],
                    res["source_name"],
                    f"{res['vol_take']:.2f}",  # 保留2位小数
                    f"{res['vol_media']:.1f}",
                    f"{res['final_total']:.1f}" + res["note"]
                ))
                
            if has_zero:
                self.tree1.insert("", "end", values=(
                    0, "不加药", "0", needed_vol, needed_vol
                ))
                    
        except ValueError:
            messagebox.showerror("错误", "请输入有效数字，注意单位换算")


    # =========================================================================
    # TAB 3: 双药混合配制 (A+B) - 适用于 Matrix 矩阵实验
    # =========================================================================
    def setup_double_drug(self, tab):
        # 提示信息
        info_label = ttk.Label(tab, text="此模式用于计算单孔/单管中同时加入药A和药B (如 Synergy Matrix)", foreground="red")
        info_label.pack(pady=5)

        # 1. 母液设置区域
        stock_frame = ttk.LabelFrame(tab, text="母液设置 (输入 mM，计算自动转为 μM)", padding=10)
        stock_frame.pack(fill="x", padx=10)
        
        # 药A
        ttk.Label(stock_frame, text="药A 母液 (mM):").grid(row=0, column=0, sticky="e")
        self.d_stock_a = tk.StringVar(value="10")
        ttk.Entry(stock_frame, textvariable=self.d_stock_a, width=8).grid(row=0, column=1, padx=5)
        
        # 药B
        ttk.Label(stock_frame, text="药B 母液 (mM):").grid(row=0, column=2, sticky="e")
        self.d_stock_b = tk.StringVar(value="10")
        ttk.Entry(stock_frame, textvariable=self.d_stock_b, width=8).grid(row=0, column=3, padx=5)

        # 体积
        ttk.Label(stock_frame, text="每管配制体积 (μL):").grid(row=0, column=4, sticky="e")
        self.d_total_vol = tk.StringVar(value="1000")
        ttk.Entry(stock_frame, textvariable=self.d_total_vol, width=8).grid(row=0, column=5, padx=5)

        # 2. 混合梯度输入区域 (Matrix List)
        input_frame = ttk.LabelFrame(tab, text="Matrix 浓度组合清单 (μM)", padding=10)
        input_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(input_frame, text="输入格式：药A浓度, 药B浓度 (一行一个组合)").pack(anchor="w")
        ttk.Label(input_frame, text="提示：你可以从 Excel 复制一列 '10, 20' 这样的数据粘贴进来", font=("Arial", 9), foreground="gray").pack(anchor="w")
        
        # 默认给几个示例
        self.text_input = tk.Text(input_frame, height=10, width=40)
        self.text_input.pack(fill="both", expand=True, pady=5)
        self.text_input.insert("1.0", "0, 0\n10, 0\n0, 20\n10, 20\n5, 50\n")

        # 3. 按钮
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="计算 Matrix 配液方案", command=self.calc_double).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清空列表", command=lambda: self.text_input.delete("1.0", tk.END)).pack(side="left", padx=5)

        # 4. 结果表格
        columns = ("conc_a", "conc_b", "vol_a", "vol_b", "vol_media")
        self.tree2 = ttk.Treeview(tab, columns=columns, show="headings", height=10)
        
        self.tree2.heading("conc_a", text="药A终浓度 (μM)")
        self.tree2.heading("conc_b", text="药B终浓度 (μM)")
        self.tree2.heading("vol_a", text="取药A (μL)")
        self.tree2.heading("vol_b", text="取药B (μL)")
        self.tree2.heading("vol_media", text="加培养基 (μL)")
        
        self.tree2.column("conc_a", width=100, anchor="center")
        self.tree2.column("conc_b", width=100, anchor="center")
        self.tree2.column("vol_a", width=100, anchor="center")
        self.tree2.column("vol_b", width=100, anchor="center")
        self.tree2.column("vol_media", width=120, anchor="center")
        
        self.tree2.pack(fill="both", expand=True, padx=10, pady=10)

    def calc_double(self):
        # 清空旧结果
        for item in self.tree2.get_children():
            self.tree2.delete(item)
            
        try:
            # === 核心修正：自动单位换算 ===
            # 输入的是 mM，计算时乘 1000 变成 μM
            stock_a_um = float(self.d_stock_a.get()) * 1000 
            stock_b_um = float(self.d_stock_b.get()) * 1000 
            
            total_vol = float(self.d_total_vol.get())
            
            # 读取文本框内容
            content = self.text_input.get("1.0", tk.END).strip()
            if not content:
                return
                
            lines = content.split("\n")
            
            for line in lines:
                # 处理中文逗号和多余空格
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
                    continue # 跳过格式错误的行
                
                # === 计算逻辑 (C1V1 = C2V2) ===
                # 都是 μM 单位，直接除
                vol_a = (target_a * total_vol) / stock_a_um
                vol_b = (target_b * total_vol) / stock_b_um
                
                # 培养基体积 = 总量 - 两个药的体积
                vol_media = total_vol - vol_a - vol_b
                
                # 检查逻辑：如果体积不够，说明浓度太高或母液太稀
                if vol_media < 0:
                    self.tree2.insert("", "end", values=(
                        target_a, target_b, "Error", "Error", "浓度过高(母液不足)"
                    ))
                else:
                    self.tree2.insert("", "end", values=(
                        target_a, 
                        target_b, 
                        f"{vol_a:.3f}", 
                        f"{vol_b:.3f}", 
                        f"{vol_media:.1f}"
                    ))

        except ValueError:
            messagebox.showerror("输入错误", "请检查母液浓度或体积是否输入了非数字字符。")
            

if __name__ == "__main__":
    root = tk.Tk()
    app = MTTLabAssistant(root)
    root.mainloop()