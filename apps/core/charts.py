"""SVG grafiklari uchun geometriya (server tomonida hisoblanadi, JS kerak emas)."""

COLORS = ["rgb(var(--accent))", "rgb(var(--ok))", "rgb(var(--warn))", "rgb(var(--danger))", "rgb(var(--violet))", "rgb(var(--ink-3))"]


def donut(values, colors=None):
    """[(label, value), ...] -> segmentlar (stroke-dasharray, r=15.9155 => aylana uzunligi 100)."""
    colors = colors or COLORS
    total = sum(v for _l, v in values) or 1
    out, offset = [], 0.0
    for i, (label, v) in enumerate(values):
        pct = v * 100 / total
        out.append({"label": label, "value": v, "pct": round(pct), "dash": f"{pct:.3f} {100 - pct:.3f}", "offset": f"{-offset:.3f}", "color": colors[i % len(colors)]})
        offset += pct
    return out


def line_area(points, width=600, height=200, pad_left=40, pad_right=10, pad_top=20, pad_bottom=30, ticks=4):
    """[(label, value), ...] -> chiziq/maydon path, nuqtalar, y o'qi belgilari. Bitta shkala ishlatiladi."""
    if not points:
        return None
    vmax = max(v for _l, v in points) or 1
    # Shkala yuqori chegarasini "chiroyli" songa yaxlitlash
    step = max(1, -(-vmax // ticks))
    top = step * ticks
    plot_w = width - pad_left - pad_right
    plot_h = height - pad_top - pad_bottom
    n = max(len(points) - 1, 1)
    xy = [(pad_left + i * plot_w / n, pad_top + plot_h - v / top * plot_h) for i, (_l, v) in enumerate(points)]
    line = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    base = pad_top + plot_h
    area = f"{line} L{xy[-1][0]:.1f},{base:.1f} L{xy[0][0]:.1f},{base:.1f} Z"
    return {
        "width": width, "height": height, "line": line, "area": area,
        "dots": [{"x": f"{x:.1f}", "y": f"{y:.1f}", "label": l, "value": v} for (x, y), (l, v) in zip(xy, points)],
        "grid": [{"y": f"{pad_top + plot_h - k * plot_h / ticks:.1f}", "label": k * step} for k in range(ticks + 1)],
        "x0": pad_left, "x1": width - pad_right, "label_y": height - 8,
    }
