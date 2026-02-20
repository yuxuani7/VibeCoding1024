import pygame as pg

from codewall import CodeWall
from game import game_loop
from guide import guide_loop
from menu import menu_loop

WINDOW_W, WINDOW_H = int(960 * 1.2), int(720 * 1.2)


def main() -> None:
    pg.init()
    pg.display.set_caption("VibeSnake 1024")
    pg.display.set_mode((WINDOW_W, WINDOW_H), pg.RESIZABLE)
    clock = pg.time.Clock()
    code_wall = CodeWall()

    running = True
    while running:
        screen = pg.display.get_surface()
        if screen is None:
            break

        width, height = screen.get_size()
        menu_result = menu_loop(screen, clock, width, height)
        if menu_result == "QUIT":
            break

        if menu_result == "START":
            guide_result = guide_loop(screen, clock)
            if guide_result == "QUIT":
                running = False
                break
            if guide_result == "MENU":
                continue
            if guide_result != "PLAY":
                continue

            game_result = game_loop(code_wall)
            if game_result == "QUIT":
                running = False
        else:
            game_result = menu_result

    pg.quit()


if __name__ == "__main__":
    main()
