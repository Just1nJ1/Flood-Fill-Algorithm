import random
from functools import partial
import asyncio

import pygame

DEBUG = True
red = lambda x: f"\033[91m{x}\033[0m"
green = lambda x: f"\033[92m{x}\033[0m"

def process(content, code):
    return green(content) if code else red(content)

# Constants
ROWS = 10
COLS = 15
CELL_SIZE = 50
WALL_SIZE = 20
MARGIN = 20
BUTTON_WIDTH = 100
BUTTON_HEIGHT = 30
BUTTON_PADDING = 10

WINDOW_WIDTH = 2 * MARGIN + (WALL_SIZE + CELL_SIZE) * COLS - WALL_SIZE
WINDOW_HEIGHT = 2 * MARGIN + (WALL_SIZE + CELL_SIZE) * ROWS - WALL_SIZE + BUTTON_HEIGHT + 2 * BUTTON_PADDING  # Extra space for button

board_area = pygame.Rect(0, 0, 2 * MARGIN + (WALL_SIZE + CELL_SIZE) * COLS - WALL_SIZE, 2 * MARGIN + (WALL_SIZE + CELL_SIZE) * ROWS - WALL_SIZE)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
LIGHTGRAY = (220, 220, 220)
DARKGRAY = (100, 100, 100)

def get_blue_color(value):
    # Clamp to [0, 40]
    value = max(0, min(20, value))
    t = value / 20

    # Dark blue RGB
    r1, g1, b1 = 0, 102, 255

    # Light blue RGB
    r2, g2, b2 = 173, 216, 230

    # Linear interpolation
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)

    return (r, g, b)

BG_COLOR = WHITE
WALL_DETECTED_COLOR = BLACK
WALL_UNDETECTED_COLOR = DARKGRAY
WALL_INACTIVE_COLOR = LIGHTGRAY
CELL_BG_COLOR = WHITE
CELL_TEXT_COLOR = BLACK
BUTTON_BG_COLOR = WHITE
BUTTON_TEXT_COLOR = BLACK
BUTTON_BORDER_WIDTH = 2
BUTTON_BORDER_COLOR = BLACK

LEFT = (-1, 0)
RIGHT = (1, 0)
UP = (0, -1)
DOWN = (0, 1)
DIRECTIONS = [LEFT, RIGHT, UP, DOWN]
# GOAL = [[7, 4], [7, 5], [8, 4], [8, 5]]

current_location = [0, ROWS - 1]
start = False
returning = False

pygame.init()
FONT = pygame.font.Font(None, 20)

class Wall:
    def __init__(self, i, j, block):
        self.i = i
        self.j = j
        self.x = MARGIN + (WALL_SIZE + CELL_SIZE) * i
        self.y = MARGIN + (WALL_SIZE + CELL_SIZE) * j
        self.block = block
        self.x_wall_rect = pygame.Rect(self.x + CELL_SIZE, self.y, WALL_SIZE, CELL_SIZE)
        self.y_wall_rect = pygame.Rect(self.x, self.y + CELL_SIZE, CELL_SIZE, WALL_SIZE)
        self.clicked_x = False
        self.clicked_y = False

    def draw(self, lim_wall):
        if self.i != COLS - 1:
            if self.block[0]:
                if not start or lim_wall.block[0]:
                    color = WALL_DETECTED_COLOR
                else:
                    color = WALL_UNDETECTED_COLOR
            else:
                color = WALL_INACTIVE_COLOR
            pygame.draw.rect(screen, color, self.x_wall_rect)
        if self.j != ROWS - 1:
            if self.block[1]:
                if not start or lim_wall.block[1]:
                    color = WALL_DETECTED_COLOR
                else:
                    color = WALL_UNDETECTED_COLOR
            else:
                color = WALL_INACTIVE_COLOR
            pygame.draw.rect(screen, color, self.y_wall_rect)

        mouse_pos = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0] == 1:
            if self.x_wall_rect.collidepoint(mouse_pos):
                if not self.clicked_x:
                    self.clicked_x = True
                    self.block[0] = not self.block[0]
                    if DEBUG:
                        print(self.i, self.j)
            else:
                self.clicked_x = False
            if self.y_wall_rect.collidepoint(mouse_pos):
                if not self.clicked_y:
                    self.clicked_y = True
                    self.block[1] = not self.block[1]
                    if DEBUG:
                        print(self.i, self.j)
            else:
                self.clicked_y = False
        if pygame.mouse.get_pressed()[0] == 0:
            self.clicked_x = False
            self.clicked_y = False


class WallCollection:
    def __init__(self):
        self.walls = []
        for i in range(COLS):
            for j in range(ROWS):
                self.walls.append(Wall(i, j, [False, False]))
        self.limited_walls = []
        for i in range(COLS):
            for j in range(ROWS):
                self.limited_walls.append(Wall(i, j, [False, False]))

    def draw(self):
        for i in range(len(self.walls)):
            self.walls[i].draw(self.limited_walls[i])

    def valid_move(self, x, y, direction, use_limited):
        if use_limited:
            target_walls = self.limited_walls
        else:
            target_walls = self.walls
        if direction == LEFT:
            return x != 0 and not target_walls[(x - 1) * ROWS + y].block[0]
        if direction == RIGHT:
            return x != COLS - 1 and not target_walls[x * ROWS + y].block[0]
        if direction == UP:
            return y != 0 and not target_walls[x * ROWS + (y - 1)].block[1]
        if direction == DOWN:
            return y != ROWS - 1 and not target_walls[x * ROWS + y].block[1]
        raise ValueError(f'Invalid direction: {direction}')

    def set_limited_wall(self, x, y, direction, value):
        if direction == LEFT and x != 0:
            self.limited_walls[(x - 1) * ROWS + y].block[0] = value
        if direction == RIGHT and x != COLS - 1:
            self.limited_walls[x * ROWS + y].block[0] = value
        if direction == UP and y != 0:
            self.limited_walls[x * ROWS + (y - 1)].block[1] = value
        if direction == DOWN and y != ROWS - 1:
            self.limited_walls[x * ROWS + y].block[1] = value


class Cell:
    def __init__(self, i, j):
        self.i: int = i
        self.j: int = j
        self.x: int = MARGIN + (WALL_SIZE + CELL_SIZE) * i
        self.y: int = MARGIN + (WALL_SIZE + CELL_SIZE) * j
        self.width: int = CELL_SIZE
        self.height: int = CELL_SIZE
        self.value: int = 65535
        self.text: str | None = None
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.pressed = False
        self.bg_color = CELL_BG_COLOR

    def draw(self, walls):
        if pygame.mouse.get_pressed()[0] == 1 and not self.pressed:
            self.pressed = True
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                if self.text is None:
                    self.text = "GOAL"
                else:
                    self.text = None
                if DEBUG:
                    print(
                        self.i, self.j,
                        process("Left", walls.valid_move(self.i, self.j, LEFT, use_limited=False)),
                        process("Right", walls.valid_move(self.i, self.j, RIGHT, use_limited=False)),
                        process("Up", walls.valid_move(self.i, self.j, UP, use_limited=False)),
                        process("Down", walls.valid_move(self.i, self.j, DOWN, use_limited=False))
                    )
        if pygame.mouse.get_pressed()[0] == 0:
            self.pressed = False

        self.text_surface = FONT.render(str(self.value) if self.text is None else self.text, True, CELL_TEXT_COLOR)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        pygame.draw.rect(screen, self.bg_color, self.rect)
        screen.blit(self.text_surface, self.text_rect)


class CellCollection:
    def __init__(self):
        self.cells = []
        for i in range(COLS):
            for j in range(ROWS):
                self.cells.append(Cell(i, j))

    def goal(self):
        targets = []
        for cell in self.cells:
            if cell.text == "GOAL":
                targets.append([cell.i, cell.j])
        return targets

    def draw(self, walls):
        for cell in self.cells:
            cell.draw(walls)

    def set_value(self, i, j, value):
        self.cells[i * ROWS + j].value = value

    def get_value(self, i, j):
        return self.cells[i * ROWS + j].value

    def set_bgcolor(self, i, j, color):
        self.cells[i * ROWS + j].bg_color = color


class Button:
    def __init__(self, x, y, width=BUTTON_WIDTH, height=BUTTON_HEIGHT, text="Text", callback_fn=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.callback_fn = callback_fn
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.text_surface = FONT.render(str(self.text), True, BUTTON_TEXT_COLOR)
        self.text_rect = self.text_surface.get_rect(center=self.rect.center)
        self.pressed = False

    def draw(self, disable=False):
        if disable:
            return
        pygame.draw.rect(screen, BUTTON_BG_COLOR, self.rect)
        pygame.draw.rect(screen, BUTTON_BORDER_COLOR, self.rect, BUTTON_BORDER_WIDTH)
        screen.blit(self.text_surface, self.text_rect)
        if pygame.mouse.get_pressed()[0] == 1 and self.callback_fn is not None and not self.pressed:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.pressed = True
                self.callback_fn()
        if pygame.mouse.get_pressed()[0] == 0:
            self.pressed = False


class PeekableGenerator:
    def __init__(self, generator):
        self._gen = generator
        self._has_next = True
        self._next = None
        self._advance()

    def _advance(self):
        try:
            self._next = next(self._gen)
        except StopIteration:
            self._next = None
            self._has_next = False

    def has_next(self):
        return self._has_next

    def next(self):
        global start
        start = True
        if not self._has_next:
            raise StopIteration
        result = self._next
        self._advance()
        return result

class TextInputBox:
    def __init__(self, x, y, width, font, screen, color=BLACK, bg_color=WHITE):
        self.x = x
        self.y = y
        self.width = width
        self.font = font
        self.screen = screen
        self.color = color
        self.backcolor = bg_color
        self.active = False
        self.value = 0
        self.rect = pygame.Rect(x, y, width, 20)

    def draw(self):
        text_surface = FONT.render(str(self.value), True, self.color)
        pygame.draw.rect(screen, self.color, self.rect, 2)
        screen.blit(text_surface, (self.x+5, self.y+5))

    def update(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and not self.active:
            self.active = self.rect.collidepoint(event.pos)
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                self.active = False
            elif event.key == pygame.K_BACKSPACE:
                self.value //= 10
            elif event.unicode in "0123456789":
                self.value = self.value * 10 + int(event.unicode)

floodfill_gen: PeekableGenerator | None = None

def floodfill(cells: CellCollection, walls: WallCollection, use_limited: bool = False, targets=None):
    goal = cells.goal() if targets is None else targets
    for cell in cells.cells:
        cell.value = 65535
        cell.bg_color = CELL_BG_COLOR
    for i, j in goal:
        cells.set_value(i, j, 0)
    queue = [g for g in goal]
    last_cell = None
    while len(queue) != 0:
        yield
        tmp = queue.pop(0)
        cells.set_bgcolor(tmp[0], tmp[1], RED)
        if last_cell is not None:
            cells.set_bgcolor(last_cell[0], last_cell[1], get_blue_color(cells.get_value(last_cell[0], last_cell[1])))
        for direction in DIRECTIONS:
            tmp_i = tmp[0] + direction[0]
            tmp_j = tmp[1] + direction[1]
            if walls.valid_move(tmp[0], tmp[1], direction, use_limited):
                new_attemp = cells.get_value(tmp[0], tmp[1]) + 1
                if new_attemp < cells.get_value(tmp_i, tmp_j):
                    cells.set_value(tmp_i, tmp_j, new_attemp)
                    queue.append([tmp_i, tmp_j])
        last_cell = tmp
    if last_cell is not None:
        cells.set_bgcolor(last_cell[0], last_cell[1], get_blue_color(cells.get_value(last_cell[0], last_cell[1])))

def start_floodfill(cells: CellCollection, walls: WallCollection, use_limited: bool = False, targets=None):
    global floodfill_gen, start
    floodfill_gen = PeekableGenerator(floodfill(cells, walls, use_limited, targets))
    start = False

def run_whole_steps():
    global floodfill_gen
    if floodfill_gen is not None:
        while floodfill_gen.has_next():
            floodfill_gen.next()

def random_walls(walls: WallCollection):
    for wall in walls.walls:
        wall.block[0] = random.random() < 0.3
        wall.block[1] = random.random() < 0.3

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Grid with Walls")

# Create cell and wall collections
cells = CellCollection()
walls = WallCollection()
buttons = []

start_floodfill(cells, walls)

def step_func():
    if floodfill_gen is None or not floodfill_gen.has_next():
        return
    else:
        floodfill_gen.next()


def car_move(walls: WallCollection, cells: CellCollection):
    current_x, current_y = current_location
    min_val = 65535
    next_x, next_y = current_location
    for direction in DIRECTIONS:
        if walls.valid_move(current_x, current_y, direction, False):
            val = cells.get_value(current_x + direction[0], current_y + direction[1])
            if val < min_val:
                min_val = val
                next_x, next_y = current_x + direction[0], current_y + direction[1]

    current_location[0] = next_x
    current_location[1] = next_y

def car_observe(walls: WallCollection):
    current_x, current_y = current_location
    for direction in DIRECTIONS:
        is_valid = walls.valid_move(current_x, current_y, direction, False)
        walls.set_limited_wall(current_x, current_y, direction, not is_valid)
        print(current_x, current_y, direction, is_valid)

def car_step(walls: WallCollection, cells: CellCollection):
    global returning
    car_observe(walls)
    
    goals = cells.goal()
    origin = [[0, ROWS - 1]]
    
    target_locs = origin if returning else goals
    
    if current_location in target_locs:
        returning = not returning
        target_locs = origin if returning else goals
        start_floodfill(cells, walls, use_limited=True, targets=target_locs)
        run_whole_steps()
    else:
        car_move(walls, cells)
        car_observe(walls)
        start_floodfill(cells, walls, use_limited=True, targets=target_locs)
        run_whole_steps()

def draw_circle_alpha(surface, color, center, radius):
    target_rect = pygame.Rect(center, (0, 0)).inflate((radius * 2, radius * 2))
    shape_surf = pygame.Surface(target_rect.size, pygame.SRCALPHA)
    pygame.draw.circle(shape_surf, color, (radius, radius), radius)
    surface.blit(shape_surf, target_rect)

def draw_car_loc():
    radius = CELL_SIZE // 4
    x = MARGIN + (WALL_SIZE + CELL_SIZE) * current_location[0] + CELL_SIZE // 2
    y = MARGIN + (WALL_SIZE + CELL_SIZE) * current_location[1] + CELL_SIZE // 2
    # pygame.draw.circle(screen, RED, (x, y), radius, 0)
    draw_circle_alpha(screen, (255, 0, 0, 127), (x, y), radius)

def reset():
    global current_location, returning
    current_location = [0, ROWS - 1]
    returning = False
    start_floodfill(cells, walls)
    for w in walls.limited_walls:
        w.block[0] = False
        w.block[1] = False


button = Button(MARGIN + BUTTON_PADDING, board_area.bottom + BUTTON_PADDING, text="Reset", callback_fn=reset)
button2 = Button(MARGIN + BUTTON_PADDING * 3 + BUTTON_WIDTH, board_area.bottom + BUTTON_PADDING, text="Floodfill Real", callback_fn=run_whole_steps)
button3 = Button(MARGIN + BUTTON_PADDING * 5 + BUTTON_WIDTH * 2, board_area.bottom + BUTTON_PADDING, text="Floodfill Step", callback_fn=step_func)
button4 = Button(MARGIN + BUTTON_PADDING * 7 + BUTTON_WIDTH * 3, board_area.bottom + BUTTON_PADDING, text="Random Walls", callback_fn=partial(random_walls, walls))
button5 = Button(MARGIN + BUTTON_PADDING * 9 + BUTTON_WIDTH * 4, board_area.bottom + BUTTON_PADDING, text="Car Step", callback_fn=partial(car_step, walls, cells))
text_box = TextInputBox(MARGIN + BUTTON_PADDING * 11 + BUTTON_WIDTH * 5, board_area.bottom + BUTTON_PADDING, 200, FONT, screen)

buttons.append(button)
buttons.append(button2)
buttons.append(button3)
buttons.append(button4)
buttons.append(button5)

async def main():
    running = True
    while running:
        screen.fill(BG_COLOR)
        pygame.draw.rect(screen, WALL_DETECTED_COLOR, board_area)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            text_box.update(event)

        walls.draw()
        cells.draw(walls)
        draw_car_loc()

        for b in buttons:
            b.draw()

        text_box.draw()

        pygame.display.flip()

        await asyncio.sleep(0)

asyncio.run(main())
