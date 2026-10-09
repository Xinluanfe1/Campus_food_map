"""生成开发演示用的校园示意图（虚构示意图，不代表真实校园）。

用法（在项目根目录执行）：
    backend\\.venv\\Scripts\\python.exe scripts\\generate_demo_map.py

输出：
    data/maps/swjtu_xipu.png（2400 × 1600）

说明：该图片仅用于本地开发与界面测试，正式公开前必须替换为经过授权的真实校园底图。
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH = 2400
HEIGHT = 1600

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "maps" / "swjtu_xipu.png"

FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

# 与演示数据中的点位坐标保持一致（map_x、map_y 为 0 至 1 的归一化坐标）。
SHOP_POSITIONS = (
    ("示例一食堂", 0.20, 0.30),
    ("示例二食堂", 0.30, 0.32),
    ("示例面馆", 0.40, 0.35),
    ("示例早餐铺", 0.45, 0.40),
    ("示例奶茶店", 0.52, 0.45),
    ("示例烤肠摊", 0.58, 0.50),
    ("示例煎饼摊", 0.62, 0.55),
    ("示例烤冷面摊", 0.66, 0.58),
    ("示例水果摊", 0.70, 0.62),
)


def load_font(size: int) -> ImageFont.ImageFont:
    """加载中文字体，找不到系统字体时退回默认字体。"""

    for candidate in FONT_CANDIDATES:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def to_pixel(map_x: float, map_y: float) -> tuple[float, float]:
    """把归一化坐标换算为图片像素坐标。"""

    return map_x * WIDTH, map_y * HEIGHT


def main() -> None:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#eaf4e6")
    draw = ImageDraw.Draw(image)

    title_font = load_font(64)
    label_font = load_font(30)
    small_font = load_font(24)

    # 参考网格：每 10% 一条线，便于核对点位比例。
    for step in range(1, 10):
        x = WIDTH * step / 10
        y = HEIGHT * step / 10
        draw.line([(x, 0), (x, HEIGHT)], fill="#dcead6", width=3)
        draw.line([(0, y), (WIDTH, y)], fill="#dcead6", width=3)

    # 主干道与美食街
    draw.line([(0, HEIGHT * 0.24), (WIDTH, HEIGHT * 0.24)], fill="#e3e5e8", width=70)
    draw.line([(0, HEIGHT * 0.78), (WIDTH, HEIGHT * 0.78)], fill="#e3e5e8", width=70)
    draw.line([(WIDTH * 0.16, HEIGHT * 0.26), (WIDTH * 0.82, HEIGHT * 0.68)], fill="#f0ead9", width=90)

    # 校园建筑
    buildings = (
        ("教学楼", 0.08, 0.05, 0.30, 0.16),
        ("图书馆", 0.55, 0.06, 0.75, 0.18),
        ("学生宿舍区", 0.08, 0.84, 0.32, 0.95),
        ("体育场", 0.55, 0.82, 0.85, 0.96),
        ("实验楼", 0.82, 0.30, 0.95, 0.48),
    )
    for name, x1, y1, x2, y2 in buildings:
        box = (x1 * WIDTH, y1 * HEIGHT, x2 * WIDTH, y2 * HEIGHT)
        draw.rounded_rectangle(box, radius=18, fill="#dfe7f0", outline="#aab8c8", width=5)
        draw.text((box[0] + 24, box[1] + 20), name, font=title_font if name == "教学楼" else label_font, fill="#4e5969")

    # 湖区
    draw.ellipse((WIDTH * 0.36, HEIGHT * 0.60, WIDTH * 0.50, HEIGHT * 0.74), fill="#cfe6f5", outline="#9fc7e0", width=5)
    draw.text((WIDTH * 0.385, HEIGHT * 0.655), "人工湖", font=label_font, fill="#33627f")

    # 演示店铺点位：与演示数据的归一化坐标一一对应
    for name, map_x, map_y in SHOP_POSITIONS:
        x, y = to_pixel(map_x, map_y)
        size = 58
        draw.rounded_rectangle(
            (x - size, y - size, x + size, y + size),
            radius=14,
            fill="#f7d9b6",
            outline="#d08b3f",
            width=4,
        )
        draw.line([(x - 20, y), (x + 20, y)], fill="#b26a1e", width=5)
        draw.line([(x, y - 20), (x, y + 20)], fill="#b26a1e", width=5)
        draw.text((x - size, y + size + 8), name, font=small_font, fill="#7a4a12")

    # 标题与声明
    draw.text((60, 40), "西南交通大学犀浦校区（开发演示示意图）", font=title_font, fill="#2b3a2b")
    draw.text(
        (60, HEIGHT - 60),
        "本图为虚构示意图，仅用于本地开发与界面测试；点位与店铺均为演示数据，不代表真实校园信息。",
        font=small_font,
        fill="#7b8794",
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_PATH, format="PNG")
    print(f"演示底图已生成：{OUTPUT_PATH}（{WIDTH} × {HEIGHT}）")


if __name__ == "__main__":
    main()
