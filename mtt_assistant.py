# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox


class MTTLabAssistant:
    def __init__(self, root):
        self.root = root
        self.root.title("MTT 实验全能助手 (计数 + 配液)")
        self.root.geometry("780x860")
        self.root.minsize(740, 820)

        tab_control = ttk.Notebook(root)
        self.tab_count = ttk.Frame(tab_control)
        self.tab_single = ttk.Frame(tab_control)
        self.tab_double = ttk.Frame(tab_control)

        tab_control.add(self.tab_count, text="1. 细胞计数与铺板")
        tab_control.add(self.tab_single, text="2. 单药梯度配制")
        tab_control.add(self.tab_double, text="3. 双药混合配制(A+B)")
        tab_control.pack(expand=1, fill="both")

        self.setup_cell_counting(self.tab_count)
        self.setup_single_drug(self.tab_single)
        self.setup_double_drug(self.tab_double)

    @staticmethod
    def _clear_tree(tree):
        for item in tree.get_children():
            tree.delete(item)

    # =========================================================================
    # TAB 1: 细胞计数与铺板计算
    # =========================================================================
    def setup_cell_counting(self, tab):
        frame = ttk.LabelFrame(tab, text="细胞计数", padding=12)
        frame.pack(fill="x", padx=10, pady=8)

        ttk.Label(frame, text="计数板总细胞数:").grid(row=0, column=0, sticky="w", pady=5)
        self.count_num = tk.StringVar()
        ttk.Entry(frame, textvariable=self.count_num, width=10).grid(row=0, column=1)

        ttk.Label(frame, text="计数大格数:").grid(row=0, column=2, sticky="w", padx=10)
        self.count_squares = tk.StringVar(value="4")
        ttk.Entry(frame, textvariable=self.count_squares, width=10).grid(row=0, column=3)

        ttk.Label(frame, text="计数稀释倍数:").grid(row=1, column=0, sticky="w", pady=5)
        self.dilution_factor = tk.StringVar(value="1")
        dilution_combo = ttk.Combobox(frame, textvariable=self.dilution_factor, width=8)
        dilution_combo["values"] = ("1", "2", "5", "10", "20")
        dilution_combo.grid(row=1, column=1)
        ttk.Label(frame, text="(如: 稀释10倍后计数则填10)").grid(row=1, column=2, columnspan=2, sticky="w")

        frame2 = ttk.LabelFrame(tab, text="铺板设置", padding=12)
        frame2.pack(fill="x", padx=10, pady=8)

        ttk.Label(frame2, text="目标每孔细胞数 (个):").grid(row=0, column=0, sticky="w", pady=5)
        self.target_cell_per_well = tk.StringVar(value="5000")
        ttk.Entry(frame2, textvariable=self.target_cell_per_well, width=10).grid(row=0, column=1)

        ttk.Label(frame2, text="每孔体积 (mL):").grid(row=0, column=2, sticky="w", padx=10)
        self.well_vol_ml = tk.StringVar(value="0.1")
        ttk.Entry(frame2, textvariable=self.well_vol_ml, width=10).grid(row=0, column=3)

        ttk.Label(frame2, text="使用孔数/板:").grid(row=1, column=0, sticky="w", pady=5)
        self.wells_per_plate = tk.StringVar(value="96")
        ttk.Entry(frame2, textvariable=self.wells_per_plate, width=10).grid(row=1, column=1)

        ttk.Label(frame2, text="计划铺板数量 (块):").grid(row=1, column=2, sticky="w", padx=10)
        self.plate_num = tk.StringVar(value="1")
        ttk.Entry(frame2, textvariable=self.plate_num, width=10).grid(row=1, column=3)

        ttk.Label(frame2, text="配液余量 (mL):").grid(row=2, column=0, sticky="w", pady=5)
        self.seed_safety = tk.StringVar(value="0.5")
        ttk.Entry(frame2, textvariable=self.seed_safety, width=10).grid(row=2, column=1)

        btn = ttk.Button(tab, text="计算铺板方案", command=self.calc_seeding)
        btn.pack(pady=8)

        self.seed_result_label = ttk.Label(
            tab, text="...", font=("Arial", 11), foreground="blue", justify="left"
        )
        self.seed_result_label.pack(pady=8, padx=20, anchor="w")

    def calc_seeding(self):
        try:
            n = float(self.count_num.get())
            sq = float(self.count_squares.get())
            df = float(self.dilution_factor.get())

            target_per_well = float(self.target_cell_per_well.get())
            vol_per_well = float(self.well_vol_ml.get())
            wells_per_plate = float(self.wells_per_plate.get())
            plates = float(self.plate_num.get())
            safety = float(self.seed_safety.get())

            if sq <= 0 or vol_per_well <= 0 or wells_per_plate <= 0 or plates <= 0:
                raise ValueError

            conc_cells_ml = (n / sq) * 10000 * df
            target_conc = target_per_well / vol_per_well
            total_wells = wells_per_plate * plates
            total_prep_vol = (total_wells * vol_per_well) + safety

            if conc_cells_ml <= 0 or target_conc <= 0 or total_prep_vol <= 0:
                raise ValueError

            vol_cell_stock = (target_conc * total_prep_vol) / conc_cells_ml
            vol_medium = total_prep_vol - vol_cell_stock

            if vol_medium < 0:
                messagebox.showwarning("警告", "原液浓度偏低，无法配到目标浓度。")

            total_cells_needed = target_per_well * total_wells

            res_text = (
                f"【计算结果】\n"
                f"1. 原液细胞密度: {conc_cells_ml/10000:.2f} x 10^4 /mL\n"
                f"2. 铺板液目标密度: {target_conc/10000:.2f} x 10^4 /mL\n"
                f"3. 需要细胞总数: {total_cells_needed:,.0f} 个\n"
                f"4. 需配制总体积: {total_prep_vol:.2f} mL (含余量)\n\n"
                f"操作方案:\n"
                f"  取细胞悬液: {vol_cell_stock:.3f} mL ({vol_cell_stock*1000:.1f} μL)\n"
                f"  + 培养基  : {vol_medium:.3f} mL"
            )
            self.seed_result_label.config(text=res_text)

        except ValueError:
            messagebox.showerror("错误", "请输入有效的数字")

    # =========================================================================
    # TAB 2: 单药梯度配制
    # =========================================================================
    def setup_single_drug(self, tab):
        top_frame = ttk.Frame(tab, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="给药方式:").grid(row=0, column=0, sticky="w")
        self.s1_mode = tk.StringVar(value="replace")
        ttk.Radiobutton(
            top_frame,
            text="方式A 换液法 (100%)",
            variable=self.s1_mode,
            value="replace",
        ).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Radiobutton(
            top_frame,
            text="方式B 添加法/2X",
            variable=self.s1_mode,
            value="add",
        ).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Label(top_frame, text="(输入终浓度，2X模式自动×2)").grid(
            row=1, column=1, columnspan=3, sticky="w", pady=2
        )

        ttk.Label(top_frame, text="药物母液浓度 (mM):").grid(row=2, column=0, sticky="w", pady=5)
        self.s1_stock = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.s1_stock, width=10).grid(row=2, column=1, padx=5)

        ttk.Label(top_frame, text="每种浓度配制体积 (μL):").grid(row=2, column=2, sticky="w")
        self.s1_total_vol = tk.StringVar(value="1000")
        ttk.Entry(top_frame, textvariable=self.s1_total_vol, width=10).grid(row=2, column=3, padx=5)

        input_frame = ttk.LabelFrame(tab, text="浓度梯度设置 (μM)", padding=10)
        input_frame.pack(fill="x", padx=10)

        ttk.Label(input_frame, text="输入目标浓度 (逗号分隔，如 0, 10, 20, 50):").pack(anchor="w")
        self.s1_targets = tk.StringVar(value="0, 5, 10, 20, 50, 100")
        ttk.Entry(input_frame, textvariable=self.s1_targets, width=60).pack(fill="x", pady=5)

        ttk.Button(tab, text="计算单药配方", command=self.calc_single).pack(pady=8)

        columns = ("target", "solution", "stock_add", "media_add")
        self.tree1 = ttk.Treeview(tab, columns=columns, show="headings", height=9)
        self.tree1.heading("target", text="终浓度 (μM)")
        self.tree1.heading("solution", text="配液浓度 (μM)")
        self.tree1.heading("stock_add", text="取母液 (μL)")
        self.tree1.heading("media_add", text="加培养基 (μL)")
        self.tree1.column("target", width=120)
        self.tree1.column("solution", width=120)
        self.tree1.column("stock_add", width=120)
        self.tree1.column("media_add", width=120)
        self.tree1.pack(fill="both", expand=True, padx=10, pady=10)

    def calc_single(self):
        self._clear_tree(self.tree1)

        try:
            stock = float(self.s1_stock.get()) * 1000
            total_vol = float(self.s1_total_vol.get())
            mode = self.s1_mode.get()
            multiplier = 2 if mode == "add" else 1

            if stock <= 0 or total_vol <= 0:
                raise ValueError

            targets = [
                float(x)
                for x in self.s1_targets.get().replace("，", ",").split(",")
                if x.strip()
            ]

            for t in targets:
                solution = t * multiplier
                if solution == 0:
                    self.tree1.insert("", "end", values=(t, solution, 0, f"{total_vol:.1f}"))
                    continue

                v_stock = (solution * total_vol) / stock
                v_media = total_vol - v_stock

                if v_media < 0:
                    messagebox.showwarning("警告", f"终浓度 {t} μM 过高，母液不足以配制")
                    continue

                self.tree1.insert(
                    "",
                    "end",
                    values=(t, f"{solution:.2f}", f"{v_stock:.3f}", f"{v_media:.1f}"),
                )

        except ValueError:
            messagebox.showerror("错误", "请输入有效数字，注意单位换算 (母液mM, 目标μM)")

    # =========================================================================
    # TAB 3: 双药混合配制 (A+B)
    # =========================================================================
    def setup_double_drug(self, tab):
        info_label = ttk.Label(tab, text="此模式用于计算一个管中同时加入药A和药B", foreground="red")
        info_label.pack(pady=5)

        mode_frame = ttk.Frame(tab, padding=5)
        mode_frame.pack(fill="x")
        ttk.Label(mode_frame, text="给药方式:").grid(row=0, column=0, sticky="w")
        self.d_mode = tk.StringVar(value="replace")
        ttk.Radiobutton(
            mode_frame,
            text="方式A 换液法 (100%)",
            variable=self.d_mode,
            value="replace",
        ).grid(row=0, column=1, sticky="w", padx=5)
        ttk.Radiobutton(
            mode_frame,
            text="方式B 添加法/2X",
            variable=self.d_mode,
            value="add",
        ).grid(row=0, column=2, sticky="w", padx=5)
        ttk.Label(mode_frame, text="(输入终浓度，2X模式自动×2)").grid(
            row=1, column=1, columnspan=3, sticky="w", pady=2
        )

        stock_frame = ttk.LabelFrame(tab, text="母液设置 (单位需一致)", padding=10)
        stock_frame.pack(fill="x", padx=10)

        ttk.Label(stock_frame, text="药A 母液浓度:").grid(row=0, column=0)
        self.d_stock_a = tk.StringVar()
        ttk.Entry(stock_frame, textvariable=self.d_stock_a, width=8).grid(row=0, column=1, padx=5)

        ttk.Label(stock_frame, text="药B 母液浓度:").grid(row=0, column=2)
        self.d_stock_b = tk.StringVar()
        ttk.Entry(stock_frame, textvariable=self.d_stock_b, width=8).grid(row=0, column=3, padx=5)

        ttk.Label(stock_frame, text="每管配制体积(μL):").grid(row=0, column=4)
        self.d_total_vol = tk.StringVar(value="1000")
        ttk.Entry(stock_frame, textvariable=self.d_total_vol, width=8).grid(row=0, column=5, padx=5)

        input_frame = ttk.LabelFrame(tab, text="混合梯度清单 (一行一个组合)", padding=10)
        input_frame.pack(fill="both", expand=True, padx=10, pady=5)

        ttk.Label(input_frame, text="输入格式：药A浓度, 药B浓度 (回车换行)").pack(anchor="w")
        ttk.Label(
            input_frame,
            text="例如:\n10, 20 (表示A=10, B=20)\n20, 20 (表示A=20, B=20)",
            font=("Arial", 9),
            foreground="gray",
        ).pack(anchor="w")

        self.text_input = tk.Text(input_frame, height=8, width=40)
        self.text_input.pack(fill="both", expand=True, pady=5)
        self.text_input.insert("1.0", "10, 0\n10, 10\n10, 20\n20, 20\n")

        ttk.Button(tab, text="计算混合配方", command=self.calc_double).pack(pady=5)

        columns = ("conc_a", "conc_b", "vol_a", "vol_b", "vol_media")
        self.tree2 = ttk.Treeview(tab, columns=columns, show="headings", height=9)
        self.tree2.heading("conc_a", text="药A终浓度")
        self.tree2.heading("conc_b", text="药B终浓度")
        self.tree2.heading("vol_a", text="加药A (μL)")
        self.tree2.heading("vol_b", text="加药B (μL)")
        self.tree2.heading("vol_media", text="加培养基 (μL)")

        self.tree2.column("conc_a", width=100)
        self.tree2.column("conc_b", width=100)
        self.tree2.column("vol_a", width=110)
        self.tree2.column("vol_b", width=110)
        self.tree2.column("vol_media", width=120)

        self.tree2.pack(fill="both", expand=True, padx=10, pady=10)

    def calc_double(self):
        self._clear_tree(self.tree2)

        try:
            stock_a = float(self.d_stock_a.get())
            stock_b = float(self.d_stock_b.get())
            total_vol = float(self.d_total_vol.get())
            mode = self.d_mode.get()
            multiplier = 2 if mode == "add" else 1

            if stock_a <= 0 or stock_b <= 0 or total_vol <= 0:
                raise ValueError

            content = self.text_input.get("1.0", tk.END).strip()
            lines = content.split("\n") if content else []

            for line in lines:
                line = line.strip().replace("，", ",")
                if not line or "," not in line:
                    continue

                parts = [p.strip() for p in line.split(",") if p.strip()]
                if len(parts) < 2:
                    continue

                target_a = float(parts[0])
                target_b = float(parts[1])

                solution_a = target_a * multiplier
                solution_b = target_b * multiplier

                vol_a = (solution_a * total_vol) / stock_a
                vol_b = (solution_b * total_vol) / stock_b
                vol_media = total_vol - vol_a - vol_b

                if vol_media < 0:
                    messagebox.showwarning("警告", f"浓度 {target_a}, {target_b} 过高，母液不足以配制")
                    continue

                self.tree2.insert(
                    "",
                    "end",
                    values=(
                        f"{target_a:g}",
                        f"{target_b:g}",
                        f"{vol_a:.3f}",
                        f"{vol_b:.3f}",
                        f"{vol_media:.1f}",
                    ),
                )

        except ValueError:
            messagebox.showerror("错误", "请输入有效数字。")


if __name__ == "__main__":
    root = tk.Tk()
    app = MTTLabAssistant(root)
    root.mainloop()
