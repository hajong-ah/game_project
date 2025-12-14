import tkinter as tk
import random
import time
import math
import pygame

from constants import *
from entities import Monster, Player


class AdventureRPGGame:
    """게임 전체를 관리: 스테이지 로딩, 카메라/사운드, 입력, 몬스터·보스·엔딩 흐름."""
    def __init__(self, root):
        self.root = root
        self.root.title("Adventrue RPG Game: 컴퓨터공학부 2025014433 하종아")
        self.center_window(SCREEN_WIDTH, GAME_HEIGHT + UI_HEIGHT)
        self.sounds = {}
        self.sound_channels = {}
        self.bgm_file = BGM_FILE
        try:
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=256)
            pygame.mixer.init()
        except Exception:
            pass
        self.load_sounds()
        
        self.game_cv = tk.Canvas(root, width=SCREEN_WIDTH, height=GAME_HEIGHT, bg="black",
                                 scrollregion=(0, 0, MAP_WIDTH, GAME_HEIGHT))
        self.game_cv.game_instance = self
        self.game_cv.pack()
        self.ui_cv = tk.Canvas(root, width=SCREEN_WIDTH, height=UI_HEIGHT, bg="#222")
        self.ui_cv.pack()
        
        self.player = None
        self.keys = {}
        self.is_paused = False
        self.show_inventory = False
        self.monsters = []
        self.boss_projectiles = []
        self.dropped_items = []
        self.goal_obj = None
        self.chest_opened = False
        self.chests = []
        self.ending_portal = None
        self.final_cutscene_running = False
        try:
            self.chest_img = tk.PhotoImage(file="image/tile_box.png")
        except Exception:
            self.chest_img = None
        self.boss_proj_frames = []
        for i in range(1, 6):
            try:
                self.boss_proj_frames.append(tk.PhotoImage(file=f"image/boss_proj{i}.png"))
            except Exception:
                break
        self.camera_x = 0.0
        self.cam_move_dir = 0
        self.loop_tick = 0
        
        root.bind("<KeyPress>", self.key_down)
        root.bind("<KeyRelease>", self.key_up)
        self.start_game("iron")

    def center_window(self, w, h):
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def load_sounds(self):
        for key, file in SOUND_FILES.items():
            try:
                self.sounds[key] = pygame.mixer.Sound(file)
            except Exception:
                self.sounds[key] = None

    def play_sound(self, key, loop=False):
        snd = self.sounds.get(key)
        if not snd:
            return
        try:
            ch = snd.play(-1 if loop else 0)
            self.sound_channels[key] = ch
        except Exception:
            pass

    def play_loop(self, key):
        snd = self.sounds.get(key)
        if not snd:
            return
        ch = self.sound_channels.get(key)
        try:
            if ch:
                ch.unpause()
            else:
                ch = snd.play(-1)
                self.sound_channels[key] = ch
        except Exception:
            pass

    def pause_sound(self, key):
        ch = self.sound_channels.get(key)
        if ch:
            try:
                ch.pause()
            except Exception:
                pass

    def stop_sound(self, key):
        ch = self.sound_channels.get(key)
        if ch:
            try:
                ch.stop()
            except Exception:
                pass

    def stop_all_sounds(self):
        for ch in self.sound_channels.values():
            try:
                ch.stop()
            except Exception:
                pass
        self.sound_channels = {}

    def play_bgm(self):
        if not self.bgm_file:
            return
        try:
            if pygame.mixer.music.get_busy():
                return
            pygame.mixer.music.load(self.bgm_file)
            pygame.mixer.music.set_volume(0.1)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def stop_bgm(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass

    def start_game(self, char_type):
        self.stop_all_sounds()
        self.game_cv.delete("all")
        self.game_cv.config(bg="skyblue", scrollregion=(0, 0, MAP_WIDTH, GAME_HEIGHT))
        self.camera_x = 0.0
        self.chest_opened = False
        self.chests = []
        self.ending_portal = None
        self.final_cutscene_running = False
        self.tutorial_done = False
        self.help_visible = False
        self.is_paused = False
        self.player = Player(self.game_cv, 100, 100, char_type)
        self.stage_level = -1
        self.load_stage(-1)
        self.play_bgm()
        self.game_loop()

    def load_stage(self, stage_num):
        """스테이지 전환: 맵/몬스터 초기화, 연출 텍스트, 플레이어 리스폰·카메라 설정."""
        self.stage_level = max(-2, min(stage_num, 4))
        self.is_paused = False
        self.game_cv.delete("all")
        self.monsters.clear()
        self.boss_projectiles.clear()
        self.dropped_items.clear()
        self.goal_obj = None
        self.chests = []
        self.ending_portal = None
        self.final_cutscene_running = False
        self.chest_opened = False
        self.tutorial_done = self.tutorial_done if self.stage_level == 0 else True
        if self.stage_level == -2:
            self.awaiting_class = False
            self.class_chosen = False
        else:
            self.awaiting_class = False

        if self.stage_level == -1:
            self.map_data = STAGE_OPEN
            self.log("차원의 코어 붕괴로 왕국이 멸망 위기... 오른쪽 포탈로 이동하세요.")
            self.show_story("배경: 평화롭던 왕국은 세계의 균형을 유지하는 '차원의 코어'에 의해 보호받고 있었습니다.\n사건: 어느 날, 알 수 없는 원인으로 코어가 파괴되면서 시공간에 균열이 발생합니다. 과거에 봉인된 몬스터들이 풀려나고, 왕국은 멸망의 위기에 처합니다.", 0)
        elif self.stage_level == 0:
            self.map_data = STAGE_0
            self.tutorial_timer = 120
            self.tutorial_boss_spawned = False
            self.tutorial_done = False
            self.show_story("상황: 플레이어는 왕국을 지키는 평범한 기사 '아이언나이트'로 시작합니다.\n전개: 쏟아지는 몬스터들에게 맞서지만 역부족입니다. (필패 이벤트: 공격해도 몬스터가 죽지 않음)", 0)
        elif self.stage_level == -2:
            self.map_data = STAGE_HIDDEN
            self.log("조력자의 힘이 깃든 숨겨진 공간. 전직할 캐릭터를 선택하세요.")
            self.class_chosen = False
            self.awaiting_class = False
            self.show_story("사건: 죽음의 문턱에서 신비한 힘을 가진 '조력자'가 나타나 자신의 생명을 희생하여 주인공을 구합니다.\n유언: \"내 수명은 여기까지다... 내 모든 힘과 가능성을 너에게 주마. 부디 이 땅을 지켜다오.\"\n(조력자는 빛이 되어 사라지고, 주인공은 그 힘을 받아들인 채 정신을 잃은 뒤 깨어나 각성합니다.)", 0)
        elif self.stage_level == 1:
            self.map_data = STAGE_1
        elif self.stage_level == 2:
            self.map_data = STAGE_2
        elif self.stage_level == 3:
            self.map_data = STAGE_3
        else:
            self.map_data = STAGE_END
        self.draw_map()
        
        if self.stage_level >= 1 or self.stage_level == -2:
            self.player.hp = self.player.max_hp
            self.player.invincible = 0

        spawn_x = 100
        self.player.x = spawn_x
        self.player.y = self.find_ground_y(spawn_x)
        self.player.dy = 0
        self.player.dx = 0
        self.keys = {}
        self.player.on_ground = True
        
        if self.player.frames and self.player.frames["right_idle"]:
            start_img = self.player.frames["right_idle"][0]
            self.player.body = self.game_cv.create_image(
                self.player.x + (self.player.w/2), 
                self.player.y + self.player.h, 
                image=start_img, anchor="s"
            )
        else:
            self.player.body = self.game_cv.create_rectangle(
                self.player.x, self.player.y, 
                self.player.x+self.player.w, self.player.y+self.player.h, 
                fill="blue"
            )

        self.camera_x = max(0, min(MAP_WIDTH - SCREEN_WIDTH, self.player.x - (SCREEN_WIDTH/2)))
        scroll_den = max(1, MAP_WIDTH - SCREEN_WIDTH)
        self.game_cv.xview_moveto(self.camera_x / scroll_den)

        monster_type = "enemy0" if self.stage_level == 1 else ["enemy1", "enemy2"]
        spawn_count = 0
        if self.stage_level == 0:
            spawn_count = 0
        elif self.stage_level == 1:
            spawn_count = 0
        elif self.stage_level in [1, 2]:
            spawn_count = 0
        elif self.stage_level >= 4 or self.stage_level <= 0:
            spawn_count = 0
        else:
            spawn_count = 5 + (self.stage_level * 2)
        if self.stage_level == 3:
            spawn_count = 3
        
        for _ in range(spawn_count):
            placed = False
            for _ in range(800):
                c = random.randint(1, MAP_COLS-2)
                r = random.randint(1, MAP_ROWS-2)
                if self.map_data[r][c] == 0 and self.map_data[r+1][c] == 1:
                    m_name = monster_type if isinstance(monster_type, str) else random.choice(monster_type)
                    mob = Monster(self.game_cv, c*TILE_SIZE, r*TILE_SIZE, m_name)
                    self.monsters.append(mob)
                    placed = True
                    break
            if not placed:
                self.log("몬스터 스폰 실패: 빈 공간 부족")
                break

        if self.stage_level == 1:
            self.monsters.clear()
            self.spawn_stage1_monsters()
        elif self.stage_level == 2:
            self.monsters.clear()
            self.spawn_stage2_monsters()

        if self.stage_level == 3:
            bx, by = (MAP_COLS//2)*TILE_SIZE, (MAP_ROWS-3)*TILE_SIZE
            boss = Monster(self.game_cv, bx, by, "Boss")
            boss.hp = 1000; boss.max_hp = 1000; boss.data["atk"] = 35
            self.monsters.append(boss)
        
        if self.stage_level in [1, 2, 3]:
            self.log(f"STAGE {stage_num} 시작!")
    def get_bbox(self, obj):
        try:
            bbox = self.game_cv.bbox(obj.body)
            if bbox and len(bbox) == 4:
                return bbox
        except Exception:
            pass
        return (obj.x, obj.y, obj.x + obj.w, obj.y + obj.h)

    def can_damage_monster(self, m):
        return True

    def update_boss_actions(self):
        """보스 투사체 발사 패턴 처리(쿨타임·속도·스프라이트·사운드)."""
        now = time.time()
        for boss in [m for m in self.monsters if getattr(m, "is_boss", False)]:
            if (now - boss.boss_last_shot) >= boss.boss_shot_cd and self.player:
                bx, by = boss.x + boss.w/2, boss.y + boss.h/2
                px, py = self.player.x + self.player.w/2, self.player.y + self.player.h/2
                dx, dy = px - bx, py - by
                dist = math.hypot(dx, dy) or 1
                speed = 14.0
                vx, vy = (dx/dist)*speed, (dy/dist)*speed
                frame_list = self.boss_proj_frames if self.boss_proj_frames else None
                pid = None
                if frame_list:
                    pid = self.game_cv.create_image(bx, by, image=frame_list[0], anchor="center", tags="boss_proj")
                else:
                    pid = self.game_cv.create_oval(bx-10, by-10, bx+10, by+10, fill="orange", tags="boss_proj")
                proj = {"id": pid, "x": bx, "y": by, "vx": vx, "vy": vy,
                        "start": now, "frame_list": frame_list, "frame_idx": 0, "expire": now + 5.0}
                self.boss_projectiles.append(proj)
                boss.boss_last_shot = now
                self.play_sound("boss_projectile")

    def draw_map(self):
        self.chests = []
        story_msgs = {
            1: "깨어나 새로운 힘을 느낀다.\n목표: 왕국 주변을 점거한 슬라임들을 처치하며 잃어버린 감각을 되찾고 코어로 향한다.",
            2: "차원의 균열이 깊다. 더 강한 몬스터가 앞을 막는다.\n조력자의 유언을 되새기며 포기하지 않고 전진하자.",
            3: "코어 직전: 코어 앞을 지키는 최종 보스를 쓰러뜨려라.",
            4: "코어 제어실: 상자를 깨우면 진실이 드러난다.\n(상자 주변에 도달하면 기본 공격(z) 키를 누르세요.)",
        }
        if self.stage_level in story_msgs:
            self.log(story_msgs[self.stage_level])
            if self.stage_level in [1, 2, 3]:
                self.show_story(story_msgs[self.stage_level], y=80)
            else:
                self.show_story(story_msgs[self.stage_level])

        tile_files = {
            -1: "image/tile_open.png",
            -2: "image/tile_hidden.png",
            0: "image/tile_stage0.png",
            1: "image/tile_stage1.png",
            2: "image/tile_stage2.png",
            3: "image/tile_stage3.png",
            4: "image/tile_stage_end.png",
        }
        self.tile_img = None
        tfile = tile_files.get(self.stage_level)
        if tfile:
            try:
                self.tile_img = tk.PhotoImage(file=tfile)
            except Exception:
                self.tile_img = None

        for r in range(MAP_ROWS):
            for c in range(MAP_COLS):
                val = self.map_data[r][c]
                x, y = c*TILE_SIZE, r*TILE_SIZE
                if val == 1:
                    if r < MAP_ROWS-1 and (c == 0 or c == MAP_COLS-1):
                        self.game_cv.create_rectangle(x, y, x+TILE_SIZE, y+TILE_SIZE, fill="skyblue", outline="")
                    elif self.tile_img:
                        self.game_cv.create_image(x, y, image=self.tile_img, anchor="nw")
                    else:
                        color = "#5D4037" if self.stage_level == 1 else "#616161"
                        self.game_cv.create_rectangle(x, y, x+TILE_SIZE, y+TILE_SIZE, fill=color, outline="")
                elif val == 2:
                    if self.chest_img:
                        cid = self.game_cv.create_image(x, y, image=self.chest_img, anchor="nw")
                    else:
                        cid = self.game_cv.create_rectangle(x, y, x+TILE_SIZE, y+TILE_SIZE, fill="goldenrod", outline="saddlebrown", width=3)
                    self.chests.append({"id": cid, "bbox": (x, y, x+TILE_SIZE, y+TILE_SIZE)})

    def update_boss_projectiles(self):
        to_remove = []
        for p in self.boss_projectiles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            if p["frame_list"]:
                elapsed = time.time() - p["start"]
                idx = min(len(p["frame_list"]) - 1, int(elapsed))
                if idx != p["frame_idx"]:
                    p["frame_idx"] = idx
                    self.game_cv.itemconfig(p["id"], image=p["frame_list"][idx])
                self.game_cv.coords(p["id"], p["x"], p["y"])
            else:
                self.game_cv.coords(p["id"], p["x"]-10, p["y"]-10, p["x"]+10, p["y"]+10)
            if self.player:
                px1, py1, px2, py2 = self.player.x, self.player.y, self.player.x + self.player.w, self.player.y + self.player.h
                if not (p["x"] > px2 or p["x"] < px1 or p["y"] > py2 or p["y"] < py1):
                    self.player.take_damage(20)
                    to_remove.append(p)
                    continue
            if p["x"] < 0 or p["x"] > MAP_WIDTH or p["y"] < 0 or p["y"] > GAME_HEIGHT or time.time() > p.get("expire", 0):
                to_remove.append(p)
        for p in to_remove:
            try:
                self.game_cv.delete(p["id"])
            except Exception:
                pass
            if p in self.boss_projectiles:
                self.boss_projectiles.remove(p)
    def key_down(self, e):
        if e.keysym in self.keys and self.keys[e.keysym]:
            return
        if getattr(self, "awaiting_class", False):
            digit = None
            if e.keysym in ["1", "2", "3", "KP_1", "KP_2", "KP_3"]:
                digit = e.keysym[-1] if "KP_" in e.keysym else e.keysym
            elif e.char in ["1", "2", "3"]:
                digit = e.char
            if digit:
                mapping = {"1": "stranger", "2": "strider", "3": "freischutz"}
                self.choose_class(mapping[digit])
            return

        self.keys[e.keysym] = True

        if e.keysym.lower() == "h":
            self.toggle_help()
            return

        if e.keysym == "d" and self.player and self.player.char_type == "stranger":
            self.player.plasma_press()
        if e.keysym == "d" and self.player and self.player.char_type == "freischutz":
            self.player.skill_trigger()

        if self.player and self.player.char_type == "strider":
            if self.player.can_dash_cancel:
                if e.keysym in ["Left", "Right"]:
                    if self.player.last_tap_key and self.player.last_tap_key != e.keysym:
                        self.player.last_tap_key = None
                    curr_time = time.time()
                    if (self.player.last_tap_key == e.keysym and 
                        curr_time - self.player.last_tap_time < 0.3):
                        
                        direction = "right" if e.keysym == "Right" else "left"
                        dead_monsters = self.player.dash_skill(direction, self.monsters, self.map_data)
                        for m in dead_monsters: self.kill_monster(m)
                        self.player.can_dash_cancel = False 
                        self.player.last_tap_key = None 
                    else:
                        self.player.last_tap_key = e.keysym
                        self.player.last_tap_time = curr_time

        if e.keysym == "i": self.toggle_inventory()
        if self.show_inventory and e.char.isdigit():
            self.equip_item(int(e.char) - 1)

    def key_up(self, e):
        self.keys[e.keysym] = False
        if e.keysym == "d" and self.player and self.player.char_type == "stranger":
            self.player.plasma_release()

    def game_loop(self):
        """16ms 주기 메인 루프: 입력 처리, 물리/카메라, 보스/이벤트, 충돌·UI."""
        try:
            if self.player and not self.is_paused:
                if self.stage_level == -1:
                    pass
                elif self.stage_level == -2:
                    if not getattr(self, "class_chosen", False) and not getattr(self, "awaiting_class", False):
                        self.prompt_class_choice()
                elif self.stage_level == 0:
                    if not getattr(self, "tutorial_done", False):
                        if not getattr(self, "tutorial_boss_spawned", False):
                            self.monsters = []
                            for i in range(8):
                                tbx = (MAP_COLS//2 + i - 4)*TILE_SIZE
                                tby = (MAP_ROWS-3)*TILE_SIZE
                                doom = Monster(self.game_cv, tbx, tby, "enemy3")
                                doom.hp = 9999; doom.max_hp = 9999; doom.data["atk"] = 30
                                doom.target_player = True
                                self.monsters.append(doom)
                            self.tutorial_boss_spawned = True
                            self.log("압도적인 적이 나타났다! 필패 이벤트")
                        if self.player.hp <= 10:
                            self.tutorial_done = True
                            self.is_paused = True
                            self.player.hp = 10
                            self.player.invincible = 9999
                            self.monsters.clear()
                            self.root.after(800, lambda: self.load_stage(-2))
                            return
                self.process_input()
                self.player.update_physics(self.map_data)

                px_center = self.player.x + (self.player.w / 2)
                want_left = self.keys.get("Left", False)
                want_right = self.keys.get("Right", False)
                dir_val = -1 if want_left and not want_right else 1 if want_right and not want_left else 0

                if dir_val != 0:
                    at_right_edge = self.camera_x >= (MAP_WIDTH - SCREEN_WIDTH - 1)
                    if dir_val < 0:
                        anchor = 0.68 if at_right_edge else 0.78
                    else:
                        anchor = 0.55
                    target_start = px_center - (SCREEN_WIDTH * anchor)
                    target_start = max(0, min(MAP_WIDTH - SCREEN_WIDTH, target_start))
                else:
                    target_start = self.camera_x

                delta = target_start - self.camera_x
                max_step = MOVE_SPEED * (0.22 if dir_val > 0 else 0.28)
                step = delta * 0.10
                step = max(-max_step, min(max_step, step))

                if dir_val < 0 and 'at_right_edge' in locals() and at_right_edge and delta < 0:
                    self.camera_x = target_start
                elif abs(delta) <= 1.0:
                    self.camera_x = target_start
                else:
                    self.camera_x = self.camera_x + step

                scroll_den = max(1, MAP_WIDTH - SCREEN_WIDTH)
                self.game_cv.xview_moveto(self.camera_x / scroll_den)
                
                if self.player.char_type == "stranger":
                    self.player.update_plasma(self.monsters, self)
                    is_s_pressed = self.keys.get("s", False)
                    self.player.toggle_floating(is_s_pressed, self.monsters)

                if self.player.invincible > 0:
                    self.player.invincible -= 1
                
                for m in self.monsters[:]: 
                    m.update_physics(self.map_data)
                    if m.hp <= 0:
                        self.kill_monster(m) 
                if self.stage_level == 3 and any(getattr(m, "is_boss", False) for m in self.monsters):
                    if self.loop_tick % 3 == 0:
                        self.update_boss_actions()
                        self.update_boss_projectiles()
                    
                self.check_collisions()
                self.check_goal()
                self.update_ui()
                
                if self.player.hp <= 0:
                    self.player.hp = 0
                    if self.stage_level in [1, 2, 3]:
                        msg = "쓰러졌습니다... 잠시 후 이 스테이지에서 재시작합니다."
                        self.log(msg)
                        self.show_story(msg, 12000)
                        self.is_paused = True
                        self.root.after(1200, lambda lvl=self.stage_level: self.load_stage(lvl))
                        return
                    else:
                        self.log("GAME OVER...")
                        self.is_paused = True
            
            if self.is_paused:
                has_popup = bool(self.ui_cv.find_withtag("lvl_popup"))
                if not has_popup and self.player and self.player.hp > 0:
                    self.is_paused = False
            
            self.loop_tick += 1
        except Exception:
            pass
        finally:
            self.root.after(16, self.game_loop)

    def process_input(self):
        self.player.dx = 0
        if self.keys.get("Left"): self.player.dx = -MOVE_SPEED
        if self.keys.get("Right"): self.player.dx = MOVE_SPEED
        if self.keys.get("space") and self.player.on_ground: self.player.dy = JUMP_POWER
        
        if self.keys.get("z"):
            self.player.attack()

    def get_attack_box(self):
        if not self.player:
            return None
        if not (self.player.is_attacking or (self.player.char_type == "freischutz" and self.player.is_skilling)):
            return None
        atk_range = 60
        if self.player.current_dir == "right":
            return (self.player.x + self.player.w, self.player.y, self.player.x + self.player.w + atk_range, self.player.y + self.player.h)
        else:
            return (self.player.x - atk_range, self.player.y, self.player.x, self.player.y + self.player.h)

    def check_collisions(self):
        """플레이어-몬스터 충돌 피해, 기본 공격 타격 판정, 드랍/상자 처리."""
        p_box = (self.player.x, self.player.y, self.player.x + self.player.w, self.player.y + self.player.h)
        if not self.player.is_attacking and not (self.player.char_type == "freischutz" and self.player.is_skilling):
            self.player.attack_hit_consumed = False
        for m in self.monsters:
            mx1, my1, mx2, my2 = self.get_bbox(m)
            if self.overlap(p_box, (mx1, my1, mx2, my2)):
                if not (self.player.char_type == "strider" and getattr(self.player, "is_dashing", False)):
                    self.player.take_damage(m.data["atk"])

        if self.player.char_type in ["iron", "strider"] and self.player.is_attacking:
            if not getattr(self.player, "attack_hit_consumed", False):
                atk_range = STRIDER_ATK_RANGE if self.player.char_type == "strider" else 30
                if self.player.current_dir == "right":
                    atk_box = (self.player.x+self.player.w, self.player.y, self.player.x+self.player.w+atk_range, self.player.y+self.player.h)
                else:
                    atk_box = (self.player.x-atk_range, self.player.y, self.player.x, self.player.y+self.player.h)
                target = None
                best_dist = None
                for m in self.monsters[:]:
                    mx1, my1, mx2, my2 = self.get_bbox(m)
                    if self.overlap(atk_box, (mx1, my1, mx2, my2)):
                        if not self.can_damage_monster(m): 
                            continue
                        if self.player.current_dir == "right":
                            dist = max(0, mx1 - (self.player.x + self.player.w))
                        else:
                            dist = max(0, (self.player.x) - mx2)
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            target = m
                if target:
                    target.hp -= self.player.atk
                    self.create_damage_text(target.x, target.y, self.player.atk)
                    target.x += 20 if self.player.x < target.x else -20
                    if target.hp <= 0: self.kill_monster(target)
                    self.player.attack_hit_consumed = True
        
        if self.player.char_type == "stranger" and self.player.is_attacking:
            if not getattr(self.player, "attack_hit_consumed", False):
                atk_range = STRANGER_ATK_RANGE
                if self.player.current_dir == "right":
                    atk_box = (self.player.x+self.player.w, self.player.y, self.player.x+self.player.w+atk_range, self.player.y+self.player.h)
                else:
                    atk_box = (self.player.x-atk_range, self.player.y, self.player.x, self.player.y+self.player.h)
                target = None
                best_dist = None
                for m in self.monsters[:]:
                    mx1, my1, mx2, my2 = self.get_bbox(m)
                    if self.overlap(atk_box, (mx1, my1, mx2, my2)):
                        if not self.can_damage_monster(m):
                            continue
                        if self.player.current_dir == "right":
                            dist = max(0, mx1 - (self.player.x + self.player.w))
                        else:
                            dist = max(0, (self.player.x) - mx2)
                        if best_dist is None or dist < best_dist:
                            best_dist = dist
                            target = m
                if target:
                    target.hp -= self.player.atk
                    self.create_damage_text(target.x, target.y, self.player.atk)
                    if target.hp <= 0: self.kill_monster(target)
                    self.player.attack_hit_consumed = True
        
        if self.player.char_type == "freischutz":
            if self.player.is_attacking:
                self.player.check_freischutz_hit(self.monsters, is_skill=False)
            if self.player.is_skilling:
                self.player.check_freischutz_hit(self.monsters, is_skill=True)

        if self.stage_level == 4 and not self.chest_opened:
            atk_box = self.get_attack_box()
            if atk_box:
                for chest in self.chests:
                    if self.overlap(atk_box, chest["bbox"]):
                        self.open_final_chest(chest)
                        break

        for item in self.dropped_items[:]:
            ix1, iy1, ix2, iy2 = self.game_cv.coords(item["id"])
            if self.overlap(p_box, (ix1, iy1, ix2, iy2)):
                self.player.inventory.append(item["data"])
                self.game_cv.delete(item["id"])
                self.dropped_items.remove(item)
                self.log(f"{item['data']['name']} 획득!")
                if self.show_inventory: self.draw_inventory()

    def kill_monster(self, monster):
        if monster in self.monsters:
            self.monsters.remove(monster)
            self.game_cv.delete(monster.body)
            if getattr(monster, "is_boss", False):
                for p in list(self.boss_projectiles):
                    try:
                        self.game_cv.delete(p.get("id"))
                    except Exception:
                        pass
                self.boss_projectiles.clear()
            exp = monster.data["exp"]
            self.player.exp += exp
            if self.player.exp >= self.player.max_exp: self.level_up_event()
            if random.random() < 0.3:
                item = random.choice(ITEM_DB)
                drop_y = monster.y + monster.h - 30
                iid = self.game_cv.create_oval(monster.x, drop_y, monster.x+30, drop_y+30, fill=item["color"])
                self.dropped_items.append({"id": iid, "data": item})
    def check_goal(self):
        """포탈 생성/입장, 엔딩 포탈, 전직 포탈 등 스테이지 이동 트리거 처리."""
        if self.stage_level >= 4 or self.stage_level == 0:
            if self.stage_level == 4 and self.ending_portal and not self.final_cutscene_running:
                portals = self.game_cv.find_withtag("ending_portal")
                if portals:
                    coords = self.game_cv.coords(portals[0])
                    if len(coords) >= 4:
                        cx = (coords[0] + coords[2]) / 2
                        cy = (coords[1] + coords[3]) / 2
                        px_cx = self.player.x + (self.player.w / 2)
                        py_cy = self.player.y + (self.player.h / 2)
                        if abs(px_cx - cx) < 60 and abs(py_cy - cy) < 80:
                            if self.keys.get("Up"):
                                self.play_final_cutscene()
            return

        if self.stage_level == -2 and getattr(self, "class_chosen", False) and not self.goal_obj:
            self.spawn_hidden_portal()

        if self.stage_level == -1 and not self.goal_obj:
            gx = (MAP_COLS-3) * TILE_SIZE
            gy = (MAP_ROWS-1) * TILE_SIZE - 90
            self.game_cv.create_oval(gx, gy, gx+60, gy+90, fill="skyblue", outline="white", width=3, tags="portal")
            self.goal_obj = self.game_cv.create_text(gx+30, gy-20, text="▲", font=("Arial", 20, "bold"), fill="white", tags="portal")
            self.log("오프닝: 오른쪽 포탈로 이동해 이야기를 시작하세요. [↑]")

        if self.stage_level >= 0 and not self.monsters and not self.goal_obj:
            gx = (MAP_COLS-3) * TILE_SIZE
            gy = (MAP_ROWS-1) * TILE_SIZE - 90
            self.game_cv.create_oval(gx, gy, gx+60, gy+90, fill="purple", outline="white", width=3, tags="portal")
            self.goal_obj = self.game_cv.create_text(gx+30, gy-20, text="▲", font=("Arial", 20, "bold"), fill="white", tags="portal")
            if self.stage_level < 3:
                self.log("포탈이 열렸습니다! [↑]키로 이동하세요.")
            else:
                msg = "보스를 처치했습니다! 포탈로 이동하세요. [↑]"
                self.log(msg)
                self.show_story("오른쪽 포탈을 타고 코어 제어실로 이동해 주세요", 12000)

        if self.goal_obj and self.goal_obj != "cleared":
            gx, gy = self.game_cv.coords(self.goal_obj)
            px_cx = self.player.x + (self.player.w / 2)
            py_cy = self.player.y + (self.player.h / 2)
            if abs(px_cx - gx) < 40 and abs(py_cy - (gy+40)) < 60:
                if self.keys.get("Up"):
                    if self.stage_level == -1:
                        self.load_stage(0)
                    elif self.stage_level == -2:
                        self.load_stage(1)
                    elif self.stage_level < 3:
                        self.load_stage(self.stage_level + 1)
                    elif self.stage_level == 3:
                        self.load_stage(4)

    def level_up_event(self):
        """레벨업 처리: 스탯 초기화, 중앙 팝업 UI 띄우고 선택 기다림."""
        self.is_paused = True
        self.player.level += 1
        self.player.exp = 0
        self.player.max_exp = int(self.player.max_exp * 1.2)
        self.game_cv.delete("lvl_popup")
        cx, cy = self.camera_x + SCREEN_WIDTH/2, GAME_HEIGHT/2
        self.game_cv.create_rectangle(cx-200, cy-100, cx+200, cy+80, fill="black", outline="gold", width=3, tags="lvl_popup")
        self.game_cv.create_text(cx, cy-60, text="LEVEL UP!", fill="gold", font=("Arial", 24), tags="lvl_popup")
        self.game_cv.create_rectangle(cx-150, cy-20, cx-20, cy+30, fill="red", tags=("lvl_popup", "btn_atk"))
        self.game_cv.create_text(cx-85, cy+5, text="ATK +5", fill="white", tags=("lvl_popup", "btn_atk"))
        self.game_cv.create_rectangle(cx+20, cy-20, cx+150, cy+30, fill="blue", tags=("lvl_popup", "btn_def"))
        self.game_cv.create_text(cx+85, cy+5, text="DEF +2", fill="white", tags=("lvl_popup", "btn_def"))
        self.game_cv.tag_bind("btn_atk", "<Button-1>", lambda e: self.choose_stat("atk"))
        self.game_cv.tag_bind("btn_def", "<Button-1>", lambda e: self.choose_stat("def"))

    def choose_stat(self, stat):
        if stat == "atk": self.player.base_atk += 5
        else: self.player.base_def += 2
        self.game_cv.delete("lvl_popup")
        self.player.hp = self.player.max_hp
        self.is_paused = False

    def prompt_class_choice(self):
        self.awaiting_class = True
        self.game_cv.delete("class_ui")
        cx, cy = self.camera_x + SCREEN_WIDTH/2, GAME_HEIGHT/2
        self.game_cv.create_rectangle(cx-360, cy-100, cx+360, cy+80, fill="black", outline="gold", width=3, tags="class_ui")
        self.game_cv.create_text(cx, cy-60, text="전직을 선택하세요 (숫자 키)", fill="gold", font=("Arial", 18), tags="class_ui")
        self.game_cv.create_text(cx, cy-30, text="[1] 스트레인져(마법사): 차원의 틈에서 흘러나온 마력을 다루는 마법사", fill="cyan", font=("Arial", 16), tags="class_ui")
        self.game_cv.create_text(cx, cy, text="[2] 스트라이더(메카닉): 미래의 기술과 기동성을 가진 로봇", fill="violet", font=("Arial", 16), tags="class_ui")
        self.game_cv.create_text(cx, cy+30, text="[3] 프라이슈츠(저격수): 원거리에서 총으로 적을 제압하는 사냥꾼", fill="orange", font=("Arial", 16), tags="class_ui")

    def choose_class(self, char_type):
        if self.player and hasattr(self.player, "body"):
            self.game_cv.delete(self.player.body)
        self.player = Player(self.game_cv, self.player.x, self.player.y, char_type)
        self.class_chosen = True
        self.awaiting_class = False
        self.game_cv.delete("class_ui")
        self.log(f"{char_type} 전직 완료! 슬라임을 처치하며 힘을 익히세요.")
        if self.stage_level == -2:
            self.spawn_hidden_portal()

    def toggle_help(self):
        if getattr(self, "help_visible", False):
            self.game_cv.delete("help_overlay")
            self.help_visible = False
            return
        self.help_visible = True
        cx, cy = self.camera_x + SCREEN_WIDTH/2, GAME_HEIGHT/2
        self.game_cv.create_rectangle(cx-360, cy-180, cx+360, cy+180, fill="black", outline="white", width=2, tags="help_overlay")
        lines = [
            "조작법 안내",
            "기본: 이동(방향키) / 점프(스페이스) / 공격(Z키) / 스킬(D키) / 인벤토리(I키)",
            "스트레인져(마법사): 점프 하강 중 로 부유(S키), 플라즈마 발사(D키 꾹)",
            "스트라이더(메카닉): 대시 공격(Z 공격 후 바로 좌 혹은 우 더블탭)\n *더블탭: (<- <- or -> -> 빠르게 연타))",
            "프라이슈츠(저격수): 스킬(D키), 콤보(Z키 연타)",
            "아이템: 빨간색(회복 물약), 청록색(강철 검), 은색(낡은 검), 갈색(나무 방패)"
        ]
        for i, t in enumerate(lines):
            self.game_cv.create_text(cx, cy-120 + i*40, text=t, fill="yellow" if i==0 else "white",
                                     font=("Arial", 16 if i==0 else 14), tags="help_overlay", width=700)

    def spawn_hidden_portal(self):
        if self.goal_obj:
            return
        gx = (MAP_COLS-3) * TILE_SIZE
        gy = (MAP_ROWS-1) * TILE_SIZE - 90
        self.game_cv.create_oval(gx, gy, gx+60, gy+90, fill="purple", outline="white", width=3, tags="portal")
        self.goal_obj = self.game_cv.create_text(gx+30, gy-20, text="▲", font=("Arial", 20, "bold"), fill="white", tags="portal")
        self.log("포탈이 열렸습니다! [↑]키로 이동하세요.")

    def spawn_stage1_monsters(self):
        """스테이지1: 플랫폼 폭별 고정 수량, 바닥 랜덤 스폰 구현."""
        width_to_count = {3: 1, 4: 2, 5: 3, 6: 4, 9: 7}
        spawned = 0
        for r in range(1, MAP_ROWS-1):
            row = self.map_data[r]
            c = 0
            while c < MAP_COLS:
                if row[c] == 1:
                    start = c
                    while c < MAP_COLS and row[c] == 1:
                        c += 1
                    width = c - start
                    if width in width_to_count:
                        count = width_to_count[width]
                        for i in range(count):
                            pos = start + (width / (count + 1)) * (i + 1)
                            x = pos * TILE_SIZE
                            y = (r - 1) * TILE_SIZE
                            m = Monster(self.game_cv, x, y, "enemy0")
                            m.left_bound = start * TILE_SIZE
                            m.right_bound = (start + width) * TILE_SIZE
                            self.monsters.append(m)
                            spawned += 1
                else:
                    c += 1
        ground_row = MAP_ROWS - 2
        ground_spawn = 5
        attempts = 0
        while ground_spawn > 0 and attempts < 400:
            attempts += 1
            c = random.randint(1, MAP_COLS-2)
            if self.map_data[ground_row][c] == 0 and self.map_data[ground_row+1][c] == 1:
                m = Monster(self.game_cv, c * TILE_SIZE, ground_row * TILE_SIZE, "enemy0")
                self.monsters.append(m)
                ground_spawn -= 1

    def spawn_stage2_monsters(self):
        """스테이지2: 행·폭 규칙 기반 플랫폼 스폰, 바닥 좌/우 구간별 랜덤 스폰."""
        config = [
            (2, 5, 3),
            (3, 4, 2),
            (4, 3, 1),
            (7, 4, 2),
            (8, 3, 1),
        ]
        for r_idx, target_w, count in config:
            if r_idx < 0 or r_idx >= MAP_ROWS-1:
                continue
            row = self.map_data[r_idx]
            c = 0
            while c < MAP_COLS:
                if row[c] == 1:
                    start = c
                    while c < MAP_COLS and row[c] == 1:
                        c += 1
                    width = c - start
                    if width == target_w:
                        for i in range(count):
                            pos = start + (width / (count + 1)) * (i + 1)
                            x = pos * TILE_SIZE
                            y = (r_idx - 1) * TILE_SIZE
                            mtype = random.choice(["enemy1", "enemy2"])
                            m = Monster(self.game_cv, x, y, mtype)
                            m.left_bound = start * TILE_SIZE
                            m.right_bound = (start + width) * TILE_SIZE
                            self.monsters.append(m)
                else:
                    c += 1
        ground_row = MAP_ROWS - 2
        def spawn_ground(side, target_count):
            attempts = 0
            while target_count > 0 and attempts < 500:
                attempts += 1
                if side == "left":
                    col = random.randint(1, 21)
                else:
                    col = random.randint(23, MAP_COLS-2)
                if self.map_data[ground_row][col] == 0 and self.map_data[ground_row+1][col] == 1:
                    mtype = random.choice(["enemy1", "enemy2"])
                    m = Monster(self.game_cv, col * TILE_SIZE, ground_row * TILE_SIZE, mtype)
                    self.monsters.append(m)
                    target_count -= 1
        spawn_ground("left", 7)
        spawn_ground("right", 4)

    def find_ground_y(self, x_pos):
        c = int(max(0, min(MAP_COLS-1, x_pos / TILE_SIZE)))
        for r in range(MAP_ROWS-2, -1, -1):
            if self.map_data[r][c] == 0 and self.map_data[r+1][c] == 1:
                return (r+1) * TILE_SIZE - self.player.h
        return (MAP_ROWS-1) * TILE_SIZE - self.player.h

    def toggle_inventory(self):
        self.show_inventory = not self.show_inventory
        if self.show_inventory: self.draw_inventory()
        else: self.game_cv.delete("inv_ui")

    def draw_inventory(self):
        self.game_cv.delete("inv_ui")
        cx = self.camera_x + SCREEN_WIDTH/2
        x1, y1, x2, y2 = cx-200, 100, cx+200, 600
        self.game_cv.create_rectangle(x1, y1, x2, y2, fill="#333", outline="white", tags="inv_ui")
        self.game_cv.create_text(cx, 130, text="INVENTORY", fill="white", font=("Arial", 20), tags="inv_ui")
        for i, item in enumerate(self.player.inventory):
            y_pos = 180 + (i * 40)
            mark = "[E]" if item in self.player.equipped.values() else ""
            text = f"{i+1}. {item['name']} {mark} (Val: {item['val']})"
            self.game_cv.create_text(x1+50, y_pos, text=text, fill=item["color"], anchor="w", font=("Arial", 14), tags="inv_ui")

    def equip_item(self, idx):
        if 0 <= idx < len(self.player.inventory):
            item = self.player.inventory[idx]
            if item["type"] == 0:
                self.player.hp = min(self.player.max_hp, self.player.hp + item["val"])
                self.player.inventory.pop(idx)
            elif item["type"] == 1:
                self.player.equipped["weapon"] = item
                self.player.equip_atk = item["val"]
            elif item["type"] == 2:
                self.player.equipped["armor"] = item
                self.player.equip_def = item["val"]
            self.draw_inventory()

    def update_ui(self):
        self.ui_cv.delete("ui")
        self.ui_cv.create_text(50, 40, text="HP", fill="red", font=("Arial", 16), tags="ui")
        self.ui_cv.create_rectangle(100, 25, 400, 55, fill="gray", tags="ui")
        hp_r = max(0, self.player.hp / self.player.max_hp)
        self.ui_cv.create_rectangle(100, 25, 100 + (300*hp_r), 55, fill="red", tags="ui")
        self.ui_cv.create_text(250, 40, text=f"{int(self.player.hp)}/{self.player.max_hp}", fill="white", tags="ui")
        
        self.ui_cv.create_text(50, 80, text="EXP", fill="yellow", font=("Arial", 16), tags="ui")
        self.ui_cv.create_rectangle(100, 65, 400, 95, fill="gray", tags="ui")
        exp_r = self.player.exp / self.player.max_exp
        self.ui_cv.create_rectangle(100, 65, 100 + (300*exp_r), 95, fill="yellow", tags="ui")
        
        info = f"Lv.{self.player.level}  ATK: {self.player.atk}  DEF: {self.player.total_def}"
        self.ui_cv.create_text(700, 60, text=info, fill="white", font=("Arial", 20), tags="ui")
        self.ui_cv.create_text(SCREEN_WIDTH - 120, 120, text="도움말: H 키", fill="white", font=("Arial", 14), tags="ui")

        if hasattr(self, 'msg_log'):
            self.ui_cv.create_text(SCREEN_WIDTH/2, 140, text=self.msg_log, fill="white", font=("Arial", 14), tags="ui")

    def open_final_chest(self, chest):
        if self.chest_opened:
            return
        self.chest_opened = True
        try:
            self.game_cv.itemconfig(chest["id"], outline="yellow")
        except Exception:
            pass
        self.game_cv.delete("story_msg")
        self.game_cv.create_text(SCREEN_WIDTH/2, 80, text="상자에는 낡은 거울만이 들어있다.", fill="yellow", font=("Arial", 18, "bold"), tags="ending_msg")
        self.game_cv.create_text(SCREEN_WIDTH/2, 120, text="반전: 그 순간, 주인공은 깨닫습니다. 외부의 도구가 필요한 것이 아니라,\n'조력자의 힘을 이어받아 시련을 극복해낸 자신' 자체가 부서진 차원을 메울 유일한 열쇠임을 알게 됩니다.", fill="white", font=("Arial", 16), tags="ending_msg")
        self.log("스스로가 열쇠임을 깨달았다. 빛 속으로 걸어간다.")
        cx = (chest["bbox"][0] + chest["bbox"][2]) / 2
        gy = (MAP_ROWS-1) * TILE_SIZE - 90
        self.game_cv.create_oval(cx-30, gy, cx+30, gy+90, fill="white", outline="gray", width=3, tags="ending_portal")
        self.game_cv.create_text(cx, gy-20, text="▲", font=("Arial", 20, "bold"), fill="black", tags="ending_portal")
        self.ending_portal = "ready"

    def play_final_cutscene(self):
        if self.final_cutscene_running:
            return
        self.final_cutscene_running = True
        self.is_paused = True
        self.stop_bgm()
        curr_img = None
        try:
            if self.game_cv.type(self.player.body) == "image":
                curr_img = self.game_cv.itemcget(self.player.body, "image")
        except Exception:
            pass
        self.game_cv.delete("all")
        self.game_cv.config(bg="white")
        cx, cy = self.camera_x + SCREEN_WIDTH/2, GAME_HEIGHT/2
        self.player.x, self.player.y = cx - self.player.w/2, cy - self.player.h
        if curr_img:
            self.player.body = self.game_cv.create_image(cx, cy, image=curr_img, anchor="s")
        else:
            self.player.body = self.game_cv.create_rectangle(self.player.x, self.player.y, self.player.x+self.player.w, self.player.y+self.player.h, fill="blue")
        text = ("엔딩: 주인공은 망설임 없이 빛이 쏟아지는 코어 속으로 걸어 들어갑니다.\n"
                "\"나의 여정은 여기서 끝나지만, 이 세계의 평화는 영원할 것이다.\"\n"
                "결말: 주인공은 스스로 열쇠가 되어 차원의 틈을 막고, 세계는 다시 평화를 되찾습니다.")
        self.game_cv.create_text(cx, cy - 120, text=text, fill="black", font=("Arial", 16, "bold"), width=SCREEN_WIDTH*0.8)
        self.root.after(10000, self.root.destroy)

    def log(self, text): self.msg_log = text

    def show_story(self, text, duration_ms=8000, y=120):
        self.game_cv.delete("story_msg")
        cx, cy = self.camera_x + SCREEN_WIDTH/2, y
        self.game_cv.create_text(cx, cy, text=text, fill="white", font=("Arial", 16), tags="story_msg", width=SCREEN_WIDTH*0.9)
        if duration_ms > 0:
            self.game_cv.after(duration_ms, lambda: self.game_cv.delete("story_msg"))
    
    def create_damage_text(self, x, y, dmg):
        t = self.game_cv.create_text(x, y-40, text=str(int(dmg)), fill="red", font=("Arial", 20, "bold"))
        self.game_cv.after(500, lambda: self.game_cv.delete(t))

    def overlap(self, box1, box2):
        return not (box1[2] < box2[0] or box1[0] > box2[2] or box1[3] < box2[1] or box1[1] > box2[3])
