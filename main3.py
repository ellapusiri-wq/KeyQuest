import json
import math
import random
import sys
from array import array
from collections import deque
from types import SimpleNamespace

import pygame

try:
    pygame.mixer.pre_init(22050, -16, 1, 512)
except pygame.error:
    pass
pygame.init()

# =============== WINDOW ===============
TILE = 40
COLS, ROWS = 15, 12
HUD = 76
WIDTH, HEIGHT = COLS * TILE, ROWS * TILE + HUD
PLAY_H = ROWS * TILE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("KEY QUEST | Ruins of the Ancients")
clock = pygame.time.Clock()

# =============== COLORS ===============
BG = (7, 10, 29)
FLOOR = (12, 22, 48)
FLOOR2 = (14, 26, 54)
CYAN = (67, 235, 255)
PURPLE = (177, 85, 255)
PINK = (255, 83, 175)
GOLD = (255, 205, 75)
GREEN = (70, 245, 160)
RED = (255, 75, 100)
ORANGE = (255, 150, 60)
WHITE = (242, 247, 255)
MUTED = (157, 180, 220)

font = pygame.font.Font(None, 25)
small = pygame.font.Font(None, 20)
medium = pygame.font.Font(None, 34)
large = pygame.font.Font(None, 52)
title_font = pygame.font.Font(None, 76)

DIRS4 = ((1, 0), (-1, 0), (0, 1), (0, -1))

# =============== LEVEL LEGEND ===============
#  #  wall            .  floor           P  player start
#  K  golden key      E  exit            D  puzzle door
#  C  coin            T  trap            O  portal (use exactly 2)
#  S  shield          F  speed boost     L  extra life
#  A  bolt ammo       M  time crystal
#  e  patrol enemy (left/right)          v  patrol enemy (up/down)
#  g  chasing ghost                      B  boss guardian
POWERUP_CHARS = {"S": "shield", "F": "speed", "L": "life",
                 "A": "ammo", "M": "time"}
VALID_CHARS = set("#.PKECTDOSFLAMevgB")

LEVEL_1 = [
    "###############",
    "#P..C....#....#",
    "###.###..#.##.#",
    "#...#.e..#..C.#",
    "#.###.####.##.#",
    "#...C....T..e.#",
    "#.######.###..#",
    "#..S.#...#.F..#",
    "####.#.###.##.#",
    "#C...#L.K....##",
    "#....T......DE#",
    "###############",
]

LEVEL_2 = [
    "###############",
    "#P..C.....F...#",
    "#.#####.####..#",
    "#..e..#....C..#",
    "#####.####.##.#",
    "#.A.T....#....#",
    "#.######.#.##.#",
    "#C.....#.#..g.#",
    "#.###..#.#.##.#",
    "#...#..K.....##",
    "#..S.T......DE#",
    "###############",
]

LEVEL_3 = [
    "###############",
    "#P..C....#..K.#",
    "#.##T##..#..C.#",
    "#..e.#...#.A..#",
    "####.#.####.#.#",
    "#C...#......#.#",
    "#.######.##.#.#",
    "#....#.T..#..S#",
    "##.#.#.##.###.#",
    "#..#..L..F.v.##",
    "#O...T....O.DE#",
    "###############",
]

# puzzle = (symbols to remember, seconds the pattern stays visible; 99 = always)
LEVELS = [
    {"name": "THE ENTRY HALL", "time": 150, "puzzle": (3, 99), "grid": LEVEL_1,
     "theme": ((25, 58, 112), (65, 160, 220), CYAN),
     "tip": "Walk into the purple door to open the symbol lock."},
    {"name": "CRYSTAL CORRIDORS", "time": 150, "puzzle": (3, 5), "grid": LEVEL_2,
     "theme": ((20, 84, 92), (60, 200, 190), GREEN),
     "tip": "Purple ghosts chase you. Press SPACE to shoot them!"},
    {"name": "PORTAL VAULTS", "time": 150, "puzzle": (4, 4), "grid": LEVEL_3,
     "theme": ((72, 38, 120), (160, 100, 230), PURPLE),
     "tip": "Step on a portal to jump to the other one."},
    {"name": "THE DARK ARCHIVE", "time": 170, "puzzle": (4, 3), "dark": True,
     "theme": ((60, 40, 70), (150, 90, 150), PINK),
     "gen": {"coins": 8, "traps": 3, "patrol_h": 1, "patrol_v": 1, "ghosts": 1,
             "hall_ghosts": 2, "boss": False, "ammo": 2},
     "tip": "It is DARK here. Follow your torch - a new maze every run!"},
    {"name": "THE GUARDIAN'S VAULT", "time": 190, "puzzle": (5, 3), "dark": True,
     "theme": ((96, 70, 24), (220, 170, 70), GOLD),
     "gen": {"coins": 10, "traps": 4, "patrol_h": 2, "patrol_v": 1, "ghosts": 2,
             "hall_ghosts": 0, "boss": True, "ammo": 3},
     "tip": "The Guardian has 3 HP. Collect bolts and fire away!"},
]

ENEMY_INTERVAL = {"patrol": 0.55, "ghost": 0.62, "boss": 0.50}
CHASE_RANGE = {"ghost": 9, "boss": 14}
BOLT_SPEED = 12.0          # tiles per second
START_LIVES = 5            # lives at the start of a new game
MAX_LIVES = 5              # hearts drawn in the HUD (a "xN" counter shows beyond this)
MAX_AMMO = 9

SAVE_FILE = "keyquest_scores.json"

# =============== SOUND (generated in code) ===============
SOUNDS = {}


def build_sounds():
    info = pygame.mixer.get_init()
    if not info:
        return
    rate, fmt, channels = info
    if fmt != -16:
        return

    def make(seq, vol=0.22):
        data = array("h")
        for freq, ms, slide in seq:
            n = int(rate * ms / 1000)
            for i in range(n):
                t = i / rate
                env = 1.0 - i / n
                if freq <= 0:
                    sample = 0
                else:
                    s = math.sin(2 * math.pi * (freq * t + 0.5 * slide * t * t))
                    wave = 0.5 * s + 0.5 * math.copysign(1, s)
                    sample = int(32767 * vol * env * wave)
                for _ in range(channels):
                    data.append(sample)
        return pygame.mixer.Sound(buffer=data.tobytes())

    try:
        SOUNDS["coin"] = make([(988, 50, 0), (1319, 90, 0)])
        SOUNDS["key"] = make([(660, 80, 0), (880, 80, 0), (1320, 170, 0)])
        SOUNDS["power"] = make([(440, 60, 0), (660, 60, 0), (880, 110, 0)])
        SOUNDS["hurt"] = make([(240, 120, -300), (150, 220, -200)], 0.3)
        SOUNDS["shoot"] = make([(900, 110, -5000)])
        SOUNDS["kill"] = make([(300, 60, 0), (520, 60, 0), (260, 130, -500)])
        SOUNDS["block"] = make([(1200, 60, 0), (800, 90, 0)])
        SOUNDS["click"] = make([(700, 40, 0)])
        SOUNDS["wrong"] = make([(180, 220, 0)], 0.3)
        SOUNDS["unlock"] = make([(523, 90, 0), (659, 90, 0), (784, 90, 0), (1046, 220, 0)])
        SOUNDS["portal"] = make([(300, 220, 2500)])
        SOUNDS["clear"] = make([(523, 100, 0), (659, 100, 0), (784, 100, 0),
                                (1046, 100, 0), (1318, 260, 0)])
        SOUNDS["lose"] = make([(400, 160, 0), (300, 160, 0), (200, 360, -100)], 0.3)
    except Exception:
        SOUNDS.clear()


def play(name):
    snd = SOUNDS.get(name)
    if snd:
        snd.play()


# =============== GAME STATE ===============
# One object holds all changing values. Writing g.score += 50 works anywhere,
# so we never need "global" (forgetting "global" caused the old puzzle crash).
g = SimpleNamespace(
    running=True, state="menu", level=0,
    score=0, best=0, lives=START_LIVES, time_left=150.0,
    shield=0.0, speed=0.0, invuln=0.0, ammo=3, shake=0.0,
    shoot_cd=0.0, move_timer=0.0,
    notice="", notice_timer=0.0, intro_timer=0.0, intro_info="",
    player=[1, 1], spawn=(1, 1), facing=(1, 0),
    key_pos=(0, 0), exit_pos=(0, 0), key_found=False, hits=0,
    puzzle_open=False, puzzle_seq=[], puzzle_choices=[],
    puzzle_peek=0.0, puzzle_show=3.0,
    theme=((25, 58, 112), (65, 160, 220), CYAN), dark=False, level_name="",
)

walls, coins, traps, doors = set(), set(), set(), set()
powerups = {}          # (x, y) -> kind
portals = []
enemies = []
bolts = []
particles = []
floaters = []
puzzle_buttons = []

static_layer = pygame.Surface((WIDTH, PLAY_H))
fog_layer = pygame.Surface((WIDTH, PLAY_H), pygame.SRCALPHA)

stars = [
    [random.randrange(WIDTH), random.randrange(HEIGHT),
     random.uniform(0.4, 1.8), random.choice([1, 1, 2])]
    for _ in range(100)
]

# =============== SAVE / LOAD BEST SCORE ===============
try:
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        g.best = int(json.load(f).get("best", 0))
except (OSError, ValueError, TypeError, json.JSONDecodeError):
    g.best = 0


def save_best_score():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump({"best": g.best}, f)
    except OSError:
        pass


# =============== LEVEL CHECKING ===============
def validate_grid(grid):
    """Return a list of problems (empty list = level is fair and winnable)."""
    problems = []
    if len(grid) != ROWS:
        return [f"needs {ROWS} rows, has {len(grid)}"]
    start = key = exit_ = None
    door_list, portal_list, items = [], [], []
    for y, row in enumerate(grid):
        if len(row) != COLS:
            return [f"row {y} needs {COLS} columns, has {len(row)}"]
        for x, ch in enumerate(row):
            if ch not in VALID_CHARS:
                problems.append(f"unknown symbol '{ch}' at {(x, y)}")
            elif ch == "P":
                start = (x, y)
            elif ch == "K":
                key = (x, y)
            elif ch == "E":
                exit_ = (x, y)
            elif ch == "D":
                door_list.append((x, y))
            elif ch == "O":
                portal_list.append((x, y))
            elif ch in "CSFLAM":
                items.append((x, y))
    if not (start and key and exit_):
        problems.append("level needs one P, one K and one E")
        return problems
    if not door_list:
        problems.append("no puzzle door (D)")
    if len(portal_list) not in (0, 2):
        problems.append("use exactly 0 or 2 portals (O)")

    def reach(doors_open):
        seen, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in DIRS4:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < COLS and 0 <= ny < ROWS):
                    continue
                ch = grid[ny][nx]
                if ch == "#" or (ch == "D" and not doors_open):
                    continue
                dest = (nx, ny)
                if ch == "O" and len(portal_list) == 2:
                    dest = portal_list[1] if dest == portal_list[0] else portal_list[0]
                if dest not in seen:
                    seen.add(dest)
                    queue.append(dest)
        return seen

    closed, opened = reach(False), reach(True)
    if key not in closed:
        problems.append("key cannot be reached before the door opens")
    if door_list and exit_ in closed:
        problems.append("exit is reachable without opening the door")
    if exit_ not in opened:
        problems.append("exit can never be reached")
    for item in items:
        if item not in opened:
            problems.append(f"item at {item} cannot be reached")
    return problems


def safe_route(grid):
    """True when the key AND the exit can be reached without ever stepping on a
    trap (a trap sends the player back to the start, so a trap that sits on the
    only route would make the level impossible)."""
    start = key = exit_ = gate = None
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch == "P":
                start = (x, y)
            elif ch == "K":
                key = (x, y)
            elif ch == "E":
                exit_ = (x, y)
            elif ch == "D":
                gate = (x, y)
    if not (start and key and exit_ and gate):
        return False

    def flood(doors_open):
        seen, queue = {start}, deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in DIRS4:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < COLS and 0 <= ny < ROWS):
                    continue
                ch = grid[ny][nx]
                if ch in "#T":
                    continue
                if ch == "D" and not doors_open:
                    continue
                if (nx, ny) not in seen:
                    seen.add((nx, ny))
                    queue.append((nx, ny))
        return seen

    closed = flood(False)
    if key not in closed:
        return False
    if (gate[0], gate[1] - 1) not in closed:      # the cell in front of the door
        return False
    return exit_ in flood(True)


def try_generate_level(cfg):
    """One attempt at a random maze with a locked vault behind a puzzle door.
    Returns a list of row strings, or None if this attempt was not valid."""
    grid = [["#"] * COLS for _ in range(ROWS)]

    # --- maze: cells sit on odd coordinates, x 1..13, y 1..7 ---
    def inside(x, y):
        return 1 <= x <= 13 and 1 <= y <= 7

    grid[1][1] = "."
    stack, seen = [(1, 1)], {(1, 1)}
    while stack:
        x, y = stack[-1]
        options = [(x + dx * 2, y + dy * 2, dx, dy) for dx, dy in DIRS4
                   if inside(x + dx * 2, y + dy * 2)
                   and (x + dx * 2, y + dy * 2) not in seen]
        if options:
            nx, ny, dx, dy = random.choice(options)
            grid[y + dy][x + dx] = "."
            grid[ny][nx] = "."
            seen.add((nx, ny))
            stack.append((nx, ny))
        else:
            stack.pop()
    grid[1][1] = "P"

    # --- vault hall (rows 9-10) behind one door ---
    for y in (9, 10):
        for x in range(1, 14):
            grid[y][x] = "."
    for x in (4, 8, 12):
        grid[9][x] = "#"
    for x in (6, 10):
        grid[10][x] = "#"
    gate_x = random.choice(range(1, 14, 2))
    grid[8][gate_x] = "D"
    grid[10][13] = "E"

    # --- distances from the start (door closed) ---
    dist, prev = {(1, 1): 0}, {(1, 1): None}
    queue = deque([(1, 1)])
    while queue:
        x, y = queue.popleft()
        for dx, dy in DIRS4:
            n = (x + dx, y + dy)
            if n in dist or grid[n[1]][n[0]] != ".":
                continue
            dist[n] = dist[(x, y)] + 1
            prev[n] = (x, y)
            queue.append(n)

    floorset = set(dist)

    def floor_neighbors(p):
        return sum(1 for dx, dy in DIRS4 if (p[0] + dx, p[1] + dy) in floorset)

    gate_cell = (gate_x, 7)
    if gate_cell not in dist:
        return None
    dead_ends = [p for p in dist
                 if p != (1, 1) and p != gate_cell and floor_neighbors(p) == 1]
    if not dead_ends:
        return None
    key_pos = max(dead_ends, key=lambda p: dist[p])

    required = set()
    for target in (key_pos, gate_cell):
        p = target
        while p is not None:
            required.add(p)
            p = prev[p]

    taken = {(1, 1), key_pos, gate_cell}
    grid[key_pos[1]][key_pos[0]] = "K"
    off_path = [p for p in dist if p not in required]
    any_floor = [p for p in dist]
    straight_h = [p for p in dist
                  if (p[0] - 1, p[1]) in floorset and (p[0] + 1, p[1]) in floorset]
    straight_v = [p for p in dist
                  if (p[0], p[1] - 1) in floorset and (p[0], p[1] + 1) in floorset]

    def put(ch, pool, count, min_dist=0):
        cands = [p for p in pool if p not in taken and dist[p] >= min_dist]
        random.shuffle(cands)
        for p in cands[:count]:
            grid[p[1]][p[0]] = ch
            taken.add(p)

    put("T", off_path, cfg["traps"], 3)      # traps only on side branches
    put("S", any_floor, 1, 3)
    put("F", any_floor, 1, 3)
    put("L", any_floor, 1, 6)
    put("M", any_floor, 1, 3)
    put("A", any_floor, cfg["ammo"], 3)
    put("C", any_floor, cfg["coins"], 2)
    put("e", straight_h, cfg["patrol_h"], 6)
    put("v", straight_v, cfg["patrol_v"], 6)
    put("g", any_floor, cfg["ghosts"], 10)

    # hall contents
    for p in ((2, 9), (2, 10), (13, 9), (12, 10), (5, 10)):
        grid[p[1]][p[0]] = "C"
    if cfg["boss"]:
        grid[10][8] = "B"
    for p in ((9, 10), (4, 10))[:cfg["hall_ghosts"]]:
        grid[p[1]][p[0]] = "g"

    # Hall traps: the hall is a winding 1-tile-wide path, so the old fixed trap
    # positions sat on the only route (stepping on a trap sends you back to the
    # start, which made the level impossible). Now every trap is only kept if the
    # key and the exit can still be reached without touching any trap.
    hall_free = [(x, y) for y in (9, 10) for x in range(1, 14) if grid[y][x] == "."]
    random.shuffle(hall_free)
    placed = 0
    for x, y in hall_free:
        if placed >= 2:
            break
        grid[y][x] = "T"
        if safe_route(["".join(r) for r in grid]):
            placed += 1
        else:
            grid[y][x] = "."

    rows = ["".join(r) for r in grid]
    if validate_grid(rows) or not safe_route(rows):
        return None
    return rows


# Hand-made emergency layout: only used if random generation ever fails, so the
# game can never crash or get stuck while loading a generated level.
FALLBACK_LEVEL = [
    "###############",
    "#P....C.....K.#",
    "#############.#",
    "#.C.....C.....#",
    "#.#############",
    "#.....C......C#",
    "#############.#",
    "#.......C.....#",
    "#######D#######",
    "#...#...#...#.#",
    "#.....#...#..E#",
    "###############",
]


def fallback_level(cfg):
    rows = list(FALLBACK_LEVEL)
    if cfg.get("boss"):
        row = list(rows[10])
        row[8] = "B"
        rows[10] = "".join(row)
    return rows


def generate_level(cfg):
    """Random maze (always solvable) with a locked vault behind a puzzle door."""
    for _attempt in range(300):
        rows = try_generate_level(cfg)
        if rows:
            return rows
    return fallback_level(cfg)


# =============== DRAWING HELPERS ===============
def draw_text(label, fnt, color, x, y):
    image = fnt.render(label, True, color)
    screen.blit(image, image.get_rect(center=(int(x), int(y))))


def glow(color, x, y, radius):
    x, y = int(x), int(y)
    for extra, alpha in ((11, 22), (6, 42)):
        r = radius + extra
        layer = pygame.Surface((r * 2 + 2, r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(layer, (*color, alpha), (r + 1, r + 1), r)
        screen.blit(layer, (x - r - 1, y - r - 1))
    pygame.draw.circle(screen, color, (x, y), radius)


def draw_background():
    screen.fill(BG)
    now = pygame.time.get_ticks()
    for i in range(5):
        x = (i * 173 + now // (22 + i * 3)) % (WIDTH + 160) - 80
        y = 70 + (i % 3) * 150
        color = (32, 39, 105) if i % 2 else (62, 24, 99)
        glow(color, x, y, 24 + i * 3)
    for star in stars:
        star[1] += star[2] * 0.28
        if star[1] > HEIGHT:
            star[1] = 0
            star[0] = random.randrange(WIDTH)
        pulse = 170 + int(70 * (0.5 + 0.5 * math.sin(now / 350 + star[0])))
        pygame.draw.circle(screen, (pulse // 2, pulse, 255),
                           (int(star[0]), int(star[1])), star[3])


def draw_panel(rect, border=CYAN):
    surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(surface, (10, 19, 46, 245), surface.get_rect(), border_radius=17)
    pygame.draw.rect(surface, (*border, 230), surface.get_rect(), 2, border_radius=17)
    screen.blit(surface, rect.topleft)


def star_points(cx, cy, r):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = r if i % 2 == 0 else r * 0.45
        pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
    return pts


SYMBOL_NAMES = ["CIRCLE", "TRIANGLE", "STAR", "SQUARE"]
SYMBOL_COLORS = [CYAN, PURPLE, GOLD, GREEN]


def draw_symbol(kind, cx, cy, r, color, width=0):
    """Symbols are drawn with shapes (fonts cannot show triangle/star glyphs)."""
    if kind == 0:
        pygame.draw.circle(screen, color, (int(cx), int(cy)), int(r), width)
    elif kind == 1:
        pygame.draw.polygon(screen, color,
                            [(cx, cy - r), (cx + r * 0.95, cy + r * 0.75),
                             (cx - r * 0.95, cy + r * 0.75)], width)
    elif kind == 2:
        pygame.draw.polygon(screen, color, star_points(cx, cy, r * 1.1), width)
    else:
        rect = pygame.Rect(int(cx - r * 0.85), int(cy - r * 0.85),
                           int(r * 1.7), int(r * 1.7))
        pygame.draw.rect(screen, color, rect, width)


def set_notice(message):
    g.notice = message
    g.notice_timer = 2.2


def add_particles(x, y, color, count=14):
    for _ in range(count):
        angle = random.random() * math.tau
        speed = random.uniform(35, 130)
        particles.append([x, y, math.cos(angle) * speed, math.sin(angle) * speed,
                          random.uniform(0.35, 0.8), color])


def add_floater(tile, text, color=GOLD):
    floaters.append([tile[0] * TILE + 20, tile[1] * TILE + 8, text, color, 0.9])


def center(tile):
    return tile[0] * TILE + 20, tile[1] * TILE + 20


# =============== LEVEL SETUP ===============
def new_enemy(x, y, kind, dx=0, dy=0):
    hp = 3 if kind == "boss" else 1
    return {"x": x, "y": y, "dx": dx, "dy": dy, "kind": kind,
            "hp": hp, "maxhp": hp, "t": random.random() * 0.4, "alert": False}


def build_static_layer():
    fill, edge, top = g.theme
    for y in range(ROWS):
        for x in range(COLS):
            rect = pygame.Rect(x * TILE, y * TILE, TILE, TILE)
            pygame.draw.rect(static_layer, FLOOR if (x + y) % 2 == 0 else FLOOR2, rect)
            pygame.draw.rect(static_layer, (24, 49, 82), rect, 1)
    for x, y in walls:
        r = pygame.Rect(x * TILE + 2, y * TILE + 2, TILE - 4, TILE - 4)
        pygame.draw.rect(static_layer, fill, r, border_radius=6)
        pygame.draw.rect(static_layer, edge, r, 2, border_radius=6)
        pygame.draw.line(static_layer, top, (r.x + 6, r.y + 3), (r.right - 6, r.y + 3), 2)


def load_level(idx):
    cfg = LEVELS[idx]
    grid = cfg["grid"] if "grid" in cfg else generate_level(cfg["gen"])

    for collection in (walls, coins, traps, doors):
        collection.clear()
    for collection in (powerups,):
        collection.clear()
    for collection in (portals, enemies, bolts, particles, floaters):
        collection.clear()

    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            p = (x, y)
            if ch == "#":
                walls.add(p)
            elif ch == "C":
                coins.add(p)
            elif ch == "T":
                traps.add(p)
            elif ch == "P":
                g.spawn = p
            elif ch == "K":
                g.key_pos = p
            elif ch == "E":
                g.exit_pos = p
            elif ch == "D":
                doors.add(p)
            elif ch == "O":
                portals.append(p)
            elif ch in POWERUP_CHARS:
                powerups[p] = POWERUP_CHARS[ch]
            elif ch == "e":
                enemies.append(new_enemy(x, y, "patrol", 1, 0))
            elif ch == "v":
                enemies.append(new_enemy(x, y, "patrol", 0, 1))
            elif ch == "g":
                enemies.append(new_enemy(x, y, "ghost"))
            elif ch == "B":
                enemies.append(new_enemy(x, y, "boss"))

    g.player = list(g.spawn)
    g.facing = (1, 0)
    g.key_found = False
    g.puzzle_open = False
    g.puzzle_choices = []
    g.hits = 0
    g.theme = cfg["theme"]
    g.dark = cfg.get("dark", False)
    g.level_name = cfg["name"]
    g.time_left = float(cfg["time"])
    g.invuln = 1.5
    g.ammo = max(g.ammo, 3)

    count, show = cfg["puzzle"]
    g.puzzle_show = float(show)
    seq = []
    while len(seq) < count:
        s = random.randrange(4)
        if not seq or s != seq[-1]:
            seq.append(s)
    g.puzzle_seq = seq
    build_static_layer()


def start_level():
    load_level(g.level)
    g.state = "intro"
    g.intro_timer = 2.8


def start_game():
    g.level = 0
    g.score = 0
    g.lives = START_LIVES
    g.ammo = 3
    g.shield = 0.0
    g.speed = 0.0
    g.shake = 0.0
    g.intro_info = ""
    start_level()


def finish_game(won):
    if won:
        g.score += g.lives * 50
        play("clear")
    else:
        play("lose")
    g.state = "win" if won else "gameover"
    if g.score > g.best:
        g.best = g.score
        save_best_score()


def complete_level():
    time_bonus = max(0, int(g.time_left)) * 2
    g.score += time_bonus
    info = f"Time bonus +{time_bonus}"
    if g.hits == 0:
        g.score += 100
        info += "   |   No-damage bonus +100"
    if g.level < len(LEVELS) - 1:
        play("clear")
        g.level += 1
        start_level()
        g.intro_info = info
    else:
        finish_game(True)


# =============== COLLISION / MOVEMENT RULES ===============
def blocked(x, y):
    if x < 0 or y < 0 or x >= COLS or y >= ROWS:
        return True
    if (x, y) in walls:
        return True
    if (x, y) in doors and not g.puzzle_open:
        return True
    return False


def adjacent_to_door():
    px, py = g.player
    return any(abs(px - x) + abs(py - y) <= 1 for x, y in doors)


def hurt(enemy=None):
    """Player touched an enemy or trap. Shield absorbs one hit."""
    if g.invuln > 0 or g.state != "playing":
        return
    cx, cy = center(g.player)
    if g.shield > 0:
        g.shield = 0.0
        g.invuln = 1.5
        play("block")
        set_notice("SHIELD BLOCKED IT!")
        add_particles(cx, cy, CYAN, 18)
        if enemy is not None:
            if enemy["kind"] == "boss":
                damage_enemy(enemy)
                knock_back(enemy)
            else:
                kill_enemy(enemy)
        return
    g.lives -= 1
    g.hits += 1
    g.shake = 0.35
    add_particles(cx, cy, RED, 24)
    play("hurt")
    if g.lives <= 0:
        finish_game(False)
        return
    g.invuln = 2.0
    g.player[:] = list(g.spawn)
    set_notice("OUCH! BACK TO START")


def knock_back(enemy):
    px, py = g.player
    options = [(enemy["x"] + dx, enemy["y"] + dy) for dx, dy in DIRS4
               if not enemy_blocked(enemy["x"] + dx, enemy["y"] + dy, False)
               and (enemy["x"] + dx, enemy["y"] + dy) != (px, py)]
    if options:
        enemy["x"], enemy["y"] = random.choice(options)


def damage_enemy(enemy):
    enemy["hp"] -= 1
    add_particles(*center((enemy["x"], enemy["y"])), ORANGE, 12)
    if enemy["hp"] <= 0:
        kill_enemy(enemy)
    else:
        play("block")


def kill_enemy(enemy):
    if enemy in enemies:
        enemies.remove(enemy)
    points = 200 if enemy["kind"] == "boss" else 30
    g.score += points
    tile = (enemy["x"], enemy["y"])
    add_particles(*center(tile), PINK if enemy["kind"] != "boss" else GOLD,
                  40 if enemy["kind"] == "boss" else 18)
    add_floater(tile, f"+{points}", PINK)
    play("kill")
    if enemy["kind"] == "boss":
        set_notice("GUARDIAN DEFEATED! +200")


def trap_hit(tile):
    if g.shield > 0:
        g.shield = 0.0
        traps.discard(tile)
        play("block")
        set_notice("SHIELD DESTROYED THE TRAP!")
        add_particles(*center(tile), CYAN, 16)
    else:
        hurt()


def check_enemy_touch():
    here = tuple(g.player)
    for enemy in enemies[:]:
        if (enemy["x"], enemy["y"]) == here:
            hurt(enemy)
            if g.state != "playing":
                return


# =============== PLAYER ACTIONS ===============
def move_player(dx, dy):
    nx, ny = g.player[0] + dx, g.player[1] + dy

    if (nx, ny) in doors and not g.puzzle_open:
        open_puzzle()
        return
    if blocked(nx, ny):
        return

    g.player[:] = [nx, ny]
    tile = (nx, ny)
    cx, cy = center(tile)

    if tile in coins:
        coins.remove(tile)
        g.score += 10
        add_particles(cx, cy, GOLD)
        add_floater(tile, "+10")
        play("coin")

    if tile == g.key_pos and not g.key_found:
        g.key_found = True
        g.score += 25
        add_particles(cx, cy, GOLD, 22)
        set_notice("MAGIC KEY FOUND! +25")
        play("key")

    if tile in powerups:
        # pop() removes the power-up from the map first, so one pickup can only
        # ever be applied once (it is gone before any effect is given).
        kind = powerups.pop(tile)
        color = CYAN
        if kind == "shield":
            g.shield = 8.0
            set_notice("SHIELD ACTIVATED!")
        elif kind == "speed":
            g.speed = 8.0
            color = PURPLE
            set_notice("SPEED BOOST!")
        elif kind == "life":
            g.lives += 1          # exactly +1 life per extra-life power-up
            color = PINK
            set_notice("EXTRA LIFE!")
        elif kind == "ammo":
            g.ammo = min(MAX_AMMO, g.ammo + 3)
            color = (90, 170, 255)
            set_notice("+3 MAGIC BOLTS!")
        else:
            g.time_left += 15
            color = GREEN
            set_notice("+15 SECONDS!")
        g.score += 15
        add_particles(cx, cy, color, 20)
        play("power")

    if tile in portals and len(portals) == 2:
        dest = portals[1] if tile == portals[0] else portals[0]
        g.player[:] = list(dest)
        add_particles(cx, cy, PURPLE, 20)
        add_particles(*center(dest), PURPLE, 20)
        set_notice("PORTAL!")
        play("portal")

    here = tuple(g.player)
    if here in traps:
        trap_hit(here)
        if g.state != "playing":
            return

    check_enemy_touch()
    if g.state != "playing":
        return

    if tuple(g.player) == g.exit_pos:
        if g.key_found:
            complete_level()
        else:
            set_notice("FIND THE GOLDEN KEY FIRST!")


def shoot():
    if g.shoot_cd > 0:
        return
    if g.ammo <= 0:
        set_notice("OUT OF BOLTS! FIND BLUE CRYSTALS")
        return
    dx, dy = g.facing
    g.ammo -= 1
    g.shoot_cd = 0.25
    bolts.append({"x": float(g.player[0]), "y": float(g.player[1]),
                  "dx": dx, "dy": dy, "life": 3.0})
    play("shoot")


# =============== PUZZLE ===============
def open_puzzle():
    if not doors or g.puzzle_open:
        set_notice("NO LOCKED DOOR HERE")
        return
    g.puzzle_choices = []
    g.puzzle_peek = g.puzzle_show
    g.state = "puzzle"


def try_open_puzzle():
    if doors and not g.puzzle_open and adjacent_to_door():
        open_puzzle()
    elif doors and not g.puzzle_open:
        set_notice("MOVE NEXT TO THE PURPLE DOOR, THEN PRESS P")
    else:
        set_notice("THE DOOR IS ALREADY OPEN")


def puzzle_click(idx):
    n = len(g.puzzle_choices)
    if n >= len(g.puzzle_seq):
        return
    if idx == g.puzzle_seq[n]:
        g.puzzle_choices.append(idx)
        play("click")
        if len(g.puzzle_choices) == len(g.puzzle_seq):
            g.puzzle_open = True
            g.score += 50
            door = next(iter(doors))
            add_particles(*center(door), GOLD, 30)
            set_notice("DOOR UNLOCKED! +50")
            play("unlock")
            g.state = "playing"
            g.move_timer = 0.25
    else:
        g.puzzle_choices = []
        g.time_left = max(1.0, g.time_left - 5)
        g.puzzle_peek = max(g.puzzle_peek, 2.0)
        g.shake = 0.2
        set_notice("WRONG ORDER! -5 SECONDS")
        play("wrong")


# =============== ENEMIES ===============
def enemy_blocked(x, y, avoid_traps):
    if blocked(x, y):
        return True
    return avoid_traps and (x, y) in traps


def bfs_path(start, goal, limit):
    """Shortest walkable path (list of tiles, first step first) or None."""
    if start == goal:
        return []
    prev = {start: None}
    queue = deque([(start, 0)])
    while queue:
        cur, d = queue.popleft()
        if d >= limit:
            continue
        for dx, dy in DIRS4:
            n = (cur[0] + dx, cur[1] + dy)
            if n in prev or enemy_blocked(n[0], n[1], False):
                continue
            prev[n] = cur
            if n == goal:
                path = [n]
                while prev[path[-1]] != start:
                    path.append(prev[path[-1]])
                return path[::-1]
            queue.append((n, d + 1))
    return None


def move_enemies(dt):
    for enemy in enemies[:]:
        enemy["t"] += dt
        interval = ENEMY_INTERVAL[enemy["kind"]] * (1 - 0.04 * g.level)
        if enemy["t"] < interval:
            continue
        enemy["t"] = 0.0

        if enemy["kind"] == "patrol":
            nx, ny = enemy["x"] + enemy["dx"], enemy["y"] + enemy["dy"]
            if enemy_blocked(nx, ny, True):
                enemy["dx"] *= -1
                enemy["dy"] *= -1
                nx, ny = enemy["x"] + enemy["dx"], enemy["y"] + enemy["dy"]
            if not enemy_blocked(nx, ny, True):
                enemy["x"], enemy["y"] = nx, ny
        else:
            path = bfs_path((enemy["x"], enemy["y"]), tuple(g.player),
                            CHASE_RANGE[enemy["kind"]])
            enemy["alert"] = bool(path)
            if path:
                enemy["x"], enemy["y"] = path[0]

        if (enemy["x"], enemy["y"]) == tuple(g.player):
            hurt(enemy)
        if g.state != "playing":
            return


def update_bolts(dt):
    for b in bolts[:]:
        b["x"] += b["dx"] * BOLT_SPEED * dt
        b["y"] += b["dy"] * BOLT_SPEED * dt
        b["life"] -= dt
        tx, ty = int(math.floor(b["x"] + 0.5)), int(math.floor(b["y"] + 0.5))
        if b["life"] <= 0 or blocked(tx, ty):
            bolts.remove(b)
            add_particles(tx * TILE + 20, ty * TILE + 20, CYAN, 5)
            continue
        for enemy in enemies[:]:
            if enemy["x"] == tx and enemy["y"] == ty:
                damage_enemy(enemy)
                bolts.remove(b)
                break


def update_particles(dt):
    for p in particles[:]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
        if p[4] <= 0:
            particles.remove(p)
    for f in floaters[:]:
        f[1] -= 28 * dt
        f[4] -= dt
        if f[4] <= 0:
            floaters.remove(f)


# =============== PER-FRAME UPDATE ===============
MOVE_KEYS = {
    pygame.K_UP: (0, -1), pygame.K_DOWN: (0, 1),
    pygame.K_LEFT: (-1, 0), pygame.K_RIGHT: (1, 0),
    pygame.K_w: (0, -1), pygame.K_s: (0, 1),
    pygame.K_a: (-1, 0), pygame.K_d: (1, 0),
}


def update_playing(dt):
    g.time_left -= dt
    g.shield = max(0.0, g.shield - dt)
    g.speed = max(0.0, g.speed - dt)
    g.invuln = max(0.0, g.invuln - dt)
    g.shake = max(0.0, g.shake - dt)
    g.shoot_cd = max(0.0, g.shoot_cd - dt)
    g.move_timer -= dt

    if g.time_left <= 0:
        g.time_left = 0.0
        set_notice("TIME IS UP!")
        finish_game(False)
        return

    if g.move_timer <= 0:
        keys = pygame.key.get_pressed()
        for key, (dx, dy) in MOVE_KEYS.items():
            if keys[key]:
                g.facing = (dx, dy)
                move_player(dx, dy)
                g.move_timer = 0.085 if g.speed > 0 else 0.14
                break

    if g.state == "playing":
        update_bolts(dt)
        move_enemies(dt)


def update(dt):
    update_particles(dt)
    g.notice_timer = max(0.0, g.notice_timer - dt)
    if g.state == "playing":
        update_playing(dt)
    elif g.state == "puzzle":
        g.shake = max(0.0, g.shake - dt)
        if g.puzzle_peek < 90:
            g.puzzle_peek = max(0.0, g.puzzle_peek - dt)
    elif g.state == "intro":
        g.intro_timer -= dt
        if g.intro_timer <= 0:
            g.state = "playing"


# =============== DRAWING: GAME SCREEN ===============
def draw_hearts():
    for i in range(MAX_LIVES):
        x, y = 25 + i * 24, PLAY_H + 20
        if i < g.lives:
            pygame.draw.circle(screen, PINK, (x - 4, y - 2), 6)
            pygame.draw.circle(screen, PINK, (x + 4, y - 2), 6)
            pygame.draw.polygon(screen, PINK, [(x - 10, y), (x + 10, y), (x, y + 10)])
        else:
            pygame.draw.circle(screen, (65, 65, 95), (x, y), 5)
    if g.lives > MAX_LIVES:
        # more lives than hearts fit in the HUD: show the exact number
        draw_text(f"x{g.lives}", small, PINK, 25 + MAX_LIVES * 24, PLAY_H + 20)


def draw_enemy(enemy, now):
    ex, ey = center((enemy["x"], enemy["y"]))
    kind = enemy["kind"]
    if kind == "patrol":
        glow(RED, ex, ey, 12)
        pygame.draw.circle(screen, (65, 8, 38), (ex, ey), 9)
        pygame.draw.circle(screen, WHITE, (ex - 3, ey - 2), 2)
        pygame.draw.circle(screen, WHITE, (ex + 3, ey - 2), 2)
    elif kind == "ghost":
        bob = int(math.sin(now / 200 + ex) * 2)
        color = PINK if enemy["alert"] else PURPLE
        glow(color, ex, ey + bob, 12)
        pygame.draw.circle(screen, (28, 12, 60), (ex, ey + bob), 9)
        pygame.draw.circle(screen, WHITE, (ex - 3, ey - 2 + bob), 2)
        pygame.draw.circle(screen, WHITE, (ex + 3, ey - 2 + bob), 2)
        pygame.draw.line(screen, color, (ex - 6, ey + 8 + bob), (ex + 6, ey + 8 + bob), 2)
    else:
        glow(ORANGE, ex, ey, 16)
        pygame.draw.circle(screen, (60, 18, 10), (ex, ey), 13)
        pygame.draw.polygon(screen, GOLD, [(ex - 10, ey - 11), (ex - 5, ey - 19),
                                           (ex, ey - 11), (ex + 5, ey - 19),
                                           (ex + 10, ey - 11)])
        pygame.draw.circle(screen, RED, (ex - 5, ey - 2), 3)
        pygame.draw.circle(screen, RED, (ex + 5, ey - 2), 3)
        for i in range(enemy["maxhp"]):
            color = GREEN if i < enemy["hp"] else (60, 60, 80)
            pygame.draw.rect(screen, color, (ex - 14 + i * 10, ey - 27, 8, 5))


def draw_darkness():
    """Torch light: everything is black except a glowing circle around the player."""
    fog_layer.fill((2, 3, 12, 238))
    px, py = center(g.player)
    radius_boost = 18 if g.shield > 0 else 0
    for radius, alpha in ((200, 205), (165, 160), (135, 110),
                          (105, 60), (80, 20), (60, 0)):
        pygame.draw.circle(fog_layer, (2, 3, 12, alpha), (px, py), radius + radius_boost)
    screen.blit(fog_layer, (0, 0))


def draw_hud():
    pygame.draw.rect(screen, (6, 12, 32), (0, PLAY_H, WIDTH, HUD))
    pygame.draw.line(screen, g.theme[2], (0, PLAY_H), (WIDTH, PLAY_H), 2)
    draw_hearts()
    draw_text(f"SCORE {g.score}", font, GOLD, 200, PLAY_H + 20)
    secs = max(0, int(g.time_left))
    time_color = RED if secs < 20 and int(g.time_left * 2) % 2 == 0 else CYAN
    draw_text(f"TIME {secs // 60:02d}:{secs % 60:02d}", font, time_color, 340, PLAY_H + 20)
    draw_text(f"LEVEL {g.level + 1}/{len(LEVELS)}", font, WHITE, 500, PLAY_H + 20)

    draw_text(f"BOLTS x{g.ammo}", small, (90, 170, 255), 55, PLAY_H + 44)
    draw_text(f"SHIELD {g.shield:0.0f}s" if g.shield > 0 else "SHIELD --",
              small, CYAN if g.shield > 0 else MUTED, 150, PLAY_H + 44)
    draw_text(f"SPEED {g.speed:0.0f}s" if g.speed > 0 else "SPEED --",
              small, PURPLE if g.speed > 0 else MUTED, 245, PLAY_H + 44)
    draw_text("KEY: FOUND" if g.key_found else "KEY: MISSING",
              small, GOLD if g.key_found else MUTED, 350, PLAY_H + 44)
    if g.puzzle_open:
        draw_text("DOOR: OPEN", small, GREEN, 460, PLAY_H + 44)
    else:
        draw_text("DOOR: LOCKED", small, PURPLE, 460, PLAY_H + 44)
    draw_text("MOVE: ARROWS/WASD  |  SPACE: SHOOT  |  P: DOOR  |  ESC: PAUSE",
              small, MUTED, WIDTH // 2, PLAY_H + 64)

    if g.notice_timer > 0:
        r = pygame.Rect(WIDTH // 2 - 175, 5, 350, 30)
        draw_panel(r, GOLD)
        draw_text(g.notice, small, WHITE, WIDTH // 2, 20)


def draw_maze():
    screen.blit(static_layer, (0, 0))
    now = pygame.time.get_ticks()

    for x, y in doors:
        r = pygame.Rect(x * TILE + 4, y * TILE + 4, TILE - 8, TILE - 8)
        pygame.draw.rect(screen, GREEN if g.puzzle_open else PURPLE, r, border_radius=8)
        pygame.draw.rect(screen, WHITE, r, 2, border_radius=8)
        if g.puzzle_open:
            pygame.draw.lines(screen, WHITE, False,
                              [(r.x + 8, r.centery), (r.centerx - 2, r.bottom - 9),
                               (r.right - 7, r.y + 8)], 3)
        else:
            draw_text("?", medium, WHITE, x * TILE + 20, y * TILE + 20)

    for x, y in coins:
        bob = math.sin(now / 180 + x) * 2
        glow(GOLD, x * TILE + 20, y * TILE + 20 + bob, 7)

    for x, y in traps:
        pygame.draw.polygon(screen, RED, [(x * TILE + 20, y * TILE + 7),
                                          (x * TILE + 33, y * TILE + 32),
                                          (x * TILE + 7, y * TILE + 32)])
        pygame.draw.polygon(screen, WHITE, [(x * TILE + 20, y * TILE + 7),
                                            (x * TILE + 33, y * TILE + 32),
                                            (x * TILE + 7, y * TILE + 32)], 2)

    for (x, y), kind in powerups.items():
        color, symbol = {"shield": (CYAN, "S"), "speed": (PURPLE, ">"),
                         "life": (PINK, "+"), "ammo": ((90, 170, 255), "*"),
                         "time": (GREEN, "T")}[kind]
        glow(color, x * TILE + 20, y * TILE + 20, 10)
        draw_text(symbol, medium, WHITE, x * TILE + 20, y * TILE + 20)

    for i, (x, y) in enumerate(portals):
        radius = 12 + int(3 * math.sin(now / 160 + i))
        pygame.draw.circle(screen, PURPLE, (x * TILE + 20, y * TILE + 20), radius, 4)
        pygame.draw.circle(screen, CYAN, (x * TILE + 20, y * TILE + 20), radius - 5, 2)

    if not g.key_found:
        kx, ky = g.key_pos
        bob = int(math.sin(now / 220) * 2)
        pygame.draw.circle(screen, GOLD, (kx * TILE + 14, ky * TILE + 20 + bob), 8, 4)
        pygame.draw.line(screen, GOLD, (kx * TILE + 21, ky * TILE + 20 + bob),
                         (kx * TILE + 34, ky * TILE + 20 + bob), 4)

    ex, ey = g.exit_pos
    pygame.draw.rect(screen, (15, 95, 85), (ex * TILE + 4, ey * TILE + 4, TILE - 8, TILE - 8),
                     border_radius=8)
    pygame.draw.rect(screen, GREEN if g.key_found else MUTED,
                     (ex * TILE + 4, ey * TILE + 4, TILE - 8, TILE - 8), 3, border_radius=8)
    draw_text("EXIT", small, WHITE, ex * TILE + 20, ey * TILE + 20)

    for enemy in enemies:
        draw_enemy(enemy, now)

    px, py = center(g.player)
    blink = g.invuln > 0 and g.shield <= 0 and (now // 100) % 2 == 0
    if not blink:
        glow(CYAN if g.shield > 0 else PINK, px, py, 12)
        pygame.draw.circle(screen, (30, 28, 60), (px, py), 9)
        pygame.draw.circle(screen, (255, 220, 190), (px, py - 2), 6)
        pygame.draw.circle(screen, BG, (px - 2, py - 2), 1)
        pygame.draw.circle(screen, BG, (px + 2, py - 2), 1)
    fx, fy = g.facing
    pygame.draw.circle(screen, (90, 170, 255) if g.ammo > 0 else MUTED,
                       (px + fx * 15, py + fy * 15), 3)

    for b in bolts:
        glow((90, 170, 255), b["x"] * TILE + 20, b["y"] * TILE + 20, 5)

    for p in particles:
        pygame.draw.circle(screen, p[5], (int(p[0]), int(p[1])), max(1, int(4 * p[4])))

    if g.dark:
        draw_darkness()

    for f in floaters:
        draw_text(f[2], small, f[3], f[0], f[1])

    draw_hud()

    if g.shake > 0:
        frame = screen.copy()
        screen.fill(BG)
        screen.blit(frame, (random.randint(-4, 4), random.randint(-4, 4)))


# =============== DRAWING: MENUS ===============
def draw_button(rect, label, color, hovered=False):
    pygame.draw.rect(screen, (18, 34, 72), rect, border_radius=13)
    pygame.draw.rect(screen, color, rect, 3 if hovered else 2, border_radius=13)
    if hovered:
        pygame.draw.line(screen, color, (rect.x + 15, rect.y + 5),
                         (rect.right - 15, rect.y + 5), 2)
    draw_text(label, font, WHITE, rect.centerx, rect.centery)


MENU_BUTTONS = [
    (pygame.Rect(WIDTH // 2 - 125, 255, 250, 50), "START ADVENTURE", GOLD),
    (pygame.Rect(WIDTH // 2 - 125, 318, 250, 44), "HOW TO PLAY", CYAN),
    (pygame.Rect(WIDTH // 2 - 125, 374, 250, 44), None, PURPLE),
    (pygame.Rect(WIDTH // 2 - 125, 430, 250, 44), "QUIT GAME", PINK),
]


def draw_menu():
    draw_background()
    now = pygame.time.get_ticks()
    glow(CYAN, WIDTH - 95, 82, 26)
    pygame.draw.circle(screen, (220, 240, 255), (WIDTH - 102, 75), 17)

    draw_text("KEY QUEST", title_font, GOLD, WIDTH // 2, 78)
    draw_text("RUINS OF THE ANCIENTS", medium, CYAN, WIDTH // 2, 130)
    draw_text("CLASSIC REIMAGINED EDITION", small, PINK, WIDTH // 2, 160)
    draw_text("FIND THE KEY. SOLVE THE LOCK. ESCAPE THE RUINS.",
              small, WHITE, WIDTH // 2, 186)

    for i in range(9):
        x = 42 + i * 63 + math.sin(now / 500 + i) * 9
        y = 218 + math.cos(now / 400 + i) * 8
        glow([CYAN, PURPLE, GOLD][i % 3], x, y, 3)

    mouse = pygame.mouse.get_pos()
    for rect, label, color in MENU_BUTTONS:
        draw_button(rect, label or f"BEST SCORE: {g.best}", color, rect.collidepoint(mouse))

    draw_text("COINS  |  POWER-UPS  |  COMBAT  |  PUZZLES  |  BOSS",
              small, MUTED, WIDTH // 2, 505)


def draw_howto():
    draw_background()
    draw_panel(pygame.Rect(25, 30, WIDTH - 50, 450), CYAN)
    draw_text("HOW TO PLAY", large, GOLD, WIDTH // 2, 70)
    lines = [
        "ARROWS / WASD - Move (hold to keep walking)",
        "SPACE - Fire a magic bolt (limited ammo)",
        "COINS - Collect them for points",
        "GOLDEN KEY - Needed to use the exit",
        "PURPLE DOOR - Walk into it, repeat the symbols",
        "RED TRAPS / PATROLLERS - Avoid or shoot them",
        "GHOSTS chase you. The GUARDIAN has 3 HP",
        "POWER-UPS: S shield  > speed  + life",
        "                  * bolts  T time crystal",
        "PORTALS - Step on one to jump to the other",
        "ESC - Pause the game",
    ]
    for i, line in enumerate(lines):
        draw_text(line, font, WHITE, WIDTH // 2, 118 + i * 31)
    draw_text("Press any key or click to go back", small, CYAN, WIDTH // 2, 462)


def draw_puzzle():
    draw_background()
    draw_panel(pygame.Rect(25, 48, WIDTH - 50, 410), PURPLE)
    draw_text("ANCIENT SYMBOL LOCK", large, GOLD, WIDTH // 2, 88)

    n = len(g.puzzle_seq)
    always = g.puzzle_show >= 90
    showing = always or g.puzzle_peek > 0
    if always:
        draw_text("REPEAT THE PATTERN SHOWN BELOW", small, WHITE, WIDTH // 2, 122)
    elif showing:
        draw_text(f"MEMORIZE THE PATTERN!  Hiding in {g.puzzle_peek:0.1f}s",
                  small, GOLD, WIDTH // 2, 122)
    else:
        draw_text("THE PATTERN IS HIDDEN - REPEAT IT FROM MEMORY",
                  small, PINK, WIDTH // 2, 122)

    spacing = 56
    start_x = WIDTH // 2 - (n - 1) * spacing / 2
    for i in range(n):
        cx = start_x + i * spacing
        if showing:
            kind = g.puzzle_seq[i]
            draw_symbol(kind, cx, 168, 17, SYMBOL_COLORS[kind])
        else:
            pygame.draw.rect(screen, MUTED, (int(cx) - 20, 148, 40, 40), 2, border_radius=8)
            draw_text("?", medium, MUTED, cx, 168)

    puzzle_buttons.clear()
    for i in range(4):
        rect = pygame.Rect(48 + i * 137, 215, 88, 88)
        puzzle_buttons.append((rect, i))
        pygame.draw.rect(screen, (20, 38, 80), rect, border_radius=15)
        pygame.draw.rect(screen, SYMBOL_COLORS[i], rect, 3, border_radius=15)
        draw_symbol(i, rect.centerx, rect.centery, 25, SYMBOL_COLORS[i])
        draw_text(f"{i + 1}  {SYMBOL_NAMES[i]}", small, MUTED, rect.centerx, rect.bottom + 14)

    draw_text("YOUR INPUT", small, CYAN, WIDTH // 2, 352)
    for i in range(n):
        cx = start_x + i * spacing
        if i < len(g.puzzle_choices):
            kind = g.puzzle_choices[i]
            draw_symbol(kind, cx, 392, 15, SYMBOL_COLORS[kind])
        else:
            pygame.draw.circle(screen, (60, 70, 110), (int(cx), 392), 13, 2)

    draw_text("CLICK or press 1-4   |   WRONG = -5 SECONDS   |   ESC to leave",
              small, MUTED, WIDTH // 2, 435)
    if g.notice_timer > 0:
        r = pygame.Rect(WIDTH // 2 - 175, 8, 350, 30)
        draw_panel(r, GOLD)
        draw_text(g.notice, small, WHITE, WIDTH // 2, 23)


def draw_intro():
    draw_background()
    draw_panel(pygame.Rect(40, 130, WIDTH - 80, 260), g.theme[2])
    draw_text(f"LEVEL {g.level + 1}", large, g.theme[2], WIDTH // 2, 185)
    draw_text(g.level_name, medium, WHITE, WIDTH // 2, 235)
    draw_text(LEVELS[g.level]["tip"], small, MUTED, WIDTH // 2, 285)
    draw_text("Find the key  >  open the door  >  reach the exit",
              small, GOLD, WIDTH // 2, 315)
    if g.intro_info:
        draw_text(g.intro_info, small, GREEN, WIDTH // 2, 350)
    draw_text("Press any key to start", small, CYAN, WIDTH // 2, 470)


def draw_pause():
    draw_maze()
    shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 10, 170))
    screen.blit(shade, (0, 0))
    draw_panel(pygame.Rect(WIDTH // 2 - 160, 200, 320, 150), CYAN)
    draw_text("PAUSED", large, GOLD, WIDTH // 2, 245)
    draw_text("ESC / ENTER - resume", font, WHITE, WIDTH // 2, 292)
    draw_text("M - main menu", font, MUTED, WIDTH // 2, 322)


def draw_end(won):
    draw_background()
    color = GOLD if won else RED
    draw_text("RUINS CONQUERED!" if won else "GAME OVER", title_font, color, WIDTH // 2, 130)
    draw_text("You escaped with the ancient treasure!" if won
              else f"You fell on level {g.level + 1}: {g.level_name}.",
              font, WHITE, WIDTH // 2, 195)
    draw_text(f"FINAL SCORE: {g.score}", medium, GOLD, WIDTH // 2, 250)
    draw_text(f"BEST SCORE: {g.best}", font, CYAN, WIDTH // 2, 295)
    rect = pygame.Rect(WIDTH // 2 - 120, 350, 240, 52)
    draw_button(rect, "PLAY AGAIN", GREEN if won else PINK,
                rect.collidepoint(pygame.mouse.get_pos()))
    draw_text("Press ENTER to play again | ESC for menu", small, MUTED, WIDTH // 2, 430)


def draw():
    st = g.state
    if st == "menu":
        draw_menu()
    elif st == "howto":
        draw_howto()
    elif st == "intro":
        draw_intro()
    elif st == "playing":
        draw_maze()
    elif st == "paused":
        draw_pause()
    elif st == "puzzle":
        draw_puzzle()
    elif st == "win":
        draw_end(True)
    elif st == "gameover":
        draw_end(False)


# =============== INPUT ===============
PUZZLE_KEYS = {pygame.K_1: 0, pygame.K_2: 1, pygame.K_3: 2, pygame.K_4: 3}


def handle_key(key):
    st = g.state
    if st == "menu":
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            start_game()
        elif key == pygame.K_h:
            g.state = "howto"
        elif key == pygame.K_q:
            g.running = False
    elif st == "howto":
        g.state = "menu"
    elif st == "intro":
        g.state = "playing"
    elif st == "playing":
        if key == pygame.K_ESCAPE:
            g.state = "paused"
        elif key == pygame.K_p:
            try_open_puzzle()
        elif key == pygame.K_SPACE:
            shoot()
    elif st == "paused":
        if key in (pygame.K_ESCAPE, pygame.K_RETURN):
            g.state = "playing"
        elif key == pygame.K_m:
            g.state = "menu"
    elif st == "puzzle":
        if key == pygame.K_ESCAPE:
            g.state = "playing"
            g.move_timer = 0.4
        elif key in PUZZLE_KEYS:
            puzzle_click(PUZZLE_KEYS[key])
    elif st in ("win", "gameover"):
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            start_game()
        elif key == pygame.K_ESCAPE:
            g.state = "menu"


def handle_click(pos):
    st = g.state
    if st == "menu":
        if MENU_BUTTONS[0][0].collidepoint(pos):
            start_game()
        elif MENU_BUTTONS[1][0].collidepoint(pos):
            g.state = "howto"
        elif MENU_BUTTONS[3][0].collidepoint(pos):
            g.running = False
    elif st == "howto":
        g.state = "menu"
    elif st == "intro":
        g.state = "playing"
    elif st in ("win", "gameover"):
        if pygame.Rect(WIDTH // 2 - 120, 350, 240, 52).collidepoint(pos):
            start_game()
    elif st == "puzzle":
        for rect, idx in puzzle_buttons:
            if rect.collidepoint(pos):
                puzzle_click(idx)
                break


# =============== MAIN LOOP ===============
def check_levels():
    for i, cfg in enumerate(LEVELS):
        if "grid" in cfg:
            problems = validate_grid(cfg["grid"])
            if problems:
                print(f"WARNING level {i + 1} ({cfg['name']}):", "; ".join(problems))


def main():
    check_levels()
    build_sounds()
    while g.running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        update(dt)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                g.running = False
            elif event.type == pygame.KEYDOWN:
                handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                handle_click(event.pos)
        draw()
        pygame.display.flip()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
