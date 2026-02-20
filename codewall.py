# codewall.py
from __future__ import annotations

import random
from typing import Set

import pygame as pg

# ---------------- CodeWall（代码雨） ----------------

SUCCESS_COLOR = (0, 255, 128)
ERROR_COLOR = (255, 80, 80)
NEUTRAL_COLOR = (230, 230, 230)

SUCCESS_TOKENS = [
    "BUILD SUCCESS",
    "ALL TESTS PASS",
    "DEPLOY ✓",
    "PIPELINE GREEN",
    "SHIP IT!",
    "1024 UNLOCKED",
    "LEVEL CLEARED",
    "SCORE++",
    "COMMIT APPROVED",
    "GG WP",
]

ERROR_TOKENS = [
    "ERROR 404",
    "ERROR 500",
    "SEGFAULT",
    "ROLLBACK",
    "TIMEOUT",
    "PANIC!",
    "BUILD FAILED",
    "MERGE CONFLICT",
]

CODE_TOKENS = [
    "git status",
    "git push origin main",
    "git checkout -b feature/1024",
    "python main.py",
    "pip install pygame",
    "docker run --rm -it",
    "kubectl get pods",
    "npm install",
    "npm run build",
    "curl -s https://example.com",
    "wget https://openai.com",
    "ssh user@server",
    "code .",
    "make && make install",
    "pytest -q",
    "npm test",
    "yarn dev",
    "pnpm install",
    "printf(\"hello\\n\");",
    "console.log(' ');",
    "sudo service restart",
    "chmod +x deploy.sh",
    "ls -al",
    "cat README.md",
    "tail -f /var/log/app.log",
    "watch -n1 sensors",
    "top -o cpu",
    "htop",
    "systemctl",
    "tmux attach",
    "ps aux",
    "grep py",
    "ifconfig",
    "dig host",
    "nslookup",
    "scp file",
    "rsync -av",
    "g++ build",
    "clang fmt",
    "cargo run",
    "go test",
    "rustup up",
    "node -v",
    "python -m",
    "pwsh proc",
    "brew up",
    "aws s3 ls",
    "gcloud init",
    "helm install",
    "terraform",
    "kill -9",
    "whoami",
    "pwd",
    "echo 1024",
    "exit",
]
class _Glyph:
    __slots__ = ("text", "x", "y", "vx", "vy", "color", "alpha", "surface")
    def __init__(self, text, x, y, vx, vy, color, alpha, surface):
        self.text = text; self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.color = color; self.alpha = alpha; self.surface = surface

class CodeWall:
    def __init__(
        self,
        font_name="Consolas, Menlo, Monospace",
        font_size=16,
        density=0.12,
        speed=(30, 120),
        horizontal_speed=(10, 40),
        alpha_range=(140, 220),
        greenish=True,
        seed=None,
        max_token_len: int | None = 24,
    ):
        pg.font.init()
        self.rng = random.Random(seed)
        self.font = pg.font.SysFont(font_name, font_size)
        self.font_size = font_size
        self.density = density
        self.speed = speed
        self.hspeed = horizontal_speed
        self.alpha_range = alpha_range
        self.max_token_len = max_token_len
        self._theme = greenish  # kept for backward compatibility

        self.success_tokens = self._trim_tokens(SUCCESS_TOKENS)
        self.error_tokens = self._trim_tokens(ERROR_TOKENS)
        self.normal_tokens = self._trim_tokens(CODE_TOKENS)

        self.score = 0
        self.success_weight = self._calc_success_weight(self.score)
        self.error_weight = 1.0
        self.normal_weight = 1.0

        self.glyphs: list[_Glyph] = []
        self.last_layout_key = None
        self.bounds_rect = pg.Rect(0, 0, 0, 0)

    # ---------- 内部工具 ----------
    def _trim_tokens(self, tokens: list[str]) -> list[str]:
        if self.max_token_len is None:
            return list(tokens)
        return [
            tok if len(tok) <= self.max_token_len else tok[: self.max_token_len]
            for tok in tokens
        ]

    def _calc_success_weight(self, score: int) -> float:
        if score >= 90:
            return 10.0
        if score >= 50:
            return 6.0
        if score >= 20:
            return 3.0
        return 1.0

    def set_score(self, score: int) -> None:
        score = max(0, int(score))
        if score == self.score:
            return
        self.score = score
        self.success_weight = self._calc_success_weight(self.score)

    def _random_token(self) -> tuple[str, tuple[int, int, int]]:
        groups: list[tuple[float, list[str], tuple[int, int, int]]] = []
        if self.normal_tokens:
            groups.append((self.normal_weight, self.normal_tokens, NEUTRAL_COLOR))
        if self.error_tokens:
            groups.append((self.error_weight, self.error_tokens, ERROR_COLOR))
        if self.success_tokens:
            groups.append((self.success_weight, self.success_tokens, SUCCESS_COLOR))

        if not groups:
            return ("", NEUTRAL_COLOR)

        total_weight = sum(weight for weight, _, _ in groups)
        pick = self.rng.uniform(0, total_weight)
        cumulative = 0.0
        for weight, tokens, color in groups:
            cumulative += weight
            if pick <= cumulative and tokens:
                return self.rng.choice(tokens), color

        # fallback if floating point rounding leaves pick slightly > cumulative
        tokens, color = groups[-1][1], groups[-1][2]
        return (self.rng.choice(tokens) if tokens else "", color)

    def _make_surface(self, text: str, color: tuple[int,int,int], alpha: int) -> pg.Surface:
        surf = self.font.render(text, True, color).convert_alpha()
        if alpha < 255: surf.set_alpha(alpha)
        return surf

    def _ensure_layout(self, screen_size, hud_height):
        key = (screen_size, hud_height)
        if key == self.last_layout_key: return
        self.last_layout_key = key
        sw, sh = screen_size
        self.glyphs.clear()
        top_margin = max(0, min(hud_height, sh))
        self.bounds_rect = pg.Rect(0, top_margin, sw, max(0, sh - top_margin))
        if self.bounds_rect.width <= 0 or self.bounds_rect.height <= 0: return

        fs = self.font_size
        area = self.bounds_rect.width * self.bounds_rect.height
        target = int(max(12, area / (fs * fs) * self.density))
        for _ in range(target):
            x = self.rng.uniform(self.bounds_rect.left, self.bounds_rect.right)
            y = self.rng.uniform(self.bounds_rect.top, self.bounds_rect.bottom)
            vy = self.rng.uniform(*self.speed)
            vx = self.rng.uniform(-self.hspeed[1], self.hspeed[1])
            alpha = self.rng.randint(*self.alpha_range)
            text, color = self._random_token()
            surface = self._make_surface(text, color, alpha)
            self.glyphs.append(_Glyph(text, x, y, vx, vy, color, alpha, surface))

    # ---------- 新：位置推进（每帧一次） ----------
    def advance(self, dt_ms: int, screen: pg.Surface | None = None, hud_height: int = 0):
        if screen is None: screen = pg.display.get_surface()
        if screen is None: return
        sw, sh = screen.get_width(), screen.get_height()
        self._ensure_layout((sw, sh), hud_height)
        if self.bounds_rect.width <= 0 or self.bounds_rect.height <= 0: return

        dt = max(1.0, float(dt_ms)) / 1000.0
        b = self.bounds_rect
        for g in self.glyphs:
            g.x += g.vx * dt
            g.y += g.vy * dt
            if g.y > b.bottom:
                g.y = b.top - self.font_size * self.rng.uniform(0.2, 1.5)
                g.text, g.color = self._random_token()
                g.alpha = self.rng.randint(*self.alpha_range)
                g.surface = self._make_surface(g.text, g.color, g.alpha)
            if g.x < b.left - 20:
                g.x = b.right + 10
            elif g.x > b.right + 20:
                g.x = b.left - 10

    # ---------- 绘制：将代码雨直接画到屏幕（棋盘外与未激活区域内） ----------
    def draw(
        self,
        screen: pg.Surface,
        *,
        board_rect: pg.Rect | None,
        board_scale: float,
        cell_pixels: int = 16,
        subgrid_cells: int = 16,
        active_subgrids: Set[int] | None = None,
        grid_cells: int = 64,
        subgrid_cols: int = 4,
        hide_margin_px: int = 0,
    ) -> None:
        if screen is None:
            return
        active_subgrids = active_subgrids or set()
        scale = max(board_scale, 1e-6)
        board_span = cell_pixels * grid_cells

        for g in self.glyphs:
            if g.surface is None:
                continue

            glyph_rect_screen = g.surface.get_rect(topleft=(g.x, g.y))
            if board_rect and glyph_rect_screen.colliderect(board_rect):
                continue

            surf = g.surface
            screen.blit(surf, (g.x, g.y))
