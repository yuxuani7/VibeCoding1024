# guide.py
import pygame as pg


GUIDE_LINES = [
    "- Use Arrow keys or WASD to steer.",
    "- Press R to restart.",
    "- Press ESC to return to the menu.",
    "",
    "- Red beans = Error -> Length -5",
    "- Yellow beans = Warning -> Length -1",
    "- Green beans = Success -> Length +2",
    "- Keep pushing toward 1024!"
]

def guide_loop(screen: pg.Surface, clock: pg.time.Clock) -> str:
    font_title = pg.font.SysFont("Consolas, Menlo, Monospace", 42)
    font_body = pg.font.SysFont("Consolas, Menlo, Monospace", 24)
    font_tip = pg.font.SysFont("Consolas, Menlo, Monospace", 20)

    width, height = screen.get_size()

    def draw():
        width_local, height_local = screen.get_size()
        screen.fill((16, 18, 24))

        title_surf = font_title.render("Snake 1024 — Guide", True, (210, 230, 240))
        screen.blit(title_surf, (width_local // 2 - title_surf.get_width() // 2, 60))

        panel_width = int(width_local * 0.7)
        panel_height = int(height_local * 0.55)
        panel_rect = pg.Rect(
            width_local // 2 - panel_width // 2,
            height_local // 2 - panel_height // 2 + 30,
            panel_width,
            panel_height,
        )

        panel_surface = pg.Surface(panel_rect.size, pg.SRCALPHA)
        panel_surface.fill((0, 0, 0, 120))
        pg.draw.rect(panel_surface, (50, 110, 95), panel_surface.get_rect(), width=2, border_radius=18)
        screen.blit(panel_surface, panel_rect.topleft)

        text_y = panel_rect.top + 30
        for line in GUIDE_LINES:
            body_surf = font_body.render(line, True, (200, 235, 220))
            screen.blit(body_surf, (panel_rect.left + 40, text_y))
            text_y += body_surf.get_height() + 14

        footer = font_tip.render("ENTER / SPACE — Continue     ESC — Back to Menu", True, (150, 200, 190))
        screen.blit(footer, (width_local // 2 - footer.get_width() // 2, panel_rect.bottom + 24))

        pg.display.flip()

    draw()
    while True:
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return "QUIT"
            if event.type == pg.VIDEORESIZE:
                screen = pg.display.set_mode((event.w, event.h), pg.RESIZABLE)
                draw()
            if event.type == pg.KEYDOWN:
                if event.key in (pg.K_RETURN, pg.K_SPACE):
                    return "PLAY"
                if event.key == pg.K_ESCAPE:
                    return "MENU"
        clock.tick(60)
