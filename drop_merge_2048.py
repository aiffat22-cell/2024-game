import pygame
import random
import sys
import os
import time
import math
import json
from datetime import datetime

# --- CONFIGURATION ---
WIDTH, HEIGHT = 450, 800

# Vertical Layout
HEADER_H = 120
FOOTER_H = 130
SPAWN_AREA_H = 110 
BOARD_PAD_TOP = 15
BOARD_PAD_SIDE = 15

# Calc Board Size
AVAIL_H = HEIGHT - HEADER_H - FOOTER_H - SPAWN_AREA_H - BOARD_PAD_TOP
COLS, ROWS = 5, 7
GAP = 8

# Tile Dimensions
CELL_W = (WIDTH - (BOARD_PAD_SIDE*2) - (COLS-1)*GAP) // COLS
CELL_H = (AVAIL_H - (ROWS-1)*GAP) // ROWS
TILE_SIZE = min(CELL_W, CELL_H)
BOARD_W = TILE_SIZE*COLS + GAP*(COLS-1)
BOARD_H = TILE_SIZE*ROWS + GAP*(ROWS-1)
BOARD_X = (WIDTH - BOARD_W) // 2
BOARD_Y = HEADER_H + BOARD_PAD_TOP

# --- THEME PALETTE ---
C_BG            = (18, 14, 28)       # Deep Night
C_PANEL_DARK    = (30, 22, 40)       # UI Panels
C_SLOT          = (45, 30, 60)       # Empty Grid
C_PASTEL_PURP   = (190, 160, 240)    # Selector Overlay 
C_ACCENT        = (255, 190, 0)      # Gold
C_WHITE         = (255, 255, 255)
C_PURPLE_GLOW   = (160, 100, 255)

# Text & Msg
C_MSG_RECORD    = (0, 255, 150)      # Spring Green
C_BTN_OFF       = (70, 60, 85)
C_BTN_ON        = (180, 50, 80)      # Active Tool

# --- TILE COLORS (Corrected Name) ---
TILE_COLORS = {
    0:    ((0,0,0,0), (0,0,0)), 
    2:    ((100, 80, 220), (255,255,255)), # Periwinkle
    4:    ((120, 90, 240), (255,255,255)),
    8:    ((150, 80, 255), (255,255,255)),
    16:   ((180, 70, 220), (255,255,255)),
    32:   ((220, 60, 180), (255,255,255)),
    64:   ((255, 80, 80),  (255,255,255)),
    128:  ((255, 140, 40), (255,255,255)),
    256:  ((255, 200, 50), (30, 30, 30)),
    512:  ((50, 255, 255), (0,0,0)),        # Cyan Neon
    1024: ((40, 40, 40),   (255,255,255)),
}

# Image Config
ICON_PATHS = {"H": "icon_hammer.png", "S": "icon_swap.png", "U": "icon_undo.png"}
FONT_NAME = "segoeui" if os.name == 'nt' else "arial"

# --- SYSTEM UTILS ---

def load_icon(char, size=40):
    path = ICON_PATHS.get(char, "")
    if os.path.exists(path):
        try:
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(img, (size, size)), None
        except: pass
    return None, char

def draw_rounded(surf, col, rect, r=10):
    pygame.draw.rect(surf, col, rect, border_radius=r)

# --- MANAGERS ---

class HistoryManager:
    """Handles Score Saving & History List"""
    def __init__(self):
        self.filename = "history.json"
        self.scores = self.load() # List of dicts {score, date}
    
    def load(self):
        if not os.path.exists(self.filename): return []
        try:
            with open(self.filename, 'r') as f: return json.load(f)
        except: return []

    def add_entry(self, score):
        if score == 0: return
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = {"score": score, "date": now}
        self.scores.append(entry)
        self.scores.sort(key=lambda x: x['score'], reverse=True)
        self.scores = self.scores[:50]
        self.save()
    
    def save(self):
        with open(self.filename, 'w') as f: json.dump(self.scores, f)

    def get_best(self):
        if not self.scores: return 0
        return self.scores[0]['score']

# --- VISUALS ---

class Particle:
    def __init__(self, x, y, color, gravity=0.5, life_speed=0.05):
        self.x=x; self.y=y; self.color=color
        a=random.uniform(0, 6.28); s=random.uniform(2, 6)
        self.vx=math.cos(a)*s; self.vy=math.sin(a)*s
        self.life=1.0; self.grav=gravity; self.dec=life_speed
    def update(self):
        self.x+=self.vx; self.y+=self.vy; self.vy+=self.grav
        self.life-=self.dec
        return self.life>0
    def draw(self, s):
        alp = int(255*self.life)
        if alp>0:
            surf = pygame.Surface((6,6), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*self.color[:3], alp), (3,3), 3)
            s.blit(surf, (self.x, self.y))

class FloatText:
    def __init__(self, text, x, y, color):
        self.text=str(text); self.x=x; self.y=y; self.col=color
        self.font=pygame.font.SysFont(FONT_NAME, 30, bold=True)
        self.alpha=255
    def update(self):
        self.y-=2; self.alpha-=4
        return self.alpha>0
    def draw(self, s):
        tx = self.font.render(self.text, True, self.col)
        tx.set_alpha(self.alpha)
        s.blit(tx, tx.get_rect(center=(self.x, self.y)))

class VisualFX:
    def __init__(self):
        self.particles = []
        self.texts = []

    def spawn_confetti(self):
        for _ in range(50):
            x = random.randint(0, WIDTH)
            y = random.randint(0, HEIGHT//2)
            c = random.choice([C_ACCENT, C_PURPLE_GLOW, (0,255,255)])
            self.particles.append(Particle(x,y,c, gravity=0.1, life_speed=0.01))

    def spawn_merge_poof(self, x, y, color):
        for _ in range(12):
            self.particles.append(Particle(x,y,color))

    def add_msg(self, text, x, y, col):
        self.texts.append(FloatText(text, x, y, col))

    def update(self, screen):
        self.particles = [p for p in self.particles if p.update()]
        for p in self.particles: p.draw(screen)
        
        self.texts = [t for t in self.texts if t.update()]
        for t in self.texts: t.draw(screen)

class FallingBlock:
    def __init__(self, r, c, val):
        self.r, self.c, self.val = r, c, val
        self.target_y = BOARD_Y + GAP + r*(TILE_SIZE+GAP)
        self.x = BOARD_X + GAP + c*(TILE_SIZE+GAP)
        self.y = BOARD_Y - TILE_SIZE # Start above
        self.vy = 25 # Fast speed
        self.done = False
    def update(self):
        self.y += self.vy
        if self.y >= self.target_y:
            self.y = self.target_y
            self.done = True
    def draw(self, s):
        bg, txt = TILE_COLORS.get(self.val, TILE_COLORS[1024])
        r = pygame.Rect(self.x, self.y, TILE_SIZE, TILE_SIZE)
        draw_rounded(s, bg, r, 8)
        f = pygame.font.SysFont(FONT_NAME, 32, bold=True)
        t = f.render(str(self.val), True, txt)
        s.blit(t, t.get_rect(center=r.center))

# --- MAIN GAME CLASS ---

class GamePro:
    def __init__(self):
        self.hist_mgr = HistoryManager()
        self.fx = VisualFX()
        self.reset()
        
    def reset(self):
        self.board = [[0]*COLS for _ in range(ROWS)]
        self.score = 0
        self.best_at_start = self.hist_mgr.get_best()
        self.celebrated_best = False
        
        self.gems = 20
        self.curr = self.rnd()
        self.next = self.rnd()
        
        self.state = "IDLE" 
        self.undo_stack = []
        self.hammer_on = False
        self.timer = 0
        self.fallers = []

    def rnd(self): return random.choice([2,2,4,4,8,8,16])

    def save_state(self):
        if len(self.undo_stack) > 3: self.undo_stack.pop(0)
        snapshot = {
            'b': [row[:] for row in self.board],
            's': self.score,
            'g': self.gems,
            'c': self.curr,
            'n': self.next
        }
        self.undo_stack.append(snapshot)

    def restore_state(self):
        if self.gems < 5 or not self.undo_stack: return
        self.gems -= 5
        st = self.undo_stack.pop()
        self.board = st['b']
        self.score = st['s']
        self.gems = st['g'] - 5 
        self.curr = st['c']
        self.next = st['n']
        self.fx.add_msg("UNDO", WIDTH//2, HEIGHT-200, C_WHITE)

    def update_logic(self):
        if self.score > self.best_at_start and not self.celebrated_best and self.best_at_start > 0:
            self.celebrated_best = True
            self.fx.spawn_confetti()
            self.fx.add_msg("NEW RECORD!", WIDTH//2, HEADER_H + 50, C_MSG_RECORD)

        if self.state == "FALL":
            active = False
            for b in self.fallers:
                b.update()
                if not b.done: active = True
            
            if not active:
                for b in self.fallers:
                    self.board[b.r][b.c] = b.val
                self.fallers = []
                
                if self.check_loss():
                    self.end_game()
                else:
                    self.state = "MERGE_WAIT"
                    self.timer = 5
        
        elif self.state == "MERGE_WAIT":
            if self.timer>0: self.timer-=1
            else:
                hit = self.check_merges()
                if hit:
                    self.state = "GRAVITY_WAIT"
                    self.timer = 15
                else:
                    self.state = "IDLE"
        
        elif self.state == "GRAVITY_WAIT":
            if self.timer>0: self.timer-=1
            else:
                self.apply_gravity()
                self.state = "MERGE_WAIT"
                self.timer = 5

    def check_merges(self):
        visited = set()
        merged = False
        for r in range(ROWS-1, -1, -1):
            for c in range(COLS):
                if self.board[r][c] == 0 or (r,c) in visited: continue
                val = self.board[r][c]
                group = self.bfs_group(r, c, val)
                if len(group) >= 2:
                    merged = True
                    group.sort(key=lambda x: x[0], reverse=True)
                    anchor = group[0]
                    new_val = val * 2
                    self.score += new_val
                    
                    if new_val==512: self.gems+=2; self.fx.add_msg("GEMS!", WIDTH//2, HEIGHT//2, C_ACCENT)

                    for cell in group:
                        visited.add(cell)
                        # Fix: Use TILE_COLORS here instead of missing gradients var
                        col_rgb = TILE_COLORS.get(val, TILE_COLORS[1024])[0]
                        self.fx.spawn_merge_poof(
                            BOARD_X+GAP+cell[1]*(TILE_SIZE+GAP)+TILE_SIZE//2,
                            BOARD_Y+GAP+cell[0]*(TILE_SIZE+GAP)+TILE_SIZE//2, col_rgb)
                        
                        if cell == anchor:
                            self.board[cell[0]][cell[1]] = new_val
                            px = BOARD_X+GAP+cell[1]*(TILE_SIZE+GAP)+TILE_SIZE//2
                            py = BOARD_Y+GAP+cell[0]*(TILE_SIZE+GAP)
                            self.fx.add_msg(f"+{new_val}", px, py, C_WHITE)
                        else:
                            self.board[cell[0]][cell[1]] = 0

        return merged

    def bfs_group(self, r, c, val):
        stack = [(r,c)]
        grp = []
        while stack:
            curr = stack.pop()
            if curr in grp: continue
            grp.append(curr)
            for d in [(0,1),(0,-1),(1,0),(-1,0)]:
                nr,nc = curr[0]+d[0], curr[1]+d[1]
                if 0<=nr<ROWS and 0<=nc<COLS and self.board[nr][nc]==val:
                    stack.append((nr,nc))
        return grp

    def apply_gravity(self):
        for c in range(COLS):
            col_dat = [self.board[r][c] for r in range(ROWS) if self.board[r][c]!=0]
            new_col = [0]*(ROWS-len(col_dat)) + col_dat
            for r in range(ROWS): self.board[r][c] = new_col[r]

    def action_drop(self, col):
        if self.state != "IDLE": return
        lr = -1
        for r in range(ROWS-1, -1, -1):
            if self.board[r][col] == 0:
                lr = r; break
        if lr == -1: return 
        self.save_state()
        self.fallers = [FallingBlock(lr, col, self.curr)]
        self.curr = self.next
        self.next = self.rnd()
        self.state = "FALL"
    
    def action_swap(self):
        if self.gems < 2: return
        self.save_state()
        self.gems -= 2
        self.curr, self.next = self.next, self.curr
        self.fx.add_msg("SWAP", WIDTH//2, HEIGHT-200, C_ACCENT)

    def action_hammer(self, r, c):
        if self.board[r][c] != 0:
            self.save_state()
            self.gems -= 10
            self.board[r][c] = 0
            self.fx.spawn_merge_poof(
                 BOARD_X+GAP+c*(TILE_SIZE+GAP)+TILE_SIZE//2, 
                 BOARD_Y+GAP+r*(TILE_SIZE+GAP)+TILE_SIZE//2, C_WHITE)
            self.hammer_on = False
            self.apply_gravity()

    def check_loss(self):
        full = 0
        for c in range(COLS):
            if self.board[0][c] != 0: full += 1
        return full == COLS
        
    def end_game(self):
        self.state = "OVER"
        self.hist_mgr.add_entry(self.score)

# --- RENDERER ---

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("2048: Fusion Pro")
clock = pygame.time.Clock()
G = GamePro()

def draw_text(t, x, y, size=20, col=C_WHITE, align="center"):
    f = pygame.font.SysFont(FONT_NAME, size, bold=True)
    surf = f.render(str(t), True, col)
    if align=="center": r = surf.get_rect(center=(x,y))
    else: r = surf.get_rect(topleft=(x,y))
    screen.blit(surf, r)

def draw_ui():
    screen.fill(C_BG)

    # 1. BOARD
    br = pygame.Rect(BOARD_X-5, BOARD_Y-5, BOARD_W+10, BOARD_H+10)
    draw_rounded(screen, C_PANEL_DARK, br, 15)

    mx, my = pygame.mouse.get_pos()
    col_hov = -1
    if G.state == "IDLE" and not G.hammer_on:
         if BOARD_X <= mx <= BOARD_X+BOARD_W and BOARD_Y <= my <= BOARD_Y+BOARD_H:
              col_hov = (mx - BOARD_X) // (TILE_SIZE+GAP)

    for c in range(COLS):
        bx = BOARD_X + GAP + c*(TILE_SIZE+GAP)
        sl = pygame.Rect(bx, BOARD_Y+GAP, TILE_SIZE, BOARD_H-GAP)
        draw_rounded(screen, C_SLOT, sl, 8)
        
        if col_hov == c:
             s = pygame.Surface((TILE_SIZE, sl.height), pygame.SRCALPHA)
             s.fill(C_PASTEL_PURP)
             screen.blit(s, (bx, sl.y))
             
        for r in range(ROWS):
            v = G.board[r][c]
            if v != 0:
                y = BOARD_Y + GAP + r*(TILE_SIZE+GAP)
                draw_cell(bx, y, v)

    for b in G.fallers: b.draw(screen)

    # 2. HEADER
    pygame.draw.rect(screen, (25, 18, 35), (0,0,WIDTH,HEADER_H))
    draw_text("SCORE", WIDTH//2, 30, 14, (150,140,180))
    draw_text(str(G.score), WIDTH//2, 60, 50, C_WHITE)
    
    gem_rect = pygame.Rect(30, 75, 80, 30)
    pygame.draw.rect(screen, (0,0,0), gem_rect, border_radius=15)
    draw_text(f"💎 {G.gems}", 70, 90, 18, C_ACCENT)
    
    best_curr = max(G.score, G.hist_mgr.get_best())
    draw_text(f"🏆 {best_curr}", 60, 40, 18, (0,200,200))
    
    btn_m = pygame.Rect(WIDTH-60, 30, 45, 45)
    draw_rounded(screen, C_BTN_OFF, btn_m, 10)
    cx, cy = btn_m.centerx, btn_m.centery
    for dy in [-6, 0, 6]:
        pygame.draw.line(screen, C_WHITE, (cx-10, cy+dy), (cx+10, cy+dy), 2)
    
    # 3. SPAWNER
    cy = BOARD_Y + BOARD_H + 40
    draw_text("NEXT", WIDTH//2 + 90, cy-15, 12, (100,100,100))
    nx_r = pygame.Rect(WIDTH//2+75, cy, 30, 30)
    bg, tx = TILE_COLORS.get(G.next, TILE_COLORS[2])
    draw_rounded(screen, bg, nx_r, 6)
    draw_text(str(G.next), nx_r.centerx, nx_r.centery, 16, tx)
    
    bg_c, tx_c = TILE_COLORS.get(G.curr, TILE_COLORS[2])
    cur_r = pygame.Rect(0,0,75,75)
    cur_r.center = (WIDTH//2, cy+10)
    pygame.draw.rect(screen, (255,255,255), cur_r.inflate(4,4), border_radius=14)
    draw_rounded(screen, bg_c, cur_r, 12)
    draw_text(str(G.curr), cur_r.centerx, cur_r.centery, 40, tx_c)

    # 4. FOOTER
    btns = [
        ("HAMMER (10)", "H", G.hammer_on, 10),
        ("SWAP (2)", "S", False, 2),
        ("UNDO (5)", "U", False, 5)
    ]
    bx = (WIDTH - (3*70 + 40))//2
    by = HEIGHT - 110
    
    for idx, (label, icon, act, cost) in enumerate(btns):
        x = bx + idx*90
        r = pygame.Rect(x, by, 70, 70)
        col = C_BTN_OFF
        if G.gems >= cost and r.collidepoint(mx, my): col = (100, 80, 120)
        if act: col = C_BTN_ON
        draw_rounded(screen, col, r, 16)
        
        ic, _ = load_icon(icon)
        if ic: screen.blit(ic, ic.get_rect(center=(r.centerx, r.centery-10)))
        else: draw_text(icon, r.centerx, r.centery-10, 30)
        c_col = C_ACCENT if G.gems >= cost else (150,150,150)
        draw_text(str(cost), r.centerx, r.centery+20, 16, c_col)

    # 5. OVERLAYS
    G.fx.update(screen)
    
    if G.state == "OVER":
        draw_overlay("GAME OVER", "Open Menu to Restart", (255, 100, 100))

    if G.state == "MENU":
        draw_menu(mx, my)

    if G.state == "HISTORY":
        draw_history_page(mx, my)

def draw_cell(x, y, v):
    r = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
    b, t = TILE_COLORS.get(v, TILE_COLORS[1024])
    draw_rounded(screen, b, r, 8)
    pygame.draw.rect(screen, (255,255,255,50), r, 2, border_radius=8)
    f_sz = 34 if v < 100 else 26
    draw_text(str(v), r.centerx, r.centery, f_sz, t)
    if v >= 512:
         pygame.draw.rect(screen, (0,255,255), r.inflate(2,2), 2, border_radius=8)

def draw_overlay(title, sub, col):
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    s.fill((0,0,0,200))
    screen.blit(s, (0,0))
    draw_text(title, WIDTH//2, HEIGHT//2 - 20, 50, col)
    draw_text(sub, WIDTH//2, HEIGHT//2 + 30, 20, C_WHITE)

def draw_menu(mx, my):
    s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); s.fill((0,0,0,200)); screen.blit(s,(0,0))
    panel = pygame.Rect((WIDTH-280)//2, (HEIGHT-350)//2, 280, 350)
    draw_rounded(screen, C_PANEL_DARK, panel, 20)
    pygame.draw.rect(screen, C_ACCENT, panel, 2, border_radius=20)
    draw_text("MENU", panel.centerx, panel.y + 40, 30)
    
    opts = ["RESUME", "RESTART", "📜 HISTORY", "QUIT"]
    oy = panel.y + 100
    for o in opts:
        btn = pygame.Rect(panel.x+40, oy, 200, 45)
        c = C_BTN_OFF
        if btn.collidepoint(mx, my): c = C_BTN_ON
        draw_rounded(screen, c, btn, 10)
        draw_text(o, btn.centerx, btn.centery)
        oy += 60

def draw_history_page(mx, my):
    s = pygame.Surface((WIDTH, HEIGHT)); s.fill(C_BG); screen.blit(s,(0,0))
    draw_text("GAME HISTORY", WIDTH//2, 50, 40)
    
    bb = pygame.Rect(20, 30, 80, 40)
    draw_rounded(screen, C_BTN_OFF, bb, 8)
    draw_text("BACK", bb.centerx, bb.centery)
    
    sy = 120
    sc = G.hist_mgr.scores
    if not sc: draw_text("No games recorded yet.", WIDTH//2, 200, 20, (150,150,150))
    else:
        for i, entry in enumerate(sc[:10]): 
             bg = (40, 30, 50) if i%2==0 else (50, 40, 60)
             pygame.draw.rect(screen, bg, (40, sy, WIDTH-80, 40), border_radius=5)
             draw_text(f"#{i+1}", 70, sy+20, 20, C_ACCENT)
             draw_text(str(entry['score']), 180, sy+20, 20, C_WHITE)
             draw_text(entry['date'][5:], 320, sy+20, 16, (150,150,150))
             sy += 50

# --- LOOP ---
while True:
    G.update_logic()
    
    if G.state == "HISTORY": draw_history_page(*pygame.mouse.get_pos())
    elif G.state == "MENU": 
         draw_ui(); draw_menu(*pygame.mouse.get_pos()) # Re-draw BG then menu
    else: draw_ui()
    
    pygame.display.flip()
    clock.tick(60)
    
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
             G.end_game(); sys.exit()
             
        if e.type == pygame.MOUSEBUTTONDOWN:
            mx, my = pygame.mouse.get_pos()
            
            if G.state == "MENU":
                box_x = (WIDTH-280)//2; box_y = (HEIGHT-350)//2
                opts = ["RESUME", "RESTART", "📜 HISTORY", "QUIT"]
                oy = box_y + 100
                for o in opts:
                    if pygame.Rect(box_x+40, oy, 200, 45).collidepoint(mx, my):
                        if o=="RESUME": G.state = "IDLE"
                        elif o=="RESTART": G.reset()
                        elif o=="QUIT": G.end_game(); sys.exit()
                        elif o=="📜 HISTORY": G.state = "HISTORY"
                    oy+=60
                continue
            
            if G.state == "HISTORY":
                 if pygame.Rect(20, 30, 80, 40).collidepoint(mx, my): G.state = "MENU"
                 continue

            if pygame.Rect(WIDTH-60, 30, 45, 45).collidepoint(mx,my):
                G.state = "MENU"; continue
            
            bx = (WIDTH - (3*70+40))//2; by = HEIGHT - 110
            if pygame.Rect(bx, by, 70, 70).collidepoint(mx,my):
                 if G.gems>=10: G.hammer_on = not G.hammer_on
            elif pygame.Rect(bx+90, by, 70, 70).collidepoint(mx,my): G.action_swap()
            elif pygame.Rect(bx+180, by, 70, 70).collidepoint(mx,my): G.restore_state()
            
            if G.state == "IDLE":
                if BOARD_X<=mx<=BOARD_X+BOARD_W and BOARD_Y<=my<=BOARD_Y+BOARD_H:
                    c = (mx - BOARD_X) // (TILE_SIZE+GAP)
                    if 0<=c<COLS:
                         if G.hammer_on:
                             r = (my - BOARD_Y)//(TILE_SIZE+GAP)
                             if 0<=r<ROWS: G.action_hammer(r, c)
                         else:
                             G.action_drop(c)