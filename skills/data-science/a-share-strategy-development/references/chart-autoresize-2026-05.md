# Tkinter Canvas 图片自适应缩放

## 问题

在 tkinter `Canvas` 中加载图片后，窗口大小变化时图片不会自动缩放，导致图片过小或需要滚动条查看。

## 解决方案

1. 存储原始 PIL Image 对象
2. 绑定 `<Configure>` 事件到 Canvas
3. 每次事件触发时按 Canvas 当前尺寸重新缩放并居中显示

## 代码实现

```python
# 在 show_detail() 中加载并存储原图
self._raw_pil_img = Image.open(equity)
self._render_chart()
# 绑定窗口大小变化
self.img_canvas.bind("<Configure>", self._on_canvas_resize, add="+")

def _on_canvas_resize(self, event=None):
    if self._raw_pil_img:
        self._render_chart()

def _render_chart(self):
    if not self._raw_pil_img:
        return
    self.img_canvas.delete("all")
    cw = self.img_canvas.winfo_width() - 16
    ch = self.img_canvas.winfo_height() - 16
    if cw < 100 or ch < 100:
        return
    img = self._raw_pil_img
    ratio = min(cw / img.width, ch / img.height)
    new_w = max(200, int(img.width * ratio))
    new_h = max(150, int(img.height * ratio))
    img_small = img.resize((new_w, new_h), Image.LANCZOS)
    self._tk_img = ImageTk.PhotoImage(img_small)
    # 居中显示
    x = (cw - new_w) // 2 + 8
    y = (ch - new_h) // 2 + 8
    self.img_canvas.create_image(x, y, anchor="nw", image=self._tk_img)
```

## 关键点

- **必须持有 `PhotoImage` 引用**：`self._tk_img` 防止被 GC 回收
- **`add="+"`** 避免覆盖已有的绑定
- **`winfo_width()/winfo_height()`** 在 `<Configure>` 事件触发时已更新为新尺寸
- **居中显示**：通过 `(canvas_w - img_w) // 2` 计算偏移量
- **最小尺寸保护**：`cw < 100 or ch < 100` 时跳过，避免除以零
- 此模式下**不需要 Canvas 滚动条**（图片自动适配）
