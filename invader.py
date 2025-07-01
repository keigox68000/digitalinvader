import pyxel
import random

# --- 定数 ---
SCREEN_WIDTH = 64
SCREEN_HEIGHT = 16
DIGIT_WIDTH = 8
DIGIT_HEIGHT = 16

# リソースファイル内の画像位置
IMG_BANK = 0
IMG_V = 128

# 画像インデックス
IMG_IDX_BLANK = 0
IMG_IDX_NUM_START = 1
IMG_IDX_UFO = 11
IMG_IDX_LIVES_START = 12

# 画面上の桁の位置
PLAYER_DIGIT_POS = 0
LIVES_DIGIT_POS = 1
INVADER_START_POS = 2
INVADER_COUNT = 6
# インベーダーの列は画面の右から左へ並ぶ (位置7 -> 位置2)
INVADER_RIGHTMOST_POS = INVADER_START_POS + INVADER_COUNT - 1

# ゲームの状態
STATE_PLAYING = 0
STATE_ROUND_CLEAR = 1
STATE_GAME_OVER = 2

# プレイヤーの狙い (10をUFOとする)
TARGET_UFO = 10

# スコア (キーは画面上の桁位置)
SCORE_MAP = {7: 60, 6: 50, 5: 40, 4: 30, 3: 20, 2: 10}
SCORE_UFO = 300


class DigitalInvader:
    """
    電卓風インベーダーゲーム「デジタルインベーダー」
    """

    def __init__(self):
        pyxel.init(SCREEN_WIDTH, SCREEN_HEIGHT, title="Digital Invader", fps=30)
        try:
            pyxel.load("my_resource.pyxres")
        except Exception as e:
            print(f"エラー: 'my_resource.pyxres'を読み込めませんでした。: {e}")
            pyxel.quit()
            return
        self.reset_game()
        pyxel.run(self.update, self.draw)

    def reset_game(self):
        """ゲーム全体をリセットする"""
        self.score = 0
        self.lives = 3
        self.round = 0
        self.start_new_round()

    def start_new_round(self):
        """新しいラウンドを開始する"""
        self.round += 1
        self.game_state = STATE_PLAYING
        self.player_target = 0  # 0-9: 数字, 10: UFO

        # インベーダーの列を管理するリスト
        self.invader_line = []

        self.invaders_spawned_this_round = 0
        self.invaders_to_spawn = 16
        self.destroyed_digit_sum = 0

        # ラウンドが進むごとに出現スピードを上げる
        self.invader_spawn_speed = max(30, 90 - self.round * 10)
        self.spawn_timer = 0

    def update(self):
        """ゲームの状態を更新する (毎フレーム呼ばれる)"""
        if self.game_state == STATE_PLAYING:
            self.update_playing()
        elif self.game_state == STATE_ROUND_CLEAR:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ENTER):
                self.start_new_round()
        elif self.game_state == STATE_GAME_OVER:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_ENTER):
                self.reset_game()

    def update_playing(self):
        """プレイ中の更新処理"""
        # --- プレイヤーの操作 (0-9の数字 + UFO の11種類) ---
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.player_target = (self.player_target + 1) % 11
        if pyxel.btnp(pyxel.KEY_LEFT):
            self.player_target = (self.player_target - 1 + 11) % 11
        if pyxel.btnp(pyxel.KEY_CTRL):
            self.shoot()

        # --- 敵の出現 ---
        self.spawn_timer += 1
        # インベーダーの列に空きがあり、ラウンドの出現上限に達していなければ出現
        if (
            len(self.invader_line) < INVADER_COUNT
            and self.spawn_timer >= self.invader_spawn_speed
            and self.invaders_spawned_this_round < self.invaders_to_spawn
        ):
            self.spawn_timer = 0
            self.spawn_invader()

        # --- 侵攻によるミス判定 ---
        if len(self.invader_line) >= INVADER_COUNT:
            self.lose_life()

        # --- ラウンドクリア判定 ---
        # ラウンドの敵をすべて出現させ、かつ画面上の敵をすべて倒したらクリア
        if (
            self.invaders_spawned_this_round >= self.invaders_to_spawn
            and not self.invader_line
        ):
            self.game_state = STATE_ROUND_CLEAR

    def shoot(self):
        """プレイヤーが選択した対象を攻撃し、列を詰める"""
        new_line = []
        hit = False
        target_is_ufo = self.player_target == TARGET_UFO

        for i, enemy in enumerate(self.invader_line):
            destroyed = False
            # UFOを狙っている場合
            if target_is_ufo:
                if enemy["type"] == "ufo":
                    destroyed = True
                    self.score += SCORE_UFO
            # 数字を狙っている場合
            else:
                if enemy["type"] == "invader" and enemy["value"] == self.player_target:
                    destroyed = True
                    pos_on_screen = INVADER_RIGHTMOST_POS - i
                    self.score += SCORE_MAP.get(pos_on_screen, 0)
                    self.destroyed_digit_sum += enemy["value"]

            if destroyed:
                hit = True
            else:
                new_line.append(enemy)

        # 列を新しいものに更新（撃破した後退処理）
        self.invader_line = new_line

        # UFO出現判定 (UFOは画面に1体まで)
        if hit and self.destroyed_digit_sum > 0 and self.destroyed_digit_sum % 10 == 0:
            if not any(e["type"] == "ufo" for e in self.invader_line):
                self.spawn_ufo()

    def spawn_invader(self):
        """新しいインベーダーを列の右端に追加する"""
        self.invaders_spawned_this_round += 1
        new_invader = {
            "type": "invader",
            "value": random.randint(0, 9),
        }
        # 右端に追加（リストの先頭に追加して、描画時に右から表示する）
        self.invader_line.insert(0, new_invader)

    def spawn_ufo(self):
        """UFOを列の右端に追加する"""
        new_ufo = {
            "type": "ufo",
            # UFOを倒すのに数字は不要になった
        }
        # 右端に追加（リストの先頭に追加して、描画時に右から表示する）
        self.invader_line.insert(0, new_ufo)

    def lose_life(self):
        """ライフが減る処理"""
        self.lives -= 1
        # 画面上の敵をリセット
        self.invader_line = []
        if self.lives <= 0:
            self.game_state = STATE_GAME_OVER

    def draw(self):
        """画面を描画する"""
        pyxel.cls(0)
        if self.game_state == STATE_GAME_OVER:
            self.draw_text_centered("GAME OVER")
            self.draw_text_centered("PRESS ENTER", 6)
        elif self.game_state == STATE_ROUND_CLEAR:
            self.draw_round_number()
            self.draw_score()
            self.draw_text_centered("PRESS ENTER", 6)
        elif self.game_state == STATE_PLAYING:
            self.draw_playing_ui()
            self.draw_invader_line()

    def draw_playing_ui(self):
        """プレイ中のUIを描画"""
        # プレイヤーの狙う対象を描画
        if self.player_target == TARGET_UFO:
            img_idx = IMG_IDX_UFO
        else:
            img_idx = self.player_target + IMG_IDX_NUM_START
        self.draw_digit(PLAYER_DIGIT_POS, img_idx)

        # 残機
        if self.lives > 0:
            lives_img_idx = IMG_IDX_LIVES_START + (3 - self.lives)
            self.draw_digit(LIVES_DIGIT_POS, lives_img_idx)
        else:
            self.draw_digit(LIVES_DIGIT_POS, IMG_IDX_BLANK)

    def draw_invader_line(self):
        """インベーダーの列を描画"""
        for i, enemy in enumerate(self.invader_line):
            # 画面上の位置を計算（右から詰めて描画）
            pos_on_screen = INVADER_RIGHTMOST_POS - i

            if enemy["type"] == "invader":
                img_idx = enemy["value"] + IMG_IDX_NUM_START
            else:  # ufo
                img_idx = IMG_IDX_UFO
            self.draw_digit(pos_on_screen, img_idx)

    def draw_round_number(self):
        """ラウンド数を描画"""
        round_digit = self.round % 10
        img_idx = round_digit + IMG_IDX_NUM_START
        self.draw_digit(PLAYER_DIGIT_POS, img_idx)

    def draw_score(self):
        """スコアを6桁で描画"""
        score_str = f"{self.score:06}"
        for i in range(INVADER_COUNT):
            digit = int(score_str[i])
            img_idx = digit + IMG_IDX_NUM_START
            self.draw_digit(INVADER_START_POS + i, img_idx)

    def draw_digit(self, pos_x_idx, img_idx):
        """指定桁に画像を描画"""
        screen_x = pos_x_idx * DIGIT_WIDTH
        img_u = img_idx * DIGIT_WIDTH
        pyxel.blt(screen_x, 0, IMG_BANK, img_u, IMG_V, DIGIT_WIDTH, DIGIT_HEIGHT, 0)

    def draw_text_centered(self, text, y_offset=0):
        """画面中央にテキストを描画"""
        text_width = len(text) * pyxel.FONT_WIDTH
        x = (SCREEN_WIDTH - text_width) / 2
        y = (SCREEN_HEIGHT - pyxel.FONT_HEIGHT) / 2 + y_offset
        pyxel.text(x, y, text, 7)


DigitalInvader()
