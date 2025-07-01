import pyxel
import random

# --- 定数 ---
# 画面設定
SCREEN_WIDTH = 64
SCREEN_HEIGHT = 16
DIGIT_WIDTH = 8
DIGIT_HEIGHT = 16

# リソースファイル設定
IMG_BANK = 0
IMG_V = 128

# 画像インデックス
IMG_IDX_BLANK = 0
IMG_IDX_NUM_START = 1
IMG_IDX_UFO = 11
IMG_IDX_LIVES_START = 12
IMG_IDX_HYPHEN = 14  # 残機1の画像をハイフンとして利用

# 画面レイアウト
PLAYER_DIGIT_POS = 0
LIVES_DIGIT_POS = 1
INVADER_START_POS = 2
INVADER_COUNT = 6
INVADER_RIGHTMOST_POS = INVADER_START_POS + INVADER_COUNT - 1

# ゲーム状態
STATE_TITLE = 0
STATE_PLAYING = 1
STATE_ROUND_CLEAR = 2
STATE_GAME_OVER = 3
STATE_MISS_PAUSE = 4

# プレイヤーのターゲット定義
TARGET_UFO = 10  # 0-9が数字、10をUFOとする

# スコア設定
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
        self.reset_to_title()
        pyxel.run(self.update, self.draw)

    # --- ゲームの初期化・状態管理 ---
    def reset_to_title(self):
        """ゲーム全体をタイトル画面に戻す"""
        self.game_state = STATE_TITLE

    def start_new_game(self):
        """新しいゲームを開始するための初期化"""
        self.score = 0
        self.lives = 3
        self.round = 0
        self.start_new_round()

    def start_new_round(self):
        """新しいラウンドを開始する"""
        self.round += 1
        self.game_state = STATE_PLAYING
        self.player_target = 0
        self.invader_line = []
        self.line_offset = 0
        self.invaders_spawned_this_round = 0
        self.invaders_to_spawn = 16
        self.destroyed_digit_sum = 0
        self.ufo_pending = False
        self.last_ufo_spawn_sum = 0
        self.invader_spawn_speed = max(15, 45 - self.round * 5)
        self.spawn_timer = 0
        self.miss_pause_timer = 0
        self.round_clear_timer = 0

    # --- メインループ ---
    def update(self):
        """ゲームの状態を更新する（毎フレーム呼ばれる）"""
        state_handlers = {
            STATE_TITLE: self.update_title,
            STATE_PLAYING: self.update_playing,
            STATE_ROUND_CLEAR: self.update_round_clear,
            STATE_GAME_OVER: self.update_game_over,
            STATE_MISS_PAUSE: self.update_miss_pause,
        }
        handler = state_handlers.get(self.game_state)
        if handler:
            handler()

    def draw(self):
        """画面を描画する（毎フレーム呼ばれる）"""
        pyxel.cls(0)
        draw_handlers = {
            STATE_TITLE: self.draw_title,
            STATE_PLAYING: self.draw_playing_ui,
            STATE_ROUND_CLEAR: self.draw_round_clear_ui,
            STATE_GAME_OVER: self.draw_game_over_ui,
            STATE_MISS_PAUSE: self.draw_miss_screen,
        }
        handler = draw_handlers.get(self.game_state)
        if handler:
            handler()

    # --- 各ゲーム状態の更新処理 ---
    def update_title(self):
        """タイトル画面の更新処理"""
        # RETURNキーが押されたらゲーム開始
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.start_new_game()

    def update_playing(self):
        """プレイ中の更新処理"""
        self._handle_player_input()
        self._handle_advance_and_spawn()
        self._check_miss()
        self._check_round_clear()

    def update_round_clear(self):
        """ラウンドクリア画面の更新処理"""
        self.round_clear_timer += 1
        if self.round_clear_timer > 90:  # 3秒経過
            self.start_new_round()

    def update_game_over(self):
        """ゲームオーバー画面の更新処理"""
        # RETURNキーが押されたらタイトルへ
        if pyxel.btnp(pyxel.KEY_RETURN):
            self.reset_to_title()

    def update_miss_pause(self):
        """ミス後のポーズ処理"""
        self.miss_pause_timer += 1
        if self.miss_pause_timer > 60:  # 2秒経過
            self._resume_after_miss()

    # --- ゲームロジックのヘルパー関数 ---
    def _handle_player_input(self):
        """プレイヤーのキー入力を処理する"""
        # 右カーソルキーのみで進める（戻れない）
        if pyxel.btnp(pyxel.KEY_RIGHT):
            self.player_target = (self.player_target + 1) % 11
        if pyxel.btnp(pyxel.KEY_CTRL):
            self._shoot()

    def _handle_advance_and_spawn(self):
        """敵の侵攻と出現を管理する"""
        self.spawn_timer += 1
        if self.spawn_timer < self.invader_spawn_speed:
            return
        self.spawn_timer = 0

        can_spawn_more = self.invaders_spawned_this_round < self.invaders_to_spawn
        line_has_space = len(self.invader_line) < INVADER_COUNT

        if can_spawn_more and line_has_space:
            if self.ufo_pending and not any(
                e["type"] == "ufo" for e in self.invader_line
            ):
                self._spawn_ufo()
                self.ufo_pending = False
            else:
                self._spawn_invader()
        elif self.invader_line:
            self.line_offset += 1

    def _check_miss(self):
        """侵攻されすぎてミスになるかチェックする"""
        if not self.invader_line:
            return

        leftmost_invader_index = len(self.invader_line) - 1
        leftmost_invader_pos = (
            INVADER_RIGHTMOST_POS - leftmost_invader_index - self.line_offset
        )

        if leftmost_invader_pos < INVADER_START_POS:
            self.game_state = STATE_MISS_PAUSE
            self.miss_pause_timer = 0

    def _check_round_clear(self):
        """ラウンドクリア条件をチェックする"""
        if (
            self.invaders_spawned_this_round >= self.invaders_to_spawn
            and not self.invader_line
        ):
            self.game_state = STATE_ROUND_CLEAR
            self.round_clear_timer = 0

    def _resume_after_miss(self):
        """ミスから復帰する"""
        self.lives -= 1
        if self.lives <= 0:
            self.game_state = STATE_GAME_OVER
        else:
            self.player_target = 0
            self.invader_line = []
            self.line_offset = 0
            self.game_state = STATE_PLAYING

    def _shoot(self):
        """弾を発射し、敵を一体破壊する"""
        hit = False
        target_is_ufo = self.player_target == TARGET_UFO

        for i in range(len(self.invader_line) - 1, -1, -1):
            enemy = self.invader_line[i]
            should_destroy = False

            if target_is_ufo and enemy["type"] == "ufo":
                should_destroy = True
                self.score += SCORE_UFO
            elif (
                not target_is_ufo
                and enemy["type"] == "invader"
                and enemy["value"] == self.player_target
            ):
                should_destroy = True
                pos_on_screen = INVADER_RIGHTMOST_POS - i - self.line_offset
                self.score += SCORE_MAP.get(pos_on_screen, 0)
                self.destroyed_digit_sum += enemy["value"]

            if should_destroy:
                hit = True
                self.invader_line.pop(i)
                break

        if (
            hit
            and self.destroyed_digit_sum > 0
            and self.destroyed_digit_sum % 10 == 0
            and self.destroyed_digit_sum > self.last_ufo_spawn_sum
        ):
            self.ufo_pending = True
            self.last_ufo_spawn_sum = self.destroyed_digit_sum

    def _spawn_invader(self):
        """新しいインベーダーを列の右端に追加する"""
        self.invaders_spawned_this_round += 1
        new_invader = {"type": "invader", "value": random.randint(0, 9)}
        self.invader_line.insert(0, new_invader)

    def _spawn_ufo(self):
        """UFOを列の右端に追加する"""
        new_ufo = {"type": "ufo", "value": None}
        self.invader_line.insert(0, new_ufo)

    # --- 描画関連のヘルパー関数 ---
    def draw_title(self):
        """タイトル画面を描画"""
        for i in range(8):
            self._draw_digit(i, IMG_IDX_HYPHEN)

    def draw_playing_ui(self):
        """プレイ中のUIと敵を描画する"""
        if self.player_target == TARGET_UFO:
            self._draw_digit(PLAYER_DIGIT_POS, IMG_IDX_UFO)
        else:
            self._draw_digit(PLAYER_DIGIT_POS, self.player_target + IMG_IDX_NUM_START)

        if self.lives > 0:
            self._draw_digit(LIVES_DIGIT_POS, IMG_IDX_LIVES_START + (3 - self.lives))
        else:
            self._draw_digit(LIVES_DIGIT_POS, IMG_IDX_BLANK)

        for i, enemy in enumerate(self.invader_line):
            pos = INVADER_RIGHTMOST_POS - i - self.line_offset
            if INVADER_START_POS <= pos <= INVADER_RIGHTMOST_POS:
                img_idx = (
                    IMG_IDX_UFO
                    if enemy["type"] == "ufo"
                    else enemy["value"] + IMG_IDX_NUM_START
                )
                self._draw_digit(pos, img_idx)

    def draw_round_clear_ui(self):
        """ラウンドクリア画面を描画"""
        next_round_digit = (self.round + 1) % 10
        self._draw_digit(PLAYER_DIGIT_POS, next_round_digit + IMG_IDX_NUM_START)
        self._draw_digit(LIVES_DIGIT_POS, IMG_IDX_HYPHEN)
        self._draw_score()

    def draw_game_over_ui(self):
        """ゲームオーバー画面を描画"""
        self._draw_round_number()
        self._draw_digit(LIVES_DIGIT_POS, IMG_IDX_BLANK)
        self._draw_score()

    def draw_miss_screen(self):
        """ミス発生時の画面を描画"""
        self._draw_round_number()
        self._draw_digit(LIVES_DIGIT_POS, IMG_IDX_HYPHEN)
        self._draw_score()

    def _draw_round_number(self):
        """現在のラウンド数を描画"""
        round_digit = self.round % 10
        self._draw_digit(PLAYER_DIGIT_POS, round_digit + IMG_IDX_NUM_START)

    def _draw_score(self):
        """スコアを6桁で描画"""
        score_str = f"{self.score:06}"
        for i in range(INVADER_COUNT):
            digit = int(score_str[i])
            pos = INVADER_START_POS + i
            self._draw_digit(pos, digit + IMG_IDX_NUM_START)

    def _draw_digit(self, pos_x_idx, img_idx):
        """指定桁に画像を描画"""
        x = pos_x_idx * DIGIT_WIDTH
        u = img_idx * DIGIT_WIDTH
        pyxel.blt(x, 0, IMG_BANK, u, IMG_V, DIGIT_WIDTH, DIGIT_HEIGHT, 0)


DigitalInvader()
