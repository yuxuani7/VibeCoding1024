# shader.py
import numpy as np
import pygame as pg

pg.font.init()

# ------------------ 配置 ------------------
FONT_NAME = "Consolas, Menlo, Monospace"
TEXT_COLOR = (255, 255, 255)

# 可选: "vortex" / "metaballs" / "kaleido"
VARIANT = "vortex"  # 默认值

def set_variant(mode: str):
    """允许外部动态切换霓虹效果"""
    global VARIANT
    VARIANT = mode

# 字样与发光强度
TEXT_STRING = "1024"
GLOW_STRENGTH = 1.6     # 发光强度（加法）
STROKE_SIZE = 3         # 描边膨胀像素（近似）
STROKE_INTENSITY = 0.71 # 描边亮度

# 扫描线 & 暗角
SCANLINE_STRENGTH = 0.10
VIGNETTE_STRENGTH = 0.35

# 轻微色差（像素）
CHROM_AB_SHIFT = 1


# ------------------ 工具 ------------------
def _smoothstep(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0 + 1e-8), 0.0, 1.0)
    return t * t * (3 - 2 * t)

def _roll_max(mask, radius):
    """用 roll 做一个近似膨胀，返回 radius 内的最大值（快速近似发光/描边用）"""
    out = mask.copy()
    for r in range(1, radius + 1):
        out = np.maximum(out, np.roll(mask, r, axis=0))
        out = np.maximum(out, np.roll(mask, -r, axis=0))
        out = np.maximum(out, np.roll(mask, r, axis=1))
        out = np.maximum(out, np.roll(mask, -r, axis=1))
    return out

def _scanlines(h, w, t):
    y = np.arange(h, dtype=np.float32)[:, None]
    sl = 1.0 - SCANLINE_STRENGTH * (0.5 + 0.5 * np.sin(y * 0.5 + t * 6.0))
    return np.repeat(sl, w, axis=1)

def _vignette(nx, ny):
    r2 = nx * nx + ny * ny
    return 1.0 - VIGNETTE_STRENGTH * _smoothstep(0.6, 1.0, r2)

def _palette_neon(a, b, c):
    """把 3 个场组合进 RGB，形成霓虹感"""
    r = 0.55 * a + 0.45 * b
    g = 0.40 * a + 0.60 * c
    bch = 0.50 * (1.0 - a) + 0.50 * b
    return r, g, bch


# ------------------ 三种底图 ------------------
def _field_vortex(nx, ny, t):
    # 轻度域扭曲
    warp_x = nx + 0.05 * np.sin(ny * 8 + 0.8 * t + 0.6 * np.sin(nx * 4 - t))
    warp_y = ny + 0.05 * np.sin(nx * 8 - 0.7 * t + 0.6 * np.sin(ny * 4 + t))

    r = np.sqrt(warp_x * warp_x + warp_y * warp_y) + 1e-6
    ang = np.arctan2(warp_y, warp_x)

    swirl = 1.2 * r * r + 0.7 * np.sin(t + r * 10.0)
    cs, sn = np.cos(swirl), np.sin(swirl)
    xr = warp_x * cs - warp_y * sn
    yr = warp_x * sn + warp_y * cs

    rings = 0.5 + 0.5 * np.sin(12.0 * r + 1.4 * t + 0.4 * np.sin(ang * 6 + t))
    grid = (0.5 + 0.5 * np.cos(xr * 30 + 2.0 * t)) * (0.5 + 0.5 * np.cos(yr * 30 + 1.7 * t))
    base = 0.40 * rings + 0.60 * grid
    return np.clip(base, 0.0, 1.0), rings, grid

def _field_metaballs(nx, ny, t):
    # 三个随时间移动的“能量团簇”
    cx = np.array([0.6 * np.sin(t * 0.8), 0.75 * np.sin(t * 1.1 + 2.0), -0.65 * np.cos(t * 0.9)], dtype=np.float32)
    cy = np.array([0.6 * np.cos(t * 0.7), -0.55 * np.sin(t * 1.3 + 1.0), 0.65 * np.sin(t * 1.0 + 2.2)], dtype=np.float32)
    s = np.array([0.85, 0.95, 0.8], dtype=np.float32)

    field = np.zeros_like(nx, dtype=np.float32)
    for i in range(3):
        dx = nx - cx[i]
        dy = ny - cy[i]
        d2 = dx * dx + dy * dy
        # 高斯团簇
        blob = np.exp(-(d2) / (s[i] * 0.12 + 1e-6))
        field += blob

    field = field / (field.max() + 1e-6)
    ripples = 0.5 + 0.5 * np.sin(10.0 * np.sqrt(nx * nx + ny * ny) - 1.6 * t)
    return np.clip(0.65 * field + 0.35 * ripples, 0.0, 1.0), field, ripples

def _field_kaleido(nx, ny, t):
    # 万花镜角度折叠 + 同心波纹
    r = np.sqrt(nx * nx + ny * ny) + 1e-6
    ang = np.arctan2(ny, nx)

    sectors = 6.0
    ang_fold = np.mod(ang, 2 * np.pi / sectors)
    ang_fold = np.abs(ang_fold - (np.pi / sectors))
    star = 0.5 + 0.5 * np.cos(ang_fold * sectors + 3.0 * r - 1.2 * t)
    rings = 0.5 + 0.5 * np.sin(14.0 * r - 1.6 * t)
    lattice = 0.5 + 0.5 * np.cos(4.0 * (nx * np.cos(t) + ny * np.sin(t)) * 8.0)

    base = 0.45 * star + 0.35 * rings + 0.20 * lattice
    return np.clip(base, 0.0, 1.0), rings, lattice


# ------------------ 主函数 ------------------
def gen_1024_field(w, h, t):
    """
    生成动态底图 + '1024' 字形霓虹蒙版。
    返回 (w, h, 3) 的 uint8。
    """
    # 坐标/归一化
    yy, xx = np.mgrid[0:h, 0:w]
    nx = (xx - w * 0.5) / (0.5 * w)
    ny = (yy - h * 0.5) / (0.5 * h)

    # 选择底图
    if VARIANT == "metaballs":
        base, a1, a2 = _field_metaballs(nx, ny, t)
    elif VARIANT == "kaleido":
        base, a1, a2 = _field_kaleido(nx, ny, t)
    else:
        base, a1, a2 = _field_vortex(nx, ny, t)

    # 扫描线 + 暗角
    scan = _scanlines(h, w, t)
    vig = _vignette(nx, ny)
    base = np.clip(base * scan * vig, 0.0, 1.0)

    # ----------- 渲染文字蒙版（缩放+居中） -----------
    font_target_height = int(h * 0.60)
    font_target_width = int(w * 0.92)
    FONT_SIZE = max(24, int(font_target_height))
    font = pg.font.SysFont(FONT_NAME, FONT_SIZE, bold=True)
    text_surface = font.render(TEXT_STRING, True, TEXT_COLOR)
    tw, th = text_surface.get_width(), text_surface.get_height()
    scale = min(max(1, int(font_target_width / max(1, tw))), max(1, int(font_target_height / max(1, th))))
    sw = max(1, int(tw * scale))
    sh = max(1, int(th * scale))
    text_scaled = pg.transform.smoothscale(text_surface, (sw, sh))

    alpha_wh = pg.surfarray.array_alpha(text_scaled).astype(np.float32) / 255.0
    alpha_hw = alpha_wh.T  # (h,w) 风格

    mask = np.zeros((h, w), dtype=np.float32)
    sy = (h - sh) // 2
    sx = (w - sw) // 2
    mask[sy:sy + sh, sx:sx + sw] = alpha_hw

    # 发光 + 描边（近似膨胀/卷积）
    stroke = _roll_max(mask, STROKE_SIZE) - mask
    stroke = np.clip(stroke, 0.0, 1.0)

    glow = _roll_max(mask, 6)
    if glow.max() > 1e-6:
        glow = glow / glow.max()
    glow = glow ** 0.85  # 软一点

    # ----------- 颜色合成 -----------
    # 基础三通道
    r0, g0, b0 = _palette_neon(base, a1, a2)

    # 文本区域提亮（内发光 + 外描边）
    r = r0 + GLOW_STRENGTH * glow + STROKE_INTENSITY * stroke * 0.3
    g = g0 + GLOW_STRENGTH * glow * 0.75 + STROKE_INTENSITY * stroke * 0.5
    b = b0 + GLOW_STRENGTH * glow * 0.95 + STROKE_INTENSITY * stroke * 0.2

    # 文本内部再拉高亮度，形成“镂空霓虹”的感觉
    r = np.where(mask > 0.5, np.clip(r + 0.6, 0, 1), r)
    g = np.where(mask > 0.5, np.clip(g + 0.6, 0, 1), g)
    b = np.where(mask > 0.5, np.clip(b + 0.6, 0, 1), b)

    # 轻微色差：R/G/B 分别做像素级 roll
    if CHROM_AB_SHIFT > 0:
        r = np.roll(r, +CHROM_AB_SHIFT, axis=1)
        b = np.roll(b, -CHROM_AB_SHIFT, axis=1)

    # 合成到 0..255
    img_hw = np.zeros((h, w, 3), dtype=np.uint8)
    img_hw[..., 0] = np.clip(r * 255.0, 0, 255).astype(np.uint8)
    img_hw[..., 1] = np.clip(g * 255.0, 0, 255).astype(np.uint8)
    img_hw[..., 2] = np.clip(b * 255.0, 0, 255).astype(np.uint8)

    # pygame.surfarray.make_surface 期望 (w, h, 3)
    img_wh = np.transpose(img_hw, (1, 0, 2))
    return img_wh