# game.py
from __future__ import annotations

import random
from collections import deque
from typing import Deque, Set, Tuple

import pygame as pg

Vec2 = Tuple[int, int]

# ===== 基础尺寸 =====
CELL = 16
GRID_SIZE = 64
BOARD_PIXELS = CELL * GRID_SIZE
TOTAL_CELLS = GRID_SIZE * GRID_SIZE  # 64x64 = 4096

# ===== 渲染&布局 =====
MOVE_FPS = 10
RENDER_FPS = 60
PIXEL_PERFECT = True

HUD_RESERVED_HEIGHT = 64
HUD_TOP_MARGIN = 16
BOARD_BOTTOM_MARGIN = 24

# ===== 颜色 =====
BG_DARK = (18, 18, 18)
BOARD_BG = (28, 28, 28)

# 🐍 鲜艳天蓝色蛇身配色
SNAKE_HEAD_COLOR = (80, 200, 255)      # 明亮天蓝（比原本更鲜亮）
SNAKE_BODY_COLOR = (45, 160, 245)      # 稍深的天蓝，层次更清晰
SNAKE_OUTLINE_COLOR = (20, 90, 180)    # 深蓝描边，增强立体感
SNAKE_SHADOW_COLOR = (0, 0, 0, 170)    # 阴影略微加强以衬托亮色

HUD_TEXT_COLOR = (230, 230, 230)

# 豆子外观
# 柔和绿豆
GREEN_BEAN_FILL = (95, 180, 130)        # 原本很亮 → 降低饱和
GREEN_BEAN_OUTLINE = (220, 235, 220)    # 微灰白描边
GREEN_BEAN_HL = (240, 250, 240, 130)    # 高光半透明
GREEN_BEAN_SHADOW = (0, 0, 0, 110)      # 阴影更淡

# 柔和橙豆
ORANGE_BEAN_FILL = (230, 150, 80)       # 降低亮度
ORANGE_BEAN_OUTLINE = (240, 225, 210)   # 微暖白描边
ORANGE_BEAN_HL = (255, 245, 240, 120)   # 柔光
ORANGE_BEAN_SHADOW = (0, 0, 0, 110)     # 阴影更淡

# 柔和红豆
RED_BEAN_FILL = (210, 90, 100)          # 降饱和度的粉红红
RED_BEAN_OUTLINE = (240, 230, 230)      # 微灰白
RED_BEAN_HL = (250, 240, 240, 130)      # 柔光
RED_BEAN_SHADOW = (0, 0, 0, 120)        # 阴影更淡

# 彩蛋配色
EASTER_TEXT = (170, 255, 170)
EASTER_BACK = (0, 0, 0, 160)

FONT_NAME = "Consolas, Menlo, Monospace"

# ===== 键位 =====
DIRECTION_KEYS = {
    pg.K_UP: (0, -1), pg.K_w: (0, -1),
    pg.K_DOWN: (0, 1), pg.K_s: (0, 1),
    pg.K_LEFT: (-1, 0), pg.K_a: (-1, 0),
    pg.K_RIGHT: (1, 0), pg.K_d: (1, 0),
}

# ===== 生成节奏 =====
SPAWN_BATCH_INTERVAL = 0.5  # 每 0.5 秒生成一批

# ===== 分段总量上限（相对所有格子数量）=====
CAP_EARLY = 0.30  # <300 分，不超过 30%
CAP_PEAK  = 0.50  # 300~799 分，不超过 50%
CAP_LATE  = 0.80  # ≥800 分，不超过 80%（含 SPRINT）

# 可选：安全硬上限，避免过多绘制导致掉帧
MAX_BEANS_HARD_CAP = 1600

INITIAL_RED_BEANS = 96
MAX_RED_BEAN_COUNT = 200

class SnakeGame:
    def __init__(self, rng_seed: int | None = None):
        self.rng = random.Random(rng_seed)
        self.move_interval = 1.0 / MOVE_FPS

        self.board_surface = pg.Surface((BOARD_PIXELS, BOARD_PIXELS))
        self.entities_surface = pg.Surface((BOARD_PIXELS, BOARD_PIXELS), pg.SRCALPHA)

        self.font_hud = pg.font.SysFont(FONT_NAME, 20)
        self.font_small = pg.font.SysFont(FONT_NAME, 18)
        self.font_large = pg.font.SysFont(FONT_NAME, 48)
        self.high_score = 0

        self.reset()

    # ====== 曲线：抛物线式难度（比例） ======
    @staticmethod
    def green_weight(score: int) -> float:
        # 绿色豆子更充盈：整体数量提高
        if score < 300:
            return 5.0 + score / 120.0
        elif score < 800:
            return max(3.0, 7.0 - (score - 300) / 180.0)
        else:
            return 4.5 + (score - 800) / 80.0

    @staticmethod
    def orange_weight(score: int) -> float:
        # 早期适中，300 分后显著降低，比分超过 512 后不再生成
        if score < 150:
            return 1.2 + score / 200.0
        elif score < 300:
            return 1.8 + (score - 150) / 180.0
        elif score < 512:
            return max(0.2, 1.0 - (score - 300) / 90.0)
        else:
            return 0.0

    @staticmethod
    def batch_size(score: int) -> int:
        # 每批数量：早期3 / 中期5 / 后期4 / 冲刺3
        if score < 300:
            return 3
        elif score < 800:
            return 5
        elif score < 1000:
            return 4
        else:
            return 3

    @staticmethod
    def max_beans(score: int) -> int:
        # 相对全图格子数量的百分比上限 + 安全硬上限
        if score < 300:
            cap_ratio = CAP_EARLY
        elif score < 800:
            cap_ratio = CAP_PEAK
        else:
            cap_ratio = CAP_LATE
        cap_by_ratio = int(TOTAL_CELLS * cap_ratio)
        return min(cap_by_ratio, MAX_BEANS_HARD_CAP)

    # ====== 初始化/重置 ======
    def reset(self) -> None:
        center = GRID_SIZE // 2
        initial = [(center + offset, center) for offset in range(3, -5, -1)]
        self.snake: Deque[Vec2] = deque(initial)
        self.snake_set: Set[Vec2] = set(initial)
        self.direction: Vec2 = (1, 0)
        self.pending_direction: Vec2 = self.direction
        self.direction_locked = False

        # 分数 = 长度
        self.score = len(self.snake)
        self.high_score = max(self.high_score, self.score)

        # 豆子集合（按时间批量生成）
        self.green_beans: Set[Vec2] = set()
        self.orange_beans: Set[Vec2] = set()
        self.red_beans: Set[Vec2] = set()
        self.grow_pending = 0

        # 计时器
        self.move_timer = 0.0
        self.spawn_timer = 0.0

        # 状态
        self.dead = False
        self.restart_requested = False
        self.exit_to_menu = False
        self.easter_triggered = False

        # 开局铺一些豆子：橙:绿 ≈ 1:2（但不超过当前上限的 60%）
        self._seed_initial_beans()
        self._seed_initial_red_beans()

    # ====== 输入 ======
    def handle_keydown(self, key: int) -> None:
        if self.dead or self.easter_triggered:
            if key == pg.K_r: self.restart_requested = True
            elif key == pg.K_ESCAPE: self.exit_to_menu = True
            return
        candidate = DIRECTION_KEYS.get(key)
        if candidate is None or self.direction_locked:
            return
        opposite = (-self.direction[0], -self.direction[1])
        if candidate == opposite:
            return
        self.pending_direction = candidate
        self.direction_locked = True

    # ====== 每帧更新 ======
    def update(self, dt: float) -> None:
        if self.dead:
            return

        # 网格移动
        self.move_timer += dt
        while self.move_timer >= self.move_interval:
            self.move_timer -= self.move_interval
            self._advance_one_step()
            self.direction_locked = False
            if self.dead:
                return

        # 定时生成豆子批次（与是否吃豆无关）
        if not self.easter_triggered:
            self.spawn_timer += dt
            while self.spawn_timer >= SPAWN_BATCH_INTERVAL:
                self.spawn_timer -= SPAWN_BATCH_INTERVAL
                self._spawn_batch()

        # 彩蛋检测：分数≥1048 且 场上无红豆且橙豆≤256
        if (not self.easter_triggered
                and self.score >= 1024
                and len(self.red_beans) == 0
                and len(self.orange_beans) <= 256):
            self.easter_triggered = True

    # ====== 单步推进 ======
    def _advance_one_step(self) -> None:
        if self.easter_triggered:
            return  # 彩蛋后如需继续移动，移除此 return

        self.direction = self.pending_direction
        hx, hy = self.snake[0]
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)

        # 撞墙/撞自己
        if not (0 <= new_head[0] < GRID_SIZE and 0 <= new_head[1] < GRID_SIZE):
            self.dead = True
            return
        tail = self.snake[-1]
        if new_head in self.snake_set and new_head != tail:
            self.dead = True
            return

        # 放置新头
        self.snake.appendleft(new_head)
        self.snake_set.add(new_head)

        extra_removals = 0

        # 吃豆
        if new_head in self.green_beans:
            self.green_beans.remove(new_head)
            self.grow_pending += 2
        elif new_head in self.orange_beans:
            self.orange_beans.remove(new_head)
            extra_removals += 1  # 净 -1
        elif new_head in self.red_beans:
            self.red_beans.remove(new_head)
            extra_removals += 5  # 净 -5

        # 基础步进：优先消耗生长储备，否则移除尾巴；缩短类豆子仍然强制额外移除
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            removed = self.snake.pop()
            self.snake_set.remove(removed)
        while extra_removals > 0:
            if self.grow_pending > 0:
                self.grow_pending -= 1
            else:
                if len(self.snake) == 0:
                    self.dead = True
                    return
                removed_extra = self.snake.pop()
                self.snake_set.remove(removed_extra)
                if len(self.snake) == 0:
                    self.dead = True
                    return
            extra_removals -= 1

        # 分数 = 长度
        self.score = len(self.snake)
        if self.score > self.high_score:
            self.high_score = self.score

    # ====== 批量生成豆子 ======
    def _spawn_batch(self) -> None:
        # 不超过容量
        capacity = self.max_beans(self.score) - (len(self.green_beans) + len(self.orange_beans) + len(self.red_beans))
        if capacity <= 0:
            return

        want = min(capacity, self.batch_size(self.score))
        gw = self.green_weight(self.score)
        ow = self.orange_weight(self.score)
        total_w = gw + ow
        if total_w <= 0:
            return

        for _ in range(want):
            pick = self.rng.random() * total_w
            kind = "green" if pick < gw else "orange"
            # ≥512 分时仅生成绿豆
            if kind == "orange" and self.score >= 512:
                kind = "green"

            cell = self._random_free_cell()
            if cell is None:
                break
            if kind == "green":
                self.green_beans.add(cell)
            else:
                self.orange_beans.add(cell)

    def _seed_initial_beans(self) -> None:
        # 初始铺一些，但不超过当期上限的 60%
        cap = self.max_beans(self.score)
        target_total = max(0, int(cap * 0.6))
        need = max(0, target_total - (len(self.green_beans) + len(self.orange_beans) + len(self.red_beans)))

        for _ in range(need):
            kind = "green" if self.rng.random() < (2 / 3) else "orange"  # 约 1:2（橙:绿）
            if kind == "orange" and self.orange_weight(self.score) <= 0.0:
                kind = "green"
            cell = self._random_free_cell()
            if cell is None:
                break
            if kind == "green":
                self.green_beans.add(cell)
            else:
                self.orange_beans.add(cell)

    def _seed_initial_red_beans(self) -> None:
        target = min(INITIAL_RED_BEANS, MAX_RED_BEAN_COUNT)
        for _ in range(target):
            if len(self.red_beans) >= MAX_RED_BEAN_COUNT:
                break
            cell = self._random_free_cell()
            if cell is None:
                break
            self.red_beans.add(cell)

    def _random_free_cell(self) -> Vec2 | None:
        tries = 0
        occupied = self.snake_set | self.green_beans | self.orange_beans | self.red_beans
        while tries < 500:
            cell = (self.rng.randrange(GRID_SIZE), self.rng.randrange(GRID_SIZE))
            if cell not in occupied:
                return cell
            tries += 1
        return None

    # ====== 渲染 ======
    def _compute_board_dest(self, sw: int, sh: int):
        available_height = max(1, sh - HUD_RESERVED_HEIGHT - BOARD_BOTTOM_MARGIN)
        scale_float = min(sw / BOARD_PIXELS, available_height / BOARD_PIXELS)
        if scale_float <= 0:
            scale_float = 1.0
        use_integer_scale = PIXEL_PERFECT and scale_float >= 1.0
        if use_integer_scale:
            scale = max(1, int(scale_float))
            dest_size = (BOARD_PIXELS * scale, BOARD_PIXELS * scale)
            scale_used = float(scale)
        else:
            dest_size = (max(1, int(BOARD_PIXELS * scale_float)),) * 2
            scale_used = dest_size[0] / BOARD_PIXELS
        dest_rect = pg.Rect((0, 0), dest_size)
        dest_rect.centerx = sw // 2
        top_space = HUD_RESERVED_HEIGHT
        vertical_space = max(0, available_height - dest_size[1])
        dest_rect.top = top_space + vertical_space // 2
        return dest_rect, scale_used, use_integer_scale, dest_size

    def render(self, screen: pg.Surface, code_wall: CodeWall | None = None) -> tuple[pg.Rect, float]:
        screen.fill(BG_DARK)
        self.board_surface.fill(BOARD_BG)
        self.entities_surface.fill((0, 0, 0, 0))

        # 画豆子 & 蛇
        self._draw_beans(self.entities_surface)
        self._draw_snake(self.entities_surface)

        # 计算棋盘贴图位置&缩放
        sw, sh = screen.get_size()
        dest_rect, scale_used, use_integer_scale, dest_size = self._compute_board_dest(sw, sh)

        # 缩放并贴到屏幕
        if use_integer_scale:
            if int(scale_used) == 1:
                board_to_blit = self.board_surface
                entities_to_blit = self.entities_surface
            else:
                board_to_blit = pg.transform.scale(self.board_surface, dest_size)
                entities_to_blit = pg.transform.scale(self.entities_surface, dest_size)
        else:
            board_to_blit = (self.board_surface if self.board_surface.get_size() == dest_size
                             else pg.transform.smoothscale(self.board_surface, dest_size))
            entities_to_blit = (self.entities_surface if self.entities_surface.get_size() == dest_size
                                else pg.transform.smoothscale(self.entities_surface, dest_size))
        screen.blit(board_to_blit, dest_rect)

        # 代码雨：整盘视为激活（棋盘内会淡化）
        if code_wall is not None:
            sub_side = GRID_SIZE // 16  # 以 16x16 cell 为一子块
            all_active = set(range(max(1, sub_side * sub_side)))
            code_wall.draw(
                screen,
                board_rect=dest_rect,
                board_scale=scale_used,
                cell_pixels=CELL,
                subgrid_cells=16,
                active_subgrids=all_active,
                grid_cells=GRID_SIZE,
                subgrid_cols=max(1, sub_side),
                hide_margin_px=CELL // 2,
            )

        # 让实体在最前
        screen.blit(entities_to_blit, dest_rect)

        # HUD / 覆盖层
        self._draw_hud(screen, dest_rect)
        if self.dead:
            self._draw_death_overlay(screen)
        if self.easter_triggered:
            self._draw_easter_overlay(screen)
        return dest_rect, scale_used

    # --- 画豆子 ---
    def _draw_beans(self, surface: pg.Surface) -> None:
        for pos in self.green_beans:
            self._draw_round_item(surface, pos, GREEN_BEAN_FILL, GREEN_BEAN_OUTLINE, GREEN_BEAN_HL, GREEN_BEAN_SHADOW)
        for pos in self.orange_beans:
            self._draw_round_item(surface, pos, ORANGE_BEAN_FILL, ORANGE_BEAN_OUTLINE, ORANGE_BEAN_HL, ORANGE_BEAN_SHADOW)
        for pos in self.red_beans:
            self._draw_round_item(surface, pos, RED_BEAN_FILL, RED_BEAN_OUTLINE, RED_BEAN_HL, RED_BEAN_SHADOW)

    def _draw_round_item(
        self, surface: pg.Surface, cell: Vec2,
        fill_color: Tuple[int, int, int],
        outline_color: Tuple[int, int, int],
        hl_color: Tuple[int, int, int, int],
        shadow_color: Tuple[int, int, int, int],
    ) -> None:
        item = pg.Surface((CELL, CELL), pg.SRCALPHA)
        center = (CELL // 2, CELL // 2)
        base_r = max(4, CELL // 2 - 2)

        # 阴影
        pg.draw.circle(item, shadow_color, (center[0] + 1, center[1] + 2), base_r)

        # 描边
        pg.draw.circle(item, outline_color, center, base_r, width=2)

        # 填充
        pg.draw.circle(item, fill_color, center, base_r - 1)

        # 高光
        hl_center = (center[0] - base_r // 2, center[1] - base_r // 2)
        hl_r = max(2, base_r // 3)
        pg.draw.circle(item, hl_color, hl_center, hl_r)

        surface.blit(item, (cell[0] * CELL, cell[1] * CELL))

    # --- 画蛇 ---
    def _draw_snake(self, surface: pg.Surface) -> None:
        if not self.snake:
            return
        segments = list(self.snake)
        head_cell = segments[0]
        self._draw_snake_segment(surface, head_cell, fill_color=SNAKE_HEAD_COLOR, is_head=True)
        for segment in segments[1:]:
            self._draw_snake_segment(surface, segment, fill_color=SNAKE_BODY_COLOR, is_head=False)

    def _draw_snake_segment(self, surface: pg.Surface, cell: Vec2, *, fill_color: Tuple[int, int, int], is_head: bool) -> None:
        seg_surf = pg.Surface((CELL, CELL), pg.SRCALPHA)

        padding = max(1, CELL // 10)
        outline_rect = pg.Rect(padding, padding, CELL - padding * 2, CELL - padding * 2)

        # 阴影（略偏移，方形）
        shadow_rect = outline_rect.move(2, 3)
        pg.draw.rect(seg_surf, SNAKE_SHADOW_COLOR, shadow_rect)

        # 外框
        pg.draw.rect(seg_surf, SNAKE_OUTLINE_COLOR, outline_rect, width=max(2, CELL // 6))

        # 填充方形主体
        fill_rect = outline_rect.inflate(-max(4, CELL // 6), -max(4, CELL // 6))
        pg.draw.rect(seg_surf, fill_color, fill_rect)

        # 条纹纹理，增强区分度
        accent_color = (
            min(255, fill_color[0] + 35),
            min(255, fill_color[1] + 35),
            min(255, fill_color[2] + 35),
        )
        stripe_width = max(2, CELL // 6)
        for idx, x in enumerate(range(fill_rect.left, fill_rect.right, stripe_width * 2)):
            stripe_rect = pg.Rect(x, fill_rect.top, stripe_width, fill_rect.height)
            pg.draw.rect(seg_surf, accent_color if (idx + (1 if is_head else 0)) % 2 == 0 else fill_color, stripe_rect)

        # 头部额外高光与眼睛
        if is_head:
            highlight_rect = pg.Rect(
                fill_rect.left + fill_rect.width // 8,
                fill_rect.top + fill_rect.height // 8,
                max(3, fill_rect.width // 2),
                max(3, fill_rect.height // 2),
            )
            highlight_surface = pg.Surface(highlight_rect.size, pg.SRCALPHA)
            highlight_surface.fill((
                min(255, fill_color[0] + 60),
                min(255, fill_color[1] + 60),
                min(255, fill_color[2] + 60),
                140,
            ))
            seg_surf.blit(highlight_surface, highlight_rect.topleft)

            eye_size = max(2, CELL // 6)
            eye_color = (20, 30, 60)
            left_eye = pg.Rect(
                fill_rect.left + fill_rect.width // 6,
                fill_rect.top + fill_rect.height // 4,
                eye_size,
                eye_size,
            )
            right_eye = left_eye.move(fill_rect.width // 2, 0)
            pg.draw.rect(seg_surf, eye_color, left_eye)
            pg.draw.rect(seg_surf, eye_color, right_eye)

        surface.blit(seg_surf, (cell[0] * CELL, cell[1] * CELL))

    # --- HUD & 覆盖层 ---
    def _phase_name(self, score: int) -> str:
        if score < 300:
            return "EARLY"
        elif score < 800:
            return "PEAK"
        elif score < 1000:
            return "LATE"
        else:
            return "SPRINT"

    def _draw_hud(self, screen: pg.Surface, board_rect: pg.Rect) -> None:
        phase = self._phase_name(self.score)
        info = (f"Score: {self.score}   High: {self.high_score}   Phase: {phase}   "
                f"Beans G/O/R: {len(self.green_beans)}/{len(self.orange_beans)}/{len(self.red_beans)}")
        info_surf = self.font_hud.render(info, True, HUD_TEXT_COLOR)
        info_y = HUD_TOP_MARGIN
        if board_rect.top - info_surf.get_height() - 12 > HUD_TOP_MARGIN:
            info_y = board_rect.top - info_surf.get_height() - 12
        screen.blit(info_surf, (20, info_y))

    def _draw_death_overlay(self, screen: pg.Surface) -> None:
        overlay = pg.Surface(screen.get_size(), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        cx = screen.get_width() // 2
        cy = screen.get_height() // 2
        title = self.font_large.render("GAME OVER", True, RED_BEAN_FILL)
        score_text = self.font_hud.render(f"Final Score: {self.score}", True, HUD_TEXT_COLOR)
        prompt = self.font_small.render("R — Restart    ESC — Menu", True, HUD_TEXT_COLOR)
        screen.blit(title, (cx - title.get_width() // 2, cy - 70))
        screen.blit(score_text, (cx - score_text.get_width() // 2, cy - 20))
        screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 30))

    def _draw_easter_overlay(self, screen: pg.Surface) -> None:
        overlay = pg.Surface(screen.get_size(), pg.SRCALPHA)
        overlay.fill(EASTER_BACK)
        screen.blit(overlay, (0, 0))

        cx = screen.get_width() // 2
        cy = screen.get_height() // 2

        title = self.font_large.render("PERFECT 1024", True, EASTER_TEXT)
        line1 = self.font_hud.render("# system stable — zero errors, minimal warnings.", True, EASTER_TEXT)
        line2 = self.font_hud.render("# mission complete — the grid bows to your logic.", True, EASTER_TEXT)
        line3 = self.font_hud.render("# may every line you write light up the dark.", True, EASTER_TEXT)
        prompt = self.font_small.render("R — Restart    ESC — Menu", True, HUD_TEXT_COLOR)

        screen.blit(title, (cx - title.get_width() // 2, cy - 90))
        screen.blit(line1, (cx - line1.get_width() // 2, cy - 30))
        screen.blit(line2, (cx - line2.get_width() // 2, cy + 6))
        screen.blit(line3, (cx - line3.get_width() // 2, cy + 42))
        screen.blit(prompt, (cx - prompt.get_width() // 2, cy + 96))

# ---------- 主循环 ----------
def game_loop(code_wall) -> str:
    clock = pg.time.Clock()
    game = SnakeGame()

    while True:
        dt_ms = clock.tick(RENDER_FPS)
        dt = dt_ms / 1000.0
        screen = pg.display.get_surface()
        if screen is None:
            continue

        for event in pg.event.get():
            if event.type == pg.QUIT:
                return "QUIT"
            if event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)
            elif event.type == pg.KEYDOWN:
                game.handle_keydown(event.key)

        game.update(dt)

        # 代码雨：根据分数调整强度，并推进（advance 接受毫秒）
        if code_wall is not None:
            code_wall.set_score(game.score)
            code_wall.advance(dt_ms, screen=screen, hud_height=HUD_RESERVED_HEIGHT)

        # 渲染：棋盘 -> 代码雨 -> 实体
        game.render(screen, code_wall=code_wall)

        pg.display.flip()

        if game.dead or game.easter_triggered:
            if game.restart_requested:
                game.reset()
                continue
            if game.exit_to_menu:
                return "MENU"
