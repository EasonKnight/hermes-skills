# app.pyw 配色方案记录

## 最终方案（2026-05-17）：Python IDLE Classic 亮色主题

**状态**：已应用于 app.pyw
**来源**：cpython/Lib/idlelib/config-highlight.def
**基调**：白底黑字

### 语义映射

| Python IDLE 语义 | 颜色 | UI 用途 |
|-----------------|------|---------|
| 背景(normal) | `#ffffff` | 窗口、面板 |
| 背景(浅灰) | `#f0f0f0` | 卡片、侧边栏、表格斑马纹 |
| 背景(中灰) | `#e0e0e0` | 输入框、表头、悬停 |
| 前景(normal) | `#000000` | 主文字 |
| 前景(辅文) | `#666666` | 标签、注释 |
| 关键字(keyword) | `#ff7700` | 金色强调、金额高亮、警告 |
| 函数(definition) | `#0000ff` | 选中行、蓝色按钮、链接 |
| 字符串(string) | `#00aa00` | 正收益数值、成功状态、绿色按钮 |
| 注释(comment) | `#dd0000` | 负收益数值、危险操作、红色按钮 |
| 内置(builtin) | `#900090` | AI/自动研发按钮、紫色强调 |

### 被拒绝的历史方案（不再尝试）
- Dracula 紫黑、TradingView 暗色、Tokyo Night、GitHub Dark、Catppuccin
- 任何自定义混合色、纯灰度/Tailwind 灰阶
- 之前应用的 color_code.txt "现代舒适深色（暗色主题）"

### 注意事项
- 表格选中行 `#0000ff` 配合白色文字
- 实盘标记 `#1a3a1a` 深绿底+白字
- 图表（matplotlib Visualizer）保持独立的暗色主题，不受 GUI 配色影响
- 按钮颜色用 BTN_TEAL/BTN_BLUE/BTN_PURPLE/BTN_RED 常量，比 ACCENT_* 稍深
