import tkinter as tk
import time
from constants import *


class Entity:
    """기본 위치/충돌/중력 처리를 담당하는 모든 오브젝트의 베이스 클래스."""
    def __init__(self, canvas, x, y, w, h, color):
        self.canvas = canvas
        self.x, self.y = float(x), float(y)
        self.w, self.h = w, h
        self.dx, self.dy = 0.0, 0.0
        self.on_ground = False
        self.body = canvas.create_rectangle(x, y, x+w, y+h, fill=color, outline="black")

    def update_physics(self, map_data):
        gravity_factor = 1.0
        if hasattr(self, 'is_floating') and self.is_floating:
            gravity_factor = 0.2
        
        self.dy += (GRAVITY * gravity_factor)
        self.x += self.dx
        self.check_col(map_data, "x")
        self.y += self.dy
        self.check_col(map_data, "y")
        
        item_type = self.canvas.type(self.body)
        if item_type == "image":
            if hasattr(self, 'char_type') and self.char_type == "stranger" and (self.is_firing or self.is_casting):
                if self.current_dir == "right": 
                    self.canvas.coords(self.body, self.x, self.y + self.h)
                    self.canvas.itemconfig(self.body, anchor="sw")
                else: 
                    self.canvas.coords(self.body, self.x + self.w, self.y + self.h)
                    self.canvas.itemconfig(self.body, anchor="se")
            elif hasattr(self, 'is_dashing') and self.is_dashing:
                 self.canvas.coords(self.body, self.dash_visual_x, self.y + self.h)
                 self.canvas.itemconfig(self.body, anchor="s")
            else:
                self.canvas.coords(self.body, self.x + (self.w/2), self.y + self.h)
                self.canvas.itemconfig(self.body, anchor="s")
            
            if hasattr(self, 'update_animation'):
                self.update_animation()
        else:
            self.canvas.coords(self.body, self.x, self.y, self.x + self.w, self.y + self.h)

    def check_col(self, map_data, axis):
        if self.x < 0: self.x = 0
        if self.x > MAP_WIDTH - self.w: self.x = MAP_WIDTH - self.w

        left = int(self.x / TILE_SIZE)
        right = int((self.x + self.w - 0.1) / TILE_SIZE)
        top = int(self.y / TILE_SIZE)
        bottom = int((self.y + self.h - 0.1) / TILE_SIZE)

        if axis == "x":
            if self.dx > 0:
                if self.is_wall(map_data, top, right) or self.is_wall(map_data, bottom, right):
                    self.x = (right * TILE_SIZE) - self.w - 0.1
                    self.dx *= -1 
            elif self.dx < 0:
                if self.is_wall(map_data, top, left) or self.is_wall(map_data, bottom, left):
                    self.x = (left + 1) * TILE_SIZE + 0.1
                    self.dx *= -1

        elif axis == "y":
            if self.dy > 0:
                if self.is_wall(map_data, bottom, left) or self.is_wall(map_data, bottom, right):
                    self.y = (bottom * TILE_SIZE) - self.h
                    self.dy = 0
                    self.on_ground = True
                    return
            elif self.dy < 0:
                if self.is_wall(map_data, top, left) or self.is_wall(map_data, top, right):
                    self.y = (top + 1) * TILE_SIZE
                    self.dy = 0
            self.on_ground = False

    def is_wall(self, map_data, r, c):
        if 0 <= r < MAP_ROWS and 0 <= c < MAP_COLS: return map_data[r][c] == 1
        return True


class Monster(Entity):
    """몬스터 공통 로직: 크기/스탯 로딩, 이미지 스프라이트, AI 이동·투사체 쿨다운."""
    def __init__(self, canvas, x, y, m_type):
        data = MONSTER_DB[m_type]
        if m_type in ["enemy0", "enemy1"]:
            w, h = 60, 78
        elif m_type == "enemy2":
            w, h = 60, 73
        elif m_type == "Boss":
            w, h = 200, 150
        elif m_type == "enemy3":
            w, h = 60, 94
        else:
            w, h = 40, 40
        super().__init__(canvas, x, y, w, h, data["color"])
        self.data = data
        self.hp = data["hp"]
        self.max_hp = data["hp"]
        self.dx = data["speed"] 
        self.left_bound = None
        self.right_bound = None
        self.target_player = False
        self.is_boss = (m_type == "Boss")
        self.boss_last_shot = 0.0
        self.boss_shot_cd = 3.5

        if m_type in ["enemy0", "enemy1", "enemy2", "Boss", "enemy3"]:
            try:
                if not hasattr(Monster, "_img_cache"):
                    Monster._img_cache = {}
                if m_type == "enemy0":
                    key, file = "enemy0", "image/enemy0.png"
                elif m_type == "enemy1":
                    key, file = "enemy1", "image/enemy1.png"
                elif m_type == "enemy2":
                    key, file = "enemy2", "image/enemy2.png"
                elif m_type == "Boss":
                    key, file = "boss", "image/boss.png"
                else:
                    key, file = "enemy3", "image/enemy3.png"
                if key not in Monster._img_cache:
                    Monster._img_cache[key] = tk.PhotoImage(file=file)
                img = Monster._img_cache[key]
                self.canvas.delete(self.body)
                self.body = self.canvas.create_image(self.x, self.y, image=img, anchor="nw")
            except Exception:
                pass

    def update_physics(self, map_data):
        """플레이어 추적 옵션/플랫폼 한계 적용 후 기본 물리 처리."""
        if self.target_player and not self.is_boss and hasattr(self.canvas, "game_instance") and self.canvas.game_instance.player:
            px = self.canvas.game_instance.player.x
            if abs(px - self.x) > 2:
                self.dx = self.data["speed"] if px > self.x else -self.data["speed"]
        super().update_physics(map_data)
        if self.left_bound is not None and self.right_bound is not None:
            if self.x < self.left_bound:
                self.x = self.left_bound
                self.dx = abs(self.dx)
            elif self.x > self.right_bound - self.w:
                self.x = self.right_bound - self.w
                self.dx = -abs(self.dx)


class Player(Entity):
    """플레이어 캐릭터: 스탯, 상태 플래그, 공격/스킬/애니메이션·사운드 제어."""
    def __init__(self, canvas, x, y, char_type="iron"):
        self.canvas = canvas
        self.char_type = char_type
        self.x, self.y = float(x), float(y)
        self.dx, self.dy = 0.0, 0.0
        self.on_ground = False
        
        if self.char_type == "iron":
            self.w = 45; self.h = 96
        elif self.char_type == "strider":
            self.w = 50; self.h = 96 
        elif self.char_type == "stranger":
            self.w = 50; self.h = 96
        elif self.char_type == "freischutz":
            self.w = 45; self.h = 92

        self.level, self.exp, self.max_exp = 1, 0, 100
        self.hp, self.max_hp = 100, 100
        self.base_atk = 10
        if char_type == "strider": self.base_atk = 15
        elif char_type == "stranger": self.base_atk = 12
        elif char_type == "freischutz": self.base_atk = 14

        self.base_def, self.equip_atk, self.equip_def = 0, 0, 0
        self.inventory = []
        self.equipped = {"weapon": None, "armor": None}
        
        self.is_attacking = False
        self.is_dashing = False
        self.invincible = 0
        self.dash_cooldown = 0
        self.can_dash_cancel = False
        self.last_tap_key = None
        self.last_tap_time = 0.0

        self.z_press_time = 0.0
        self.is_casting = False     
        self.is_firing = False      
        self.fire_start_time = 0.0
        self.plasma_hits = 0
        self.is_floating = False
        self.float_dmg_timer = 0
        self.must_release_d = False
        
        self.combo_step = 1
        self.last_atk_time = 0.0
        self.attack_cooldown = 0
        self.is_skilling = False
        self.skill_end_pending = False
        self.skill_hit_targets = set()
        self.skill_render_x = 0.0
        self.skill_anchor = "s"
        self.combo_imgs = {}
        self.attack_hit_consumed = False
        self.walk_sound_playing = False
        self.plasma_sound_playing = False
        
        self.draw_anchor = "s"
        self.dash_visual_x = 0

        self.frames = {
            "right_walk": [], "left_walk": [], 
            "right_idle": [], "left_idle": [],
            "right_attack": [], "left_attack": [],
            "right_dash": [], "left_dash": [],
            "right_cast": [], "left_cast": [],
            "right_skill": [], "left_skill": [] 
        }
        self.jump_imgs = {}
        self.beam_imgs = {}

        try:
            prefix = f"{char_type}_"
            
            if self.char_type in ["strider", "stranger", "freischutz"]:
                try:
                    img_r = tk.PhotoImage(file=f"image/{prefix}idle_right.png")
                    img_l = tk.PhotoImage(file=f"image/{prefix}idle_left.png")
                    self.frames["right_idle"].append(img_r)
                    self.frames["left_idle"].append(img_l)
                    
                    if self.char_type == "freischutz":
                         for d in ["right", "left"]:
                            idx = 0
                            while True:
                                try:
                                    img = tk.PhotoImage(file=f"image/{prefix}walk_{d}.gif", format=f"gif -index {idx}")
                                    self.frames[f"{d}_walk"].append(img)
                                    idx += 1
                                except: break
                    else:
                        self.frames["right_walk"].append(img_r)
                        self.frames["left_walk"].append(img_l)
                except: pass
            else: 
                for d in ["right", "left"]:
                    idx = 0
                    while True:
                        try:
                            img = tk.PhotoImage(file=f"image/{prefix}walk_{d}.gif", format=f"gif -index {idx}")
                            self.frames[f"{d}_walk"].append(img)
                            idx += 1
                        except tk.TclError: break
                    idx = 0
                    while True:
                        try:
                            img = tk.PhotoImage(file=f"image/{prefix}idle_{d}.gif", format=f"gif -index {idx}")
                            self.frames[f"{d}_idle"].append(img)
                            idx += 1
                        except tk.TclError: break

            action_list = ["attack"]
            if self.char_type == "strider": action_list.append("dash")
            if self.char_type == "stranger": action_list.append("cast")
            if self.char_type == "freischutz": action_list = ["skill"]

            for action in action_list:
                for d in ["right", "left"]:
                    idx = 0
                    while True:
                        try:
                            img = tk.PhotoImage(file=f"image/{prefix}{action}_{d}.gif", format=f"gif -index {idx}")
                            self.frames[f"{d}_{action}"].append(img)
                            idx += 1
                        except tk.TclError: break
            
            for d in ["right", "left"]:
                self.jump_imgs[f"{d}_prep"] = tk.PhotoImage(file=f"image/{prefix}jump_prep_{d}.png")
                
                if self.char_type == "strider":
                    self.jump_imgs[f"{d}_rise"] = tk.PhotoImage(file=f"image/{prefix}jump_air_{d}.png")
                    self.jump_imgs[f"{d}_fall"] = tk.PhotoImage(file=f"image/{prefix}jump_land_{d}.png")
                else:
                    self.jump_imgs[f"{d}_rise"] = tk.PhotoImage(file=f"image/{prefix}jump_rise_{d}.png")
                    self.jump_imgs[f"{d}_fall"] = tk.PhotoImage(file=f"image/{prefix}jump_fall_{d}.png")
                
                if self.char_type == "stranger":
                    self.beam_imgs[f"{d}_beam"] = tk.PhotoImage(file=f"image/{prefix}beam_{d}.png")
                
                if self.char_type == "freischutz":
                    self.combo_imgs[f"{d}_1"] = tk.PhotoImage(file=f"image/{prefix}attack1_{d}.png")
                    self.combo_imgs[f"{d}_2"] = tk.PhotoImage(file=f"image/{prefix}attack2_{d}.png")
                    self.combo_imgs[f"{d}_3"] = tk.PhotoImage(file=f"image/{prefix}attack3_{d}.png")

        except Exception as e:
            print(f"이미지 로딩 실패: {e}")
            self.frames = None

        self.current_dir = "right"
        self.current_action = "idle"
        self.frame_index = 0
        self.anim_timer = 0
        
        if self.frames and self.frames["right_idle"]:
            self.body = canvas.create_image(
                x + (self.w/2), y + self.h, 
                image=self.frames["right_idle"][0], anchor="s"
            )
        else:
            self.body = canvas.create_rectangle(x, y, x+self.w, y+self.h, fill="blue")

    @property
    def atk(self): return self.base_atk + self.equip_atk
    @property
    def total_def(self): return self.base_def + self.equip_def

    def update_physics(self, map_data):
        """상태에 따른 중력/이동 잠금, 충돌 처리, 스프라이트 정렬/앵커 반영."""
        gravity_factor = 1.0
        
        if hasattr(self, 'is_dashing') and self.is_dashing:
            gravity_factor = 0.0
            self.dy = 0
            self.dx = 0
        elif self.char_type == "freischutz" and (self.is_attacking or self.is_skilling):
            self.dx = 0
        elif hasattr(self, 'is_floating') and self.is_floating:
            gravity_factor = 0.2
            
        self.dy += (GRAVITY * gravity_factor)
        self.x += self.dx
        self.check_col(map_data, "x")
        self.y += self.dy
        self.check_col(map_data, "y")
        
        item_type = self.canvas.type(self.body)
        if item_type == "image":
            if hasattr(self, 'update_animation'):
                self.update_animation()

            base_x = self.x + (self.w / 2)
            base_y = self.y + self.h
            offset_x = 0

            if self.char_type == "freischutz" and self.is_skilling:
                render_x = self.skill_render_x if self.skill_render_x else base_x
                self.canvas.coords(self.body, render_x, base_y)
                self.canvas.itemconfig(self.body, anchor=self.skill_anchor)
                return
            elif self.char_type == "stranger" and (self.is_firing or self.is_casting):
                if self.current_dir == "right":
                    self.canvas.coords(self.body, self.x, self.y + self.h)
                    self.canvas.itemconfig(self.body, anchor="sw")
                    return
                else:
                    self.canvas.coords(self.body, self.x + self.w, self.y + self.h)
                    self.canvas.itemconfig(self.body, anchor="se")
                    return
            elif hasattr(self, 'is_dashing') and self.is_dashing:
                base_x = self.dash_visual_x

            self.canvas.coords(self.body, base_x + offset_x, base_y)
            self.canvas.itemconfig(self.body, anchor="s")
        else:
            self.canvas.coords(self.body, self.x, self.y, self.x + self.w, self.y + self.h)

    def attack_trigger(self):
        """기본 공격 시작 처리(쿨다운/콤보/사운드 설정)."""
        if self.is_attacking or self.is_casting or self.is_firing or self.is_skilling: return
        self.is_attacking = True
        self.attack_hit_consumed = False
        gi = getattr(self.canvas, "game_instance", None)
        if self.char_type == "strider":
            self.can_dash_cancel = True
            self.canvas.after(500, lambda: setattr(self, 'can_dash_cancel', False))
            if gi: gi.play_sound("strider_attack")
        if self.char_type == "freischutz":
            now = time.time()
            if now - self.last_atk_time > 1.0: self.combo_step = 1
            self.last_atk_time = now
            duration = 250 if self.combo_step < 3 else 300
            self.update_animation()
            self.canvas.after(duration, self.end_attack_freischutz)
            if gi: gi.play_sound("freischutz_attack")
        elif self.char_type == "iron":
            if gi: gi.play_sound("iron_attack")
        elif self.char_type == "stranger":
            if gi: gi.play_sound("stranger_attack")
        else:
            self.frame_index = 0
            self.anim_timer = 0

    def end_attack(self):
        self.is_attacking = False

    def end_attack_freischutz(self):
        self.is_attacking = False
        if self.combo_step == 3:
            self.attack_cooldown = 10
            self.combo_step = 1
        else:
            self.combo_step += 1

    def attack(self):
        self.attack_trigger()

    def plasma_press(self):
        """스트레인져 플라즈마 예열/발사 상태 전환 및 타이머 초기화."""
        if self.must_release_d: return
        if not self.is_attacking and not self.is_dashing:
            self.is_casting = True
            self.is_firing = False
            self.d_press_time = time.time()
            self.fire_start_time = 0.0
            self.plasma_hits = 0
            self.frame_index = 0
            self.anim_timer = 0
            self.plasma_sound_playing = False
            has_cast = False
            if self.frames:
                cast_list = self.frames.get(f"{self.current_dir}_cast")
                has_cast = bool(cast_list)
            if not has_cast:
                self.is_casting = False
                self.is_firing = True
                self.fire_start_time = time.time()
                self.plasma_hits = 0
                gi = getattr(self.canvas, "game_instance", None)
                if gi: gi.play_sound("stranger_plasma", loop=True)
                self.plasma_sound_playing = True

    def stop_plasma(self):
        self.is_casting = False
        self.is_firing = False
        if self.plasma_sound_playing:
            gi = getattr(self.canvas, "game_instance", None)
            if gi: gi.stop_sound("stranger_plasma")
            self.plasma_sound_playing = False
        self.float_dmg_timer = 0
        self.plasma_hits = 0

    def plasma_release(self):
        self.must_release_d = False
        self.stop_plasma()
        self.d_press_time = 0

    def skill_trigger(self):
        if self.char_type != "freischutz": return
        if not self.is_skilling and not self.is_attacking:
            self.is_skilling = True
            self.skill_end_pending = False
            self.skill_hit_targets = set()
            self.skill_render_x = self.x + (self.w / 2)
            self.skill_anchor = "sw" if self.current_dir == "right" else "se"
            self.canvas.coords(self.body, self.skill_render_x, self.y + self.h)
            self.canvas.itemconfig(self.body, anchor=self.skill_anchor)
            self.frame_index = 0
            self.anim_timer = 0
            gi = getattr(self.canvas, "game_instance", None)
            if gi: gi.play_sound("freischutz_skill")
            self.update_animation()

    def finish_skill(self):
        self.is_skilling = False
        self.skill_end_pending = False
        self.skill_hit_targets = set()
        self.frame_index = 0
        self.anim_timer = 0

    def update_plasma(self, monster_list, game_instance):
        """발사 중 주기적(최대 3회) 빔 판정/데미지 적용, 종료 타이밍 관리."""
        if not self.is_firing:
            return
        if self.fire_start_time == 0.0:
            self.fire_start_time = time.time()
        elapsed = time.time() - self.fire_start_time
        if elapsed > 2.0:
            self.stop_plasma()
            self.must_release_d = True
            return
        if self.plasma_hits >= 3:
            return
        if elapsed < self.plasma_hits * 0.9:
            return

        beam_len = STRANGER_BEAM_RANGE
        if self.current_dir == "right":
            bbox = (self.x + self.w, self.y, self.x + self.w + beam_len, self.y + self.h)
        else:
            bbox = (self.x - beam_len, self.y, self.x, self.y + self.h)
        beam_dmg = max(1, int(self.atk * 0.7))
        for m in monster_list[:]:
            mx1, my1, mx2, my2 = game_instance.get_bbox(m)
            if not (bbox[2] < mx1 or bbox[0] > mx2 or bbox[3] < my1 or bbox[1] > my2):
                if hasattr(game_instance, "can_damage_monster") and not game_instance.can_damage_monster(m):
                    continue
                m.hp -= beam_dmg
                try:
                    game_instance.create_damage_text(m.x, m.y, beam_dmg)
                except Exception:
                    pass
                if m.hp <= 0:
                    game_instance.kill_monster(m)
        self.plasma_hits += 1

    def toggle_floating(self, is_active, monster_list):
        if self.char_type != "stranger": return
        if not self.on_ground and self.dy >= 0 and is_active:
            self.is_floating = True
            self.float_dmg_timer += 1
            if self.float_dmg_timer > 30:
                self.float_dmg_timer = 0
                r = STRANGER_CIRCLE_RANGE
                cx, cy = self.x + self.w/2, self.y + self.h/2
                bbox = (cx-r, cy-r, cx+r, cy+r)
                for m in monster_list:
                    mx1, my1, mx2, my2 = self.canvas.game_instance.get_bbox(m)
                    if not (bbox[2] < mx1 or bbox[0] > mx2 or bbox[3] < my1 or bbox[1] > my2):
                        if hasattr(self.canvas.game_instance, "can_damage_monster") and not self.canvas.game_instance.can_damage_monster(m):
                            continue
                        dmg = self.atk * 0.8
                        m.hp -= dmg
                        try:
                            self.canvas.game_instance.create_damage_text(m.x, m.y, int(dmg))
                        except Exception:
                            pass
                        if m.hp <= 0:
                            self.canvas.game_instance.kill_monster(m)
        else:
            self.is_floating = False
            if not is_active:
                self.float_dmg_timer = 0

    def check_freischutz_hit(self, monster_list, is_skill=False):
        atk_range = FREISCHUTZ_ATK_RANGE
        damage = self.atk if not is_skill else self.atk * 1.5
        if self.current_dir == "right":
            atk_box = (self.x + self.w, self.y, self.x + self.w + atk_range, self.y + self.h)
        else:
            atk_box = (self.x - atk_range, self.y, self.x, self.y + self.h)
        hits = []
        for m in monster_list:
            mx1, my1, mx2, my2 = self.canvas.game_instance.get_bbox(m)
            if not (atk_box[2] < mx1 or atk_box[0] > mx2 or atk_box[3] < my1 or atk_box[1] > my2):
                if hasattr(self.canvas.game_instance, "can_damage_monster") and not self.canvas.game_instance.can_damage_monster(m):
                    continue
                if is_skill:
                    mid = id(m)
                    if not hasattr(self, "skill_hit_targets"):
                        self.skill_hit_targets = set()
                    if mid in self.skill_hit_targets:
                        continue
                    self.skill_hit_targets.add(mid)
                if self.current_dir == "right":
                    dist = max(0, mx1 - (self.x + self.w))
                else:
                    dist = max(0, self.x - mx2)
                hits.append((m, dist))
        if not hits:
            return
        if not is_skill:
            if getattr(self, "attack_hit_consumed", False):
                return
            hits = [min(hits, key=lambda x: x[1])]
        for m, _ in hits:
            if hasattr(self.canvas.game_instance, "can_damage_monster") and not self.canvas.game_instance.can_damage_monster(m):
                continue
            m.hp -= damage
            try:
                self.canvas.game_instance.create_damage_text(m.x, m.y, damage)
            except Exception:
                pass
        if not is_skill:
            self.attack_hit_consumed = True

    def take_damage(self, dmg):
        if self.invincible > 0: return
        actual_dmg = max(1, dmg - self.total_def)
        self.hp -= actual_dmg
        self.invincible = 30 
        self.canvas.itemconfig(self.body, state='hidden')
        self.canvas.after(100, lambda: self.canvas.itemconfig(self.body, state='normal'))

    def dash_skill(self, direction, monster_list, map_data=None):
        """스트라이더 대시: 벽 충돌 고려 이동, 즉시 렌더, 경로 내 몬스터 판정."""
        if self.dash_cooldown > 0: return []
        
        self.is_attacking = False
        self.is_dashing = True
        self.frame_index = 0
        self.anim_timer = 0
        gi = getattr(self.canvas, "game_instance", None)
        if gi: gi.play_sound("strider_dash")
        
        dist = STRIDER_DASH_RANGE
        start_x = self.x
        sign = 1 if direction == "right" else -1
        step = TILE_SIZE / 4
        remaining = abs(dist)
        sim_x = self.x
        max_x = MAP_WIDTH - self.w
        while remaining > 0:
            move = min(step, remaining) * sign
            next_x = sim_x + move
            next_x = max(0, min(max_x, next_x))
            if map_data is not None:
                left = int(next_x / TILE_SIZE)
                right = int((next_x + self.w - 0.1) / TILE_SIZE)
                top = int(self.y / TILE_SIZE)
                bottom = int((self.y + self.h - 0.1) / TILE_SIZE)
                if sign > 0:
                    if self.is_wall(map_data, top, right) or self.is_wall(map_data, bottom, right):
                        break
                else:
                    if self.is_wall(map_data, top, left) or self.is_wall(map_data, bottom, left):
                        break
            sim_x = next_x
            remaining -= step
            if next_x == 0 or next_x == max_x:
                break
        self.x = sim_x
        actual_dist = self.x - start_x
        self.dash_visual_x = start_x + (self.w / 2) + (actual_dist / 2)

        self.dx = 0
        self.dy = 0
        self.dash_cooldown = 15 
        
        if self.frames["right_dash"]:
            self.update_animation() 
            self.canvas.coords(self.body, self.dash_visual_x, self.y + self.h)
            self.canvas.itemconfig(self.body, anchor="s")
        
        dead_monsters = []
        dash_box = (min(start_x, self.x), self.y, max(start_x, self.x) + self.w, self.y + self.h)
        for m in monster_list:
            mx1, my1, mx2, my2 = self.canvas.game_instance.get_bbox(m)
            if not (dash_box[2] < mx1 or dash_box[0] > mx2 or dash_box[3] < my1 or dash_box[1] > my2):
                if hasattr(self.canvas.game_instance, "can_damage_monster") and not self.canvas.game_instance.can_damage_monster(m):
                    continue
                damage = (self.atk * 1.5)
                m.hp -= damage
                try:
                    self.canvas.game_instance.create_damage_text(m.x, m.y, int(damage))
                except Exception:
                    pass
                if m.hp <= 0: dead_monsters.append(m)
        
        self.canvas.after(300, lambda: setattr(self, 'is_dashing', False))
        return dead_monsters

    def update_animation(self):
        """상태에 따라 액션 결정 후 프레임/사운드 교체 및 종료 조건 처리."""
        if not self.frames: return
        if self.dash_cooldown > 0: self.dash_cooldown -= 1
        if self.attack_cooldown > 0: self.attack_cooldown -= 1

        if self.dx > 0: self.current_dir = "right"
        elif self.dx < 0: self.current_dir = "left"
        
        next_action = "idle"
        if self.is_dashing: next_action = "dash"
        elif self.is_skilling: next_action = "skill"
        elif self.is_firing: next_action = "cast" 
        elif self.is_casting: next_action = "cast"
        elif self.is_attacking: next_action = "attack"
        elif not self.on_ground: next_action = "jump"
        elif self.dx != 0: next_action = "walk"
        else: next_action = "idle"

        if next_action != self.current_action:
            self.frame_index = 0
            self.anim_timer = 0
            self.current_action = next_action

        final_image = None
        
        if next_action == "jump":
            if self.dy < -5:
                final_image = self.jump_imgs.get(f"{self.current_dir}_prep")
            else:
                if self.char_type == "stranger" and self.is_floating:
                    final_image = self.jump_imgs.get(f"{self.current_dir}_fall")
                else:
                    final_image = self.jump_imgs.get(f"{self.current_dir}_rise")
        
        elif next_action == "cast":
            current_list = self.frames.get(f"{self.current_dir}_cast") if self.frames else None
            if self.is_firing:
                final_image = self.beam_imgs.get(f"{self.current_dir}_beam")
                if not self.plasma_sound_playing:
                    gi = getattr(self.canvas, "game_instance", None)
                    if gi: gi.play_sound("stranger_plasma", loop=True)
                    self.plasma_sound_playing = True
            elif current_list:
                self.anim_timer += 1
                if self.anim_timer > 5:
                    self.frame_index += 1
                    self.anim_timer = 0
                    if self.frame_index >= len(current_list):
                        self.is_casting = False
                        self.is_firing = True
                        self.fire_start_time = time.time()
                        self.frame_index = len(current_list) - 1
                        if not self.plasma_sound_playing:
                            gi = getattr(self.canvas, "game_instance", None)
                            if gi: gi.play_sound("stranger_plasma", loop=True)
                            self.plasma_sound_playing = True
                final_image = current_list[self.frame_index]
            else:
                final_image = self.beam_imgs.get(f"{self.current_dir}_beam")

        elif next_action == "attack" and self.char_type == "freischutz":
            final_image = self.combo_imgs.get(f"{self.current_dir}_{self.combo_step}")

        else:
            current_list = self.frames.get(f"{self.current_dir}_{next_action}")
            if current_list:
                if len(current_list) == 1:
                    final_image = current_list[0]
                else:
                    self.anim_timer += 1
                    
                    threshold = 5
                    max_len = len(current_list) 
                    
                    if next_action == "attack":
                        if self.char_type == "strider":
                            threshold = 5
                            max_len = 2
                        else:
                            threshold = 6
                    elif next_action == "dash": 
                        threshold = 2
                    elif next_action == "skill":
                        threshold = 6
                    
                    if self.anim_timer > threshold:
                        self.frame_index += 1
                        self.anim_timer = 0
                    
                    if self.frame_index >= max_len: 
                        if next_action == "attack": 
                            self.is_attacking = False
                            self.frame_index = 0
                        elif next_action == "dash":
                            self.is_dashing = False
                            self.frame_index = 0
                        elif next_action == "skill":
                            self.frame_index = max_len - 1
                            if not self.skill_end_pending:
                                self.skill_end_pending = True
                                self.canvas.after(120, self.finish_skill)
                        else:
                            self.frame_index = 0
                    
                    safe_index = min(self.frame_index, len(current_list) - 1)
                    final_image = current_list[safe_index]

        gi = getattr(self.canvas, "game_instance", None)
        if self.char_type == "iron":
            if next_action == "walk":
                if not self.walk_sound_playing and gi:
                    gi.play_loop("iron_walk")
                    self.walk_sound_playing = True
            else:
                if self.walk_sound_playing and gi:
                    gi.pause_sound("iron_walk")
                self.walk_sound_playing = False

        if final_image:
            self.canvas.itemconfig(self.body, image=final_image)
