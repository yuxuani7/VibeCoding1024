# menu.py
import time
import math
import random
import pygame as pg
import numpy as np
from shader import gen_1024_field, set_variant

MATRIX_COLORS = [
    (0, 80, 0),
    (0, 160, 0),
    (150, 255, 150),
]

def menu_loop(screen, clock, width, height):
    variant_choice = random.choice(["vortex", "metaballs", "kaleido"])
    set_variant(variant_choice)

    font_big = pg.font.SysFont("Consolas, Menlo, Monospace", 36)
    font_small = pg.font.SysFont("Consolas, Menlo, Monospace", 20)
    font_easter = pg.font.SysFont("Consolas, Menlo, Monospace", 18)
    matrix_font = pg.font.SysFont("Consolas, Menlo, Monospace", 20)

    t0 = time.time()
    dt = 0.016

    char_width, char_height = matrix_font.size("0")
    matrix_spacing = max(char_width + 4, int(width * 0.02))
    matrix_streams = []
    matrix_surfaces = [
        {
            "0": matrix_font.render("0", True, col).convert_alpha(),
            "1": matrix_font.render("1", True, col).convert_alpha(),
        }
        for col in MATRIX_COLORS
    ]

    # ------------------ 初始化数字雨 ------------------
    def init_matrix_streams(w: int, h: int):
        nonlocal matrix_streams, matrix_spacing, char_width, char_height
        char_width, char_height = matrix_font.size("0")
        matrix_spacing = max(char_width + 4, int(w * 0.02))
        matrix_streams = []
        for x in range(0, w + matrix_spacing, matrix_spacing):
            length = random.randint(12, 26)
            stream = {
                "x": x,
                "y": random.uniform(-h, 0),
                "speed": random.uniform(90, 160),
                "length": length,
                "chars": [random.choice(["0", "1"]) for _ in range(length)]
            }
            matrix_streams.append(stream)

    # ------------------ 绘制数字雨 ------------------
    def update_and_draw_matrix(surf: pg.Surface, dt_sec: float, exclude_rects: list[pg.Rect]):
        if not matrix_streams:
            return
        height_local = surf.get_height()
        width_local = surf.get_width()
        for stream in matrix_streams:
            # 更新 y 位置
            stream["y"] += stream["speed"] * dt_sec
            max_tail = stream["y"] - stream["length"] * char_height
            if max_tail > height_local + char_height:
                stream["y"] = random.uniform(-height_local, 0)
                stream["speed"] = random.uniform(90, 160)
                stream["length"] = random.randint(12, 26)
                stream["chars"] = [random.choice(["0", "1"]) for _ in range(stream["length"])]

            # 小概率刷新字符，营造“数字流动”的感觉
            for i in range(len(stream["chars"])):
                if random.random() < 0.02:
                    stream["chars"][i] = random.choice(["0", "1"])

            for idx in range(stream["length"]):
                char_y = stream["y"] - idx * char_height
                if char_y < -char_height or char_y > height_local:
                    continue
                color_idx = 2 if idx == 0 else (1 if idx < 4 else 0)
                glyph = matrix_surfaces[color_idx][stream["chars"][idx]]
                dest_rect = pg.Rect(stream["x"], int(char_y), char_width, char_height)
                if stream["x"] > width_local:
                    continue
                if any(dest_rect.colliderect(ex) for ex in exclude_rects):
                    continue
                surf.blit(glyph, dest_rect.topleft)

    # ============================
    # ✅ 自适应背景画布尺寸
    # ============================
    surf_w = int(width * 0.7)
    surf_h = int(height * 0.35)

    # 🐍 蛇动画参数
    node_spacing = 8
    snake_len = 50
    snake_speed = 100
    snake_radius = max(2, int(min(width, height) * 0.004))
    margin = max(8, int(min(width, height) * 0.008))

    # 🍎 苹果
    apple_offset = None
    apple_radius = max(4, int(min(width, height) * 0.006))
    apple_color = (240, 90, 90)

    # ✨ 漂浮抖动
    float_amp = 3
    float_freq = 1.0

    easter_egg_triggered = False

    init_matrix_streams(width, height)

    # ------------------ 蛇路径工具 ------------------
    def get_pos_along_path(offset, t, float_idx=0):
        if offset < path_w:
            x = x0 + margin + offset
            y = y0 + margin
            angle = -math.pi/2
        elif offset < path_w + path_h:
            x = x0 + margin + path_w
            y = y0 + margin + (offset - path_w)
            angle = 0
        elif offset < 2*path_w + path_h:
            x = x0 + margin + path_w - (offset - path_w - path_h)
            y = y0 + margin + path_h
            angle = math.pi/2
        else:
            x = x0 + margin
            y = y0 + margin + path_h - (offset - 2*path_w - path_h)
            angle = math.pi
        offset_float = float_amp * math.sin(2 * math.pi * float_freq * t + float_idx * 0.2)
        fx = x + offset_float * math.cos(angle)
        fy = y + offset_float * math.sin(angle)
        return fx, fy

    def spawn_apple():
        nonlocal apple_offset
        attempts = 0
        while attempts < 100:
            candidate = random.uniform(0, path_len)
            too_close = False
            for i in range(snake_len):
                seg_offset = (head_offset - i * node_spacing) % path_len
                if abs(candidate - seg_offset) < node_spacing * 1.5:
                    too_close = True
                    break
            if not too_close:
                apple_offset = candidate
                return
            attempts += 1
        apple_offset = None

    # ============================
    # 主循环
    # ============================
    while True:
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return "QUIT"
            if e.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((e.w, e.h), pg.RESIZABLE)
                width, height = screen.get_size()
                surf_w = int(width * 0.7)
                surf_h = int(height * 0.35)
                snake_radius = max(2, int(min(width, height) * 0.004))
                margin = max(8, int(min(width, height) * 0.008))
                apple_radius = max(4, int(min(width, height) * 0.006))
                init_matrix_streams(width, height)
            if e.type == pg.KEYDOWN:
                if e.key in (pg.K_RETURN, pg.K_SPACE):
                    return "START"
                if e.key == pg.K_ESCAPE:
                    return "QUIT"

        t = time.time() - t0
        img = gen_1024_field(surf_w, surf_h, t)
        frame = pg.surfarray.make_surface(img)

        screen.fill((12, 14, 24))

        x0 = width//2 - frame.get_width()//2
        y0 = height//2 - frame.get_height()//2 - 40
        exclude_rects = [
            pg.Rect(x0, y0, frame.get_width(), frame.get_height()),
            pg.Rect(width//2 - 260, y0 + frame.get_height() + 6, 520, 140),
        ]
        update_and_draw_matrix(screen, dt, exclude_rects)
        screen.blit(frame, (x0, y0))

        # 蛇的路径
        path_w = frame.get_width() - 2*margin
        path_h = frame.get_height() - 2*margin
        path_len = 2*(path_w + path_h)
        max_len = int(path_len / node_spacing) - 5
        head_offset = (t * snake_speed) % path_len

        # 🍎 苹果刷新
        if apple_offset is None and snake_len < max_len:
            if random.random() < 0.01:
                spawn_apple()

        # 🍎 绘制苹果
        if apple_offset is not None:
            ax, ay = get_pos_along_path(apple_offset, t)
            pg.draw.circle(screen, apple_color, (int(ax), int(ay)), apple_radius)

        # 🐍 绘制蛇
        for i in range(snake_len):
            seg_offset = (head_offset - i * node_spacing) % path_len
            sx, sy = get_pos_along_path(seg_offset, t, i)
            intensity = max(0.3, 1 - i / snake_len)
            color = (int(80 * intensity + 175 * (1 - intensity)),
                     int(220 * intensity),
                     int(120 * intensity))
            pg.draw.circle(screen, color, (int(sx), int(sy)), snake_radius)

        # 🐍 吃苹果
        if apple_offset is not None:
            head_x, head_y = get_pos_along_path(head_offset, t)
            apple_x, apple_y = get_pos_along_path(apple_offset, t)
            dist = math.hypot(head_x - apple_x, head_y - apple_y)
            if dist < snake_radius + apple_radius:
                snake_len += 5
                apple_offset = None
                if snake_len >= max_len:
                    easter_egg_triggered = True

        # 标题 & 提示
        title = font_big.render("Vibe Coding 1024 — Snake 1024", True, (220, 230, 240))
        screen.blit(title, (width//2 - title.get_width()//2, 30))
        tip = font_small.render("Press ENTER/SPACE to Start | ESC to Quit", True, (140, 150, 170))
        screen.blit(tip, (width//2 - tip.get_width()//2, y0 + frame.get_height() + 12))

        # 🐣 彩蛋
        if easter_egg_triggered:
            blessing = [
                "# keep coding, keep creating.",
                "# may your bugs be shallow and your merges be clean ✨"
            ]
            for i, line in enumerate(blessing):
                line_surf = font_easter.render(line, True, (170, 255, 170))
                screen.blit(line_surf, (width//2 - line_surf.get_width()//2,
                                        y0 + frame.get_height() + 12 + (i+1)*24))

        pg.display.flip()
        dt = clock.tick(60) / 1000.0