# MTT Streamlit 交接文档

## 目标
- 将 `mtt_tool.py`（Tkinter 桌面版 MTT 计算器）完整移植为手机可访问的 Web 应用。
- 采用 Streamlit，保留原有三大模块的计算逻辑、输出格式和单位说明。

## 已完成工作
- 新建 Streamlit 应用文件 `E:\MTT\streamlit_app.py`，内容与 Tkinter 版功能对齐。
- 三个模块全部复刻为 Tabs：
  - 细胞计数与铺板
  - 单药梯度配制（连续稀释）
  - 双药混合配制（Matrix）
- 保留原有计算逻辑与提示：
  - 原液浓度计算、铺板体积计算
  - 单药梯度：低浓度倒推、母液最小取样量修正
  - 双药混合：浓度过高提示
- 输出方式：
  - 计数与铺板结果使用 `st.code` 保留原格式
  - 单药、双药结果使用 `st.dataframe` 便于手机浏览
- 双药矩阵输入支持多行文本；使用 `st.session_state` 维持默认示例与“清空列表”功能。

## 文件清单
- `E:\MTT\streamlit_app.py`（新增）
- `E:\MTT\mtt_tool.py`（原始 Tkinter 版，未改动）
- `E:\MTT\README.md`（未改动，仍为桌面版说明）

## 运行方式
1) 安装依赖
```bash
pip install streamlit
```

2) 运行应用
```bash
python -m streamlit run E:\MTT\streamlit_app.py --server.headless true
```

3) 手机访问（同一局域网）
- 运行后终端会显示 `Network URL`，用手机浏览器打开即可。
- 如需显式绑定地址，可加：
```bash
--server.address 0.0.0.0
```

## 上次运行记录
- Streamlit 启动后打印：
  - Network URL: `http://192.168.0.248:8501`
  - External URL: `http://176.199.208.188:8501`
- 由于 CLI 超时，进程被结束；需要重新运行以保持服务。

## 已知注意点 / 待改进（可选）
- `README.md` 仍为 Tkinter 版描述，未加入 Streamlit 运行说明。
- 如需对齐 README 中“支持 μM/nM/mM 单位”的描述，可考虑扩展单位选择。
- 若需要部署到公网或长期访问，可考虑 Streamlit Cloud / 内网穿透 / 自建服务。

## 继续修改入口
- 主要代码都在 `E:\MTT\streamlit_app.py`。
- 计算逻辑函数：`calc_seeding`、`calc_single`、`calc_double`。

---
此文档用于下次继续修改时快速接续。
