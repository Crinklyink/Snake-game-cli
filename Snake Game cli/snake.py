import os
import random
import sys
import time
from collections import deque

try:
    import msvcrt  # Windows-only, used for non-blocking key reads.
except ImportError:  # pragma: no cover
    msvcrt = None

try:
    import select
    import termios
    import tty
except ImportError:  # pragma: no cover
    select = None
    termios = None
    tty = None


WIDTH = 30
HEIGHT = 20
BASE_TICK = 0.12

DIR_UP = (0, -1)
DIR_DOWN = (0, 1)
DIR_LEFT = (-1, 0)
DIR_RIGHT = (1, 0)

KEY_TO_DIR = {
    "H": DIR_UP,       # Windows arrow up
    "P": DIR_DOWN,     # Windows arrow down
    "K": DIR_LEFT,     # Windows arrow left
    "M": DIR_RIGHT,    # Windows arrow right
    "\x1b[A": DIR_UP,  # ANSI arrow up
    "\x1b[B": DIR_DOWN,
    "\x1b[D": DIR_LEFT,
    "\x1b[C": DIR_RIGHT,
    "w": DIR_UP,
    "s": DIR_DOWN,
    "a": DIR_LEFT,
    "d": DIR_RIGHT,
    "W": DIR_UP,
    "S": DIR_DOWN,
    "A": DIR_LEFT,
    "D": DIR_RIGHT,
}


def enable_ansi():
    if os.name == "nt":
        # Enables ANSI escape sequences in newer Windows terminals.
        os.system("")


def hide_cursor():
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()


def clear_screen():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()


class TerminalMode:
    def __enter__(self):
        if os.name != "nt" and termios and tty:
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        if os.name != "nt" and termios and tty:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


def read_key_windows():
    if msvcrt is None:
        return None
    if not msvcrt.kbhit():
        return None
    ch = msvcrt.getch()
    if ch in (b"\x00", b"\xe0"):
        ch = msvcrt.getch()
    return ch


def read_key_posix():
    if select is None:
        return None
    readable, _, _ = select.select([sys.stdin], [], [], 0)
    if not readable:
        return None
    ch = sys.stdin.read(1)
    if ch != "\x1b":
        return ch
    if select.select([sys.stdin], [], [], 0)[0]:
        ch2 = sys.stdin.read(1)
        if ch2 == "[" and select.select([sys.stdin], [], [], 0)[0]:
            ch3 = sys.stdin.read(1)
            return f"{ch}{ch2}{ch3}"
        return f"{ch}{ch2}"
    return ch


def read_key():
    key = read_key_windows() if os.name == "nt" else read_key_posix()
    if key is None:
        return None
    if isinstance(key, bytes):
        try:
            key = key.decode()
        except UnicodeDecodeError:
            return None
    return key


def is_opposite(a, b):
    return a[0] == -b[0] and a[1] == -b[1]


def place_food(snake_set):
    while True:
        pos = (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1))
        if pos not in snake_set:
            return pos


def render(snake, food, score):
    head = snake[0]
    snake_set = set(snake)
    rows = []
    rows.append("#" * (WIDTH + 2))
    for y in range(HEIGHT):
        line = ["#"]
        for x in range(WIDTH):
            pos = (x, y)
            if pos == head:
                line.append("O")
            elif pos in snake_set:
                line.append("o")
            elif pos == food:
                line.append("*")
            else:
                line.append(" ")
        line.append("#")
        rows.append("".join(line))
    rows.append("#" * (WIDTH + 2))
    rows.append(f"Score: {score}  (WASD / arrows, Q to quit)")
    sys.stdout.write("\x1b[H" + "\n".join(rows))
    sys.stdout.flush()


def run_game():
    snake = deque()
    start_x = WIDTH // 2
    start_y = HEIGHT // 2
    snake.appendleft((start_x, start_y))
    snake.append((start_x - 1, start_y))
    snake.append((start_x - 2, start_y))
    direction = DIR_RIGHT
    score = 0

    food = place_food(set(snake))
    last_tick = time.time()
    tick = BASE_TICK

    clear_screen()
    hide_cursor()
    try:
        with TerminalMode():
            while True:
                key = read_key()
                if key in ("q", "Q"):
                    return score, "quit"
                if key in KEY_TO_DIR:
                    candidate = KEY_TO_DIR[key]
                    if not is_opposite(candidate, direction):
                        direction = candidate

                now = time.time()
                if now - last_tick >= tick:
                    last_tick = now
                    head_x, head_y = snake[0]
                    next_head = (head_x + direction[0], head_y + direction[1])

                    if (
                        next_head[0] < 0
                        or next_head[0] >= WIDTH
                        or next_head[1] < 0
                        or next_head[1] >= HEIGHT
                    ):
                        return score, "wall"

                    if next_head in snake:
                        return score, "self"

                    snake.appendleft(next_head)
                    if next_head == food:
                        score += 1
                        food = place_food(set(snake))
                        tick = max(0.05, BASE_TICK - score * 0.002)
                    else:
                        snake.pop()

                render(snake, food, score)
                time.sleep(0.005)
    finally:
        show_cursor()


def main():
    enable_ansi()
    if os.name == "nt" and msvcrt is None:
        print("This game requires msvcrt (Windows) for input handling.")
        return

    while True:
        score, reason = run_game()
        print()
        if reason == "quit":
            print(f"Quit. Final score: {score}")
            break
        print(f"Game over ({reason}). Final score: {score}")
        choice = input("Play again? (y/n): ").strip().lower()
        if choice not in ("y", "yes"):
            break


if __name__ == "__main__":
    main()
