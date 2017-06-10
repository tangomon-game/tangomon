#!/usr/bin/env python

# Copyright (C) 2017 Julie Marchant <onpon4@riseup.net>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

__version__ = "1.0"

import argparse
import datetime
import gettext
import json
import math
import os
import random
import time
import warnings
import webbrowser

import sge
import six
import xsge_gui
import xsge_physics
import xsge_tmx


DATA = os.path.join(os.path.dirname(__file__), "data")
CONFIG = os.path.join(os.path.expanduser("~"), ".config", "tangomon")

if six.PY2:
    gettext.install(
        "tangomon", os.path.abspath(os.path.join(DATA, "locale")),
        unicode=True)
else:
    gettext.install("tangomon",
                    os.path.abspath(os.path.join(DATA, "locale")))

parser = argparse.ArgumentParser(prog="Tangomon")
parser.add_argument(
    "--version", action="version", version="%(prog)s " + __version__,
    help=_("Output version information and exit."))
parser.add_argument(
    "-l", "--lang",
    help=_("Manually choose a different language to use."))
parser.add_argument(
    "--nodelta",
    help=_("Disable delta timing. Causes the game to slow down when it can't run at full speed instead of becoming choppier."),
    action="store_true")
parser.add_argument(
    "-d", "--datadir",
    help=_('Where to load the game data from (Default: "{}")').format(DATA))
args = parser.parse_args()

DELTA = not args.nodelta
if args.datadir:
    DATA = args.datadir

if six.PY2:
    gettext.install(
        "tangomon", os.path.abspath(os.path.join(DATA, "locale")),
        unicode=True)
else:
    gettext.install("tangomon",
                    os.path.abspath(os.path.join(DATA, "locale")))

if args.lang:
    lang = gettext.translation("tangomon",
                               os.path.abspath(os.path.join(DATA, "locale")),
                               [args.lang])
    if six.PY2:
        lang.install(unicode=True)
    else:
        lang.install()

SCREEN_SIZE = [640, 480]
TILE_SIZE = 16
FPS = 60
DELTA_MIN = FPS / 10
DELTA_MAX = FPS * 4

KEY_REPEAT_INTERVAL = 20
KEY_REPEAT_DELAY = 400

SAVE_NSLOTS = 5

TEXT_SPEED = 1000
TANGOJI_LIST_SIZE = 10

TANGOJI_MIN = 3

FOREST_LEVEL_DEPTH = 3
DUNGEON_LEVEL_DEPTH = 5

HEALTH_MAX_START = 100
BASE_POWER_START = 10
INCREMENT_FACTOR = 1.1

ATTACK_INTERVAL_TIME = 4 * FPS
ATTACK_INTERVAL_FAIL_TIME = 8 * FPS
TANGOJI_ENTRY_TIME = 30 * FPS
TANGOJI_MULT_START = 1.25
TANGOJI_MULT_DECREMENT = 0.025
TANGOJI_MULT_MIN = 0.25
TANGOJI_MULT_PERSISTENT_MIN = 0.75
TANGOJI_MULT_TIME_BONUS = 0.5 / TANGOJI_ENTRY_TIME

PLAYER_SPEED = 1
PLAYER_ENCOUNTER_CHANCE = 0.01

PLAYER_BBOX_X = 3
PLAYER_BBOX_Y = 7
PLAYER_BBOX_WIDTH = 10
PLAYER_BBOX_HEIGHT = 10

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
MONTH = 30 * DAY
TANGOKAN_WAIT_TIME = DAY
TANGOJECT_TIMES = [2 * DAY, 7 * DAY, 21 * DAY, 2 * MONTH, 6 * MONTH, 18 * MONTH]

first_run = True

font_name = "Droid Sans"
fullscreen = False
scale_method = None
sound_enabled = True
music_enabled = True
fps_enabled = False
save_slots = [None for i in six.moves.range(SAVE_NSLOTS)]

font = None
font_small = None
font_big = None
loaded_music = {}
grassland_tangomon = set()
forest_tangomon = set()
dungeon_tangomon = set()

current_save_slot = None

player_name = None
player_character = 0
player_map = None
player_dest = None
player_x = None
player_y = None
player_tangojis = []
player_tangokans = []
player_tangomon = []
player_tangojections = []
grassland_tangomon_encountered = []
forest_tangomon_encountered = []
dungeon_tangomon_encountered = []


class Game(sge.dsp.Game):

    fps_time = 0
    fps_frames = 0
    fps_text = ""

    def event_step(self, time_passed, delta_mult):
        if fps_enabled:
            self.fps_time += time_passed
            self.fps_frames += 1
            if self.fps_time >= 250:
                self.fps_text = str(round(
                    (1000 * self.fps_frames) / self.fps_time, 2))
                self.fps_time = 0
                self.fps_frames = 0

            self.project_text(font_small, self.fps_text, self.width - 8,
                              self.height - 8, z=1000,
                              color=sge.gfx.Color("yellow"), halign="right",
                              valign="bottom")

    def event_mouse_button_press(self, button):
        if button == "middle":
            self.event_close()

    def event_close(self):
        if isinstance(self.current_room, Arena):
            self.current_room.event_key_press(sge.s.escape, "")
        else:
            save_game()
            self.end()

    def event_paused_close(self):
        self.event_close()


class Room(sge.dsp.Room):

    """Base room class"""

    fname = None

    def __init__(self, music=None, **kwargs):
        self.music = music
        super(Room, self).__init__(**kwargs)

    def event_room_start(self):
        self.add(gui_handler)
        play_music(self.music)

    def event_room_resume(self):
        play_music(self.music)


class TitleScreen(Room):

    """Title screen."""

    menu = None

    def event_room_start(self):
        global first_run

        super(TitleScreen, self).event_room_start()

        if first_run:
            FontChooser(gui_handler).show()
            first_run = False
            write_to_disk()

        self.menu = MainMenu.create()

    def event_room_resume(self):
        super(TitleScreen, self).event_room_resume()

        if self.menu not in gui_handler.windows:
            self.menu = MainMenu.create()


class CharacterChooser(sge.dsp.Room):

    """Character selection screen."""

    def set_sprite(self):
        self.character_obj.sprite = character_down_sprites[player_character]
        self.character_obj.image_fps = None

    def event_room_start(self):
        padding = 8
        text = _("Please use the left and right arrow keys to select your character. When you are finished, press the Enter key.")
        text_sprite = sge.gfx.Sprite.from_text(
            font, text, width=self.width - 2 * padding, halign=sge.s.center)
        text_obj = sge.dsp.Object.create(self.width / 2, padding,
                                         sprite=text_sprite)

        y = text_sprite.height + 2 * padding
        target_w = self.width - 2 * padding
        target_h = self.height - text_sprite.height - 3 * padding
        s = character_down_sprites[player_character]
        scale = min(target_w / s.width, target_h / s.height)
        x = self.width / 2 - scale * s.width / 2
        self.character_obj = sge.dsp.Object.create(x, y, image_xscale=scale,
                                                   image_yscale=scale)
        self.set_sprite()

    def event_key_press(self, key, char):
        global player_character

        if key == sge.s.left:
            play_sound(select_sound)
            player_character -= 1
            player_character %= len(character_down_sprites)
            self.set_sprite()
        elif key == sge.s.right:
            play_sound(select_sound)
            player_character += 1
            player_character %= len(character_down_sprites)
            self.set_sprite()
        elif key in {sge.s.enter, sge.s.kp_enter}:
            play_sound(confirm_sound)
            load_map()


class Worldmap(Room):

    """Overworld maps"""

    def event_key_press(self, key, char):
        if key in {sge.s.escape, sge.s.enter, sge.s.tab}:
            WorldmapMenu.create()


class Arena(Room):

    """Arena where monsters fight."""

    def __init__(self, enemy, **kwargs):
        self.player = random.randrange(len(player_tangomon))
        self.enemy = enemy
        self.tangoji = None
        self.tangoji_bonus = 0
        self.callback = None
        super(Arena, self).__init__(**kwargs)

    def event_room_start(self):
        global player_tangomon
        global player_tangojections

        super(Arena, self).event_room_start()
        self.add(gui_handler)

        self.player_tangomon = player_tangomon[:]

        padding = 8
        w = sge.game.width
        h = 2 * padding + xsge_gui.textbox_sprite.height
        self.window = xsge_gui.Window(
            gui_handler, 0, sge.game.height - h, w, h, border=False)

        self.textbox = xsge_gui.TextBox(
            self.window, padding, padding, 0, width=(w - 2 * padding))

        self.window.keyboard_focused_widget = self.textbox

        self.real_height = sge.game.height - self.window.height

        self.notification_text = ""

        hps = [get_tangomon_hp_max(s) for s in player_tangomon]
        powers = [get_tangomon_base_power(s) for s in player_tangomon]

        self.pt_name = player_tangomon.pop(self.player)
        self.player_name = get_tangomon_name(self.pt_name)
        self.player_hp = get_tangomon_hp_max(self.pt_name)
        self.player_base_power = get_tangomon_base_power(self.pt_name)
        player_sprite = get_tangomon_sprite(self.pt_name)
        y = self.real_height / 2 - player_sprite.height / 2
        self.player_object = sge.dsp.Object.create(
            padding, y, sprite=player_sprite, tangible=False)
        self.enemy_name = get_tangomon_name(self.enemy)
        self.enemy_hp = get_tangomon_hp_max(self.enemy)
        self.enemy_base_power = get_tangomon_base_power(self.enemy)
        enemy_sprite = get_tangomon_sprite(self.enemy).copy()
        enemy_sprite.mirror()
        x = self.width - padding - enemy_sprite.width
        y = self.real_height / 2 - enemy_sprite.height / 2
        self.enemy_object = sge.dsp.Object.create(x, y, sprite=enemy_sprite,
                                                  tangible=False)

        # Peer buff for player's weak tangomon
        avg_hp = int(sum(hps) / len(hps))
        avg_power = int(sum(powers) / len(powers))
        self.player_hp = max(self.player_hp, avg_hp)
        self.player_base_power = max(self.player_base_power, avg_power)

        player_tangojections.sort(key=lambda d: d.get("time"))
        if (player_tangojections and
                player_tangojections[0].get("time", time.time()) <= time.time()):
            self.tangoji = player_tangojections.pop(0)
            self.alarms["init_tangoject"] = ATTACK_INTERVAL_TIME
        else:
            self.alarms["init_player_attack"] = ATTACK_INTERVAL_TIME

    def event_step(self, time_passed, delta_mult):
        if self.notification_text:
            self.project_text(
                font_big, self.notification_text, self.width / 2, 8, 0,
                width=self.width - 16, halign=sge.s.center)

        y = self.real_height - 8
        self.project_text(font_big, str(self.player_hp), 8, y, 0,
                          halign=sge.s.left, valign=sge.s.bottom)
        self.project_text(font_big, str(self.enemy_hp), self.width - 8, y, 0,
                          halign=sge.s.right, valign=sge.s.bottom)

    def reset_state(self):
        self.player_object.image_alpha = 255
        self.enemy_object.image_alpha = 255
        self.textbox.text = ""
        self.window.hide()
        self.notification_text = ""

    def choose_tangoji(self):
        self.tangoji = random.choice(player_tangojis)

    def show_clue(self):
        if self.tangoji is not None:
            self.notification_text = self.tangoji.get("clue", "")
            self.window.show()
            self.window.keyboard_focused_widget = self.textbox

    def evaluate_tangoji(self, time=0):
        if self.tangoji is not None and self.callback is not None:
            word = self.tangoji.get("word", "")
            if self.textbox.text.lower().strip() == word.lower().strip():
                self.tangoji.setdefault("power", TANGOJI_MULT_START)
                self.tangoji_bonus = self.tangoji["power"]
                self.tangoji["power"] -= TANGOJI_MULT_DECREMENT
                self.tangoji["power"] = max(self.tangoji["power"],
                                            TANGOJI_MULT_MIN)
                if ("time_limit" in self.alarms and
                        self.alarms["time_limit"] > 0):
                    self.tangoji_bonus += (self.alarms["time_limit"] *
                                           TANGOJI_MULT_TIME_BONUS)
                    del self.alarms["time_limit"]
            else:
                self.tangoji_bonus = 0

            self.callback()
            self.callback = None

    def tangoject(self):
        word = self.tangoji.get("word", "")
        if self.tangoji_bonus:
            self.notification_text = _("You passed the test given to you by {tangomon}!").format(
                tangomon=self.player_name)
            self.alarms["init_player_attack"] = ATTACK_INTERVAL_TIME
        else:
            self.notification_text = _("You failed the test given to you by {tangomon}! {tangomon} loses faith in you and \"{tangoji}\" is transformed back into a tangoji!").format(
                tangomon=self.player_name, tangoji=word)
            self.tangoji["power"] = TANGOJI_MULT_PERSISTENT_MIN
            player_tangojis.append(self.tangoji)
            self.alarms["player_lose"] = ATTACK_INTERVAL_FAIL_TIME

    def player_attack(self):
        global player_tangomon

        self.reset_state()

        word = self.tangoji.get("word", "")
        if self.tangoji_bonus:
            damage = int(self.player_base_power * self.tangoji_bonus)
            self.enemy_hp -= damage
            self.enemy_object.image_alpha = 128
            interval = ATTACK_INTERVAL_TIME
            play_sound(hurt_sound)
            self.notification_text = _('{player} attacks with "{tangoji}", inflicting {damage} damage!').format(
                player=self.player_name, tangoji=word, damage=damage)
        else:
            interval = ATTACK_INTERVAL_FAIL_TIME
            self.notification_text = _("Attack failed! Correct Tangoji (\"{tangoji}\") not entered.").format(
                tangoji=word)

        if self.enemy_hp > 0:
            self.alarms["init_enemy_attack"] = interval
        else:
            player_tangomon = self.player_tangomon
            self.alarms["player_win"] = interval

    def enemy_attack(self):
        self.reset_state()

        word = self.tangoji.get("word", "")
        if self.tangoji_bonus:
            defense = max(1, int(self.player_base_power * self.tangoji_bonus))
            damage = int(max(0, self.enemy_base_power - defense))
            interval = ATTACK_INTERVAL_TIME
            if damage > 0:
                self.player_hp -= damage
                self.player_object.image_alpha = 128
                play_sound(hurt_sound)
                play_sound(block_sound)
                self.notification_text = _('Defense with "{tangoji}" succeeded! Damage from {enemy} attack is only {damage} (reduced by {defense}).').format(
                    enemy=self.enemy_name, tangoji=word, damage=damage,
                    defense=defense)
            else:
                play_sound(block_sound)
                self.notification_text = _('Defense with "{tangoji}" succeeded! {enemy} attack blocked.').format(
                        enemy=self.enemy_name, tangoji=word)
        else:
            damage = int(self.enemy_base_power)
            self.player_hp -= damage
            self.player_object.image_alpha = 128
            interval = ATTACK_INTERVAL_FAIL_TIME
            play_sound(hurt_sound)
            self.notification_text = _("Defense failed! Correct Tangoji (\"{tangoji}\") not entered. {enemy} attacks, inflicting {damage} damage.").format(
                tangoji=word, enemy=self.enemy_name, damage=damage)

        if self.player_hp > 0:
            self.alarms["init_player_attack"] = interval
        else:
            self.alarms["player_lose"] = interval

    def use_tangokan(self):
        global player_tangomon
        global player_tangojis
        global player_tangojections

        self.reset_state()

        if self.tangoji_bonus:
            interval = ATTACK_INTERVAL_TIME
            player_tangomon.append(self.enemy)
            for wait in TANGOJECT_TIMES:
                tangoji = self.tangoji.copy()
                tangoji["time"] = time.time() + wait
                player_tangojections.append(tangoji)

            self.notification_text = _("Impression succeeded! {tangomon} has joined your team!").format(
                tangomon=self.enemy_name)
        else:
            interval = ATTACK_INTERVAL_FAIL_TIME
            self.tangoji["power"] = TANGOJI_MULT_PERSISTENT_MIN
            player_tangojis.append(self.tangoji)
            self.enemy_run()
            self.notification_text = _("Impression failed! {tangomon} runs away, unimpressed, and your tangokan turns back into a tangoji!").format(
                tangomon=self.enemy_name)

        self.alarms["leave_arena"] = interval

    def player_run(self):
        self.reset_state()
        self.player_object.image_xscale = -1
        self.player_object.xvelocity = -5
        self.notification_text = _("{tangomon} is running away!").format(
            tangomon=self.player_name)

    def enemy_run(self):
        self.reset_state()
        self.enemy_object.image_xscale = -1
        self.enemy_object.xvelocity = 5
        self.notification_text = _("{tangomon} is running away!").format(
            tangomon=self.enemy_name)

    def end_battle(self):
        global player_tangojis

        self.reset_state()

        for tangoji in player_tangojis:
            p = tangoji.get("power", TANGOJI_MULT_START)
            tangoji["power"] = max(p, TANGOJI_MULT_PERSISTENT_MIN)

        load_map()

    def event_key_press(self, key, char):
        if key in {sge.s.enter, sge.s.kp_enter}:
            self.evaluate_tangoji()
        elif key == sge.s.escape:
            text = _("WARNING: If you leave this battle, you will lose your current tangomon! Are you sure?")
            buttons = [_("No"), _("Yes")]
            if xsge_gui.show_message(gui_handler, message=text, buttons=buttons):
                self.end_battle()

    def event_alarm(self, alarm_id):
        if alarm_id == "time_limit":
            self.evaluate_tangoji()
        elif alarm_id == "init_tangoject":
            self.show_clue()
            self.callback = self.tangoject
            self.alarms["time_limit"] = TANGOJI_ENTRY_TIME
        elif alarm_id == "init_player_attack":
            self.reset_state()
            self.choose_tangoji()
            self.show_clue()
            self.callback = self.player_attack
            self.alarms["time_limit"] = TANGOJI_ENTRY_TIME
        elif alarm_id == "init_enemy_attack":
            self.reset_state()
            self.choose_tangoji()
            self.show_clue()
            self.callback = self.enemy_attack
            self.alarms["time_limit"] = TANGOJI_ENTRY_TIME
        elif alarm_id == "player_lose":
            self.player_run()
            del player_tangomon[self.player]
            self.alarms["leave_arena"] = ATTACK_INTERVAL_TIME
        elif alarm_id == "player_win":
            self.reset_state()

            tangokans = get_player_active_tangokans()
            if tangokans:
                msg = _("Do you want to impress the {tangomon} with one of your tangokans?").format(
                    tangomon=self.enemy_name)
                buttons = [_("No"), _("Yes")]
                use_tangokan = xsge_gui.show_message(gui_handler, message=msg,
                                                      buttons=buttons)
            else:
                use_tangokan = False

            if use_tangokan:
                i = random.choice(tangokans)
                self.tangoji = player_tangokans.pop(i)
                self.show_clue()
                self.callback = self.use_tangokan
                self.alarms["time_limit"] = TANGOJI_ENTRY_TIME
            else:
                msg = _("The {tangomon} offers to teach you a new tangoji. Accept the offer?").format(
                    tangomon=self.enemy_name)
                buttons = [_("No"), _("Yes")]
                r = False
                if xsge_gui.show_message(gui_handler, message=msg,
                                         buttons=buttons):
                    r = add_player_tangoji()
                self.enemy_run()
                if r:
                    self.notification_text = _("New tangoji added!")
                self.alarms["leave_arena"] = ATTACK_INTERVAL_TIME
        elif alarm_id == "leave_arena":
            self.end_battle()


class CreditsScreen(sge.dsp.Room):

    def event_room_start(self):
        with open(os.path.join(DATA, "credits.json"), 'r') as f:
            sections = json.load(f)

        logo_section = sge.dsp.Object.create(self.width / 2, self.height,
                                             sprite=logo_sprite,
                                             tangible=False)
        self.sections = [logo_section]
        for section in sections:
            if "title" in section:
                head_sprite = sge.gfx.Sprite.from_text(
                    font_big, section["title"], width=self.width,
                    color=sge.gfx.Color("white"), halign="center")
                x = self.width / 2
                y = self.sections[-1].bbox_bottom + font_big.size * 3
                head_section = sge.dsp.Object.create(x, y, sprite=head_sprite,
                                                     tangible=False)
                self.sections.append(head_section)

            if "lines" in section:
                for line in section["lines"]:
                    list_sprite = sge.gfx.Sprite.from_text(
                        font, line, width=self.width - 2 * TILE_SIZE,
                        color=sge.gfx.Color("white"), halign="center")
                    x = self.width / 2
                    y = self.sections[-1].bbox_bottom + font.size
                    list_section = sge.dsp.Object.create(
                        x, y, sprite=list_sprite, tangible=False)
                    self.sections.append(list_section)

        for obj in self.sections:
            obj.yvelocity = -0.5

    def event_step(self, time_passed, delta_mult):
        if self.sections[0].yvelocity > 0 and self.sections[0].y > self.height:
            for obj in self.sections:
                obj.yvelocity = 0

        if self.sections[-1].bbox_bottom < 0 and "end" not in self.alarms:
            sge.snd.Music.stop(fade_time=3000)
            self.alarms["end"] = 3.5 * FPS

    def event_alarm(self, alarm_id):
        if alarm_id == "end":
            sge.game.start_room.start()

    def event_key_press(self, key, char):
        if key == sge.s.down:
            if "end" not in self.alarms:
                for obj in self.sections:
                    obj.yvelocity -= 0.25
        elif key == sge.s.up:
            if "end" not in self.alarms:
                for obj in self.sections:
                    obj.yvelocity += 0.25
        elif key in {sge.s.enter, sge.s.escape}:
            sge.game.start_room.start()


class Object(sge.dsp.Object):

    def event_end_step(self, time_passed, delta_mult):
        self.z = (math.floor(self.z) + 0.5 +
                  0.24999 * self.image_bottom / sge.game.current_room.height)


class Player(Object, xsge_physics.Collider):

    """The player which navigates the overworld."""

    def event_create(self):
        global player_dest
        global player_x
        global player_y

        if player_dest is not None:
            for obj in sge.game.current_room.objects:
                if isinstance(obj, Door) and obj.dest == player_dest:
                    player_x = obj.x
                    player_y = obj.y
                    break
            player_dest = None

        if player_x is not None:
            self.x = player_x
        if player_y is not None:
            self.y = player_y

        self.sprite = character_down_sprites[player_character]

        self.bbox_x = PLAYER_BBOX_X
        self.bbox_y = PLAYER_BBOX_Y
        self.bbox_width = PLAYER_BBOX_WIDTH
        self.bbox_height = PLAYER_BBOX_HEIGHT

        view = sge.game.current_room.views[0]
        view.x = self.image_xcenter - view.width / 2
        view.y = self.image_ycenter - view.height / 2

    def event_step(self, time_passed, delta_mult):
        global player_x
        global player_y

        xmove = (sge.keyboard.get_pressed(sge.s.right) -
                 sge.keyboard.get_pressed(sge.s.left))
        ymove = (sge.keyboard.get_pressed(sge.s.down) -
                 sge.keyboard.get_pressed(sge.s.up))
        if xmove or ymove:
            xmove *= PLAYER_SPEED * delta_mult
            ymove *= PLAYER_SPEED * delta_mult
            if xmove and ymove:
                xmove *= math.cos(math.radians(45))
                ymove *= math.sin(math.radians(45))
            self.move_x(xmove)
            self.move_y(ymove)
            player_x = self.x
            player_y = self.y

            # Check for encounter
            if (not self.collision(SafeZone) and
                    any([random.random() < PLAYER_ENCOUNTER_CHANCE
                         for j in six.moves.range(int(delta_mult))])):
                dungeon = self.collision(Dungeon)
                forest = self.collision(Forest)
                if dungeon:
                    level = dungeon[0].level
                    max_level = level + DUNGEON_LEVEL_DEPTH
                    while True:
                        tangomon = random.choice(list(dungeon_tangomon))
                        if tangomon in dungeon_tangomon_encountered:
                            i = dungeon_tangomon_encountered.index(tangomon)
                            if level <= i <= max_level:
                                break
                        elif len(dungeon_tangomon_encountered) - 1 < max_level:
                            break

                    arena = Arena(tangomon, music="battle_dungeon.ogg")
                elif forest:
                    level = forest[0].level
                    max_level = level + FOREST_LEVEL_DEPTH
                    while True:
                        tangomon = random.choice(list(forest_tangomon))
                        if tangomon in forest_tangomon_encountered:
                            i = forest_tangomon_encountered.index(tangomon)
                            if level <= i <= max_level:
                                break
                        elif len(forest_tangomon_encountered) - 1 < max_level:
                            break

                    arena = Arena(tangomon, music="battle.ogg")
                else:
                    tangomon = random.choice(list(grassland_tangomon))
                    arena = Arena(tangomon, music="battle.ogg")
                arena.start()

            if xmove > 0:
                self.sprite = character_right_sprites[player_character]
            elif xmove < 0:
                self.sprite = character_left_sprites[player_character]
            elif ymove > 0:
                self.sprite = character_down_sprites[player_character]
            elif ymove < 0:
                self.sprite = character_up_sprites[player_character]

            self.image_fps = None
        else:
            self.image_fps = 0

        # Adjust view
        view = sge.game.current_room.views[0]
        view.x = self.image_xcenter - view.width / 2
        view.y = self.image_ycenter - view.height / 2

    def warp(self, dest):
        global player_map
        global player_dest
        global player_x
        global player_y

        if ":" in dest:
            player_map, player_dest = dest.split(':', 1)
        else:
            player_map = dest
            player_dest = sge.game.current_room.fname

        player_x = None
        player_y = None

        load_map()

    def event_physics_collision_left(self, other, move_loss):
        for door in self.collision(Door):
            if self.bbox_left == door.bbox_left:
                self.warp(door.dest)

    def event_physics_collision_right(self, other, move_loss):
        for door in self.collision(Door):
            if self.bbox_right == door.bbox_right:
                self.warp(door.dest)

    def event_physics_collision_top(self, other, move_loss):
        for door in self.collision(Door):
            if self.bbox_top == door.bbox_top:
                self.warp(door.dest)

    def event_physics_collision_bottom(self, other, move_loss):
        for door in self.collision(Door):
            if self.bbox_bottom == door.bbox_bottom:
                self.warp(door.dest)


class Solid(xsge_physics.Solid):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(Solid, self).__init__(*args, **kwargs)


class Door(sge.dsp.Object):

    """Warps player to another door."""

    def __init__(self, x, y, z=0, dest=None, spawn_id=None, **kwargs):
        self.dest = dest
        self.spawn_id = spawn_id
        if dest and not spawn_id:
            if ':' in dest:
                self.spawn_id, i = dest.split(':', 1)
            else:
                self.spawn_id = dest

        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(Door, self).__init__(x, y, z=z, **kwargs)


class SpecialZone(sge.dsp.Object):

    def __init__(self, x, y, z=0, level=0, **kwargs):
        self.level = level
        kwargs.setdefault("visible", False)
        kwargs.setdefault("checks_collisions", False)
        super(SpecialZone, self).__init__(x, y, z=z, **kwargs)


class SafeZone(SpecialZone):

    """Area where no encounters will happen."""


class Forest(SpecialZone):

    """Forest area (as opposed to grassland)"""


class Dungeon(SpecialZone):

    """Dungeon area (as opposed to grassland)"""


class FontChooser(xsge_gui.Dialog):

    """Screen shown at the start of the game to choose the font."""

    def __init__(self, parent):
        super(FontChooser, self).__init__(
            parent, 0, 0, SCREEN_SIZE[0], SCREEN_SIZE[1], border=False)

        padding = 8

        text = _("The quick brown fox jumps over the lazy dog.")
        test_textbox = xsge_gui.TextBox(self, padding, padding, 0,
                                        width=(self.width - 2 * padding),
                                        text=text, text_limit=200)

        h = xsge_gui.button_sprite.height
        text = _("Done")
        done_button = xsge_gui.Button(self, padding,
                                      self.height - h - padding, 4, text,
                                      width=(self.width - 2 * padding))
        done_button.event_press = self.destroy

        h = xsge_gui.button_sprite.height
        y = done_button.y - h - padding * 2
        text = _("Change Font")
        change_font_button = xsge_gui.Button(self, padding, y, 3, text,
                                             width=(self.width - 2 * padding))
        
        h = xsge_gui.textbox_sprite.height
        y = change_font_button.y - h - padding
        font_textbox = xsge_gui.TextBox(
            self, padding, y, 2,
            width=(self.width - 2 * padding),
            text_limit=50)

        def press_change_font(self=self, font_textbox=font_textbox):
            global font_name
            font_name = font_textbox.text
            create_fonts()
            for widget in self.widgets:
                widget.font = font
                widget.redraw()
            self.redraw()

        change_font_button.event_press = press_change_font

        h = y - xsge_gui.textbox_sprite.height - 3 * padding
        text = _('If you will be using non-ASCII characters, please ensure that they display correctly by typing them into the test textbox above. If they do not, please specify a different font to use by entering its name in the textbox below and then clicking "Change Font". When you are finished, press "Done".\n\nFor English, some good font choices are Droid Sans and Arial.')
        label = xsge_gui.Label(
            self, self.width / 2, 2 * padding + xsge_gui.textbox_sprite.height,
            1, text, width=(self.width - 2 * padding), height=h,
            halign=sge.s.center)


class Menu(xsge_gui.MenuWindow):

    items = []

    @classmethod
    def create(cls, default=0, y=None):
        if cls.items:
            if y is None:
                y = sge.game.height * 2 / 3
            self = cls.from_text(
                gui_handler, sge.game.width / 2, y,
                cls.items, font_normal=font,
                color_normal=sge.gfx.Color("gray"),
                color_selected=sge.gfx.Color("white"),
                background_color=menu_color, margin=9, halign="center",
                valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            self.show()
            return self

    def event_change_keyboard_focus(self):
        play_sound(select_sound)


class MainMenu(Menu):

    items = [_("New Game"), _("Load Game"), _("Options"), _("Credits"),
             _("Support on Patreon"), _("Quit")]

    def event_choose(self):
        if self.choice == 0:
            play_sound(confirm_sound)
            NewGameMenu.create_page()
        elif self.choice == 1:
            play_sound(confirm_sound)
            LoadGameMenu.create_page()
        elif self.choice == 2:
            play_sound(confirm_sound)
            OptionsMenu.create_page()
        elif self.choice == 3:
            play_sound(confirm_sound)
            credits_room = CreditsScreen()
            credits_room.start()
        elif self.choice == 4:
            play_sound(confirm_sound)
            webbrowser.open("https://www.patreon.com/onpon4")
            MainMenu.create(self.choice)
        else:
            sge.game.end()


class NewGameMenu(Menu):

    @classmethod
    def create_page(cls, default=0):
        cls.items = []
        for slot in save_slots:
            if slot is None:
                cls.items.append(_("-Empty-"))
            else:
                name = slot.get("player_name")
                cls.items.append(name)

        cls.items.append(_("Back"))

        return cls.create(default)

    def event_choose(self):
        global current_save_slot

        if self.choice in six.moves.range(len(save_slots)):
            play_sound(confirm_sound)
            current_save_slot = self.choice
            if save_slots[current_save_slot] is None:
                new_game()
            else:
                OverwriteConfirmMenu.create(default=1)
        else:
            play_sound(cancel_sound)
            MainMenu.create(default=0)


class OverwriteConfirmMenu(Menu):

    items = [_("Overwrite this save file"), _("Back")]

    def event_choose(self):
        if self.choice == 0:
            play_sound(confirm_sound)
            new_game()
        else:
            play_sound(cancel_sound)
            NewGameMenu.create(default=current_save_slot)


class LoadGameMenu(NewGameMenu):

    def event_choose(self):
        global current_save_slot

        if self.choice in six.moves.range(len(save_slots)):
            play_sound(confirm_sound)
            current_save_slot = self.choice
            load_game()
        else:
            play_sound(cancel_sound)
            MainMenu.create(default=1)


class OptionsMenu(Menu):

    @classmethod
    def create_page(cls, default=0):
        smt = scale_method if scale_method else "fastest"
        cls.items = [
            _("Fullscreen: {}").format(_("On") if fullscreen else _("Off")),
            _("Scale Method: {}").format(smt),
            _("Sound: {}").format(_("On") if sound_enabled else _("Off")),
            _("Music: {}").format(_("On") if music_enabled else _("Off")),
            _("Show FPS: {}").format(_("On") if fps_enabled else _("Off")),
            _("Select Font"), _("Back")]
        return cls.create(default)

    def event_choose(self):
        global fullscreen
        global scale_method
        global sound_enabled
        global music_enabled
        global stereo_enabled
        global fps_enabled
        global joystick_threshold

        if self.choice == 0:
            play_sound(select_sound)
            fullscreen = not fullscreen
            sge.game.fullscreen = fullscreen
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 1:
            choices = [None, "noblur", "smooth"] + sge.SCALE_METHODS
            if scale_method in choices:
                i = choices.index(scale_method)
            else:
                i = 0

            play_sound(select_sound)
            i += 1
            i %= len(choices)
            scale_method = choices[i]
            sge.game.scale_method = scale_method
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 2:
            sound_enabled = not sound_enabled
            play_sound(confirm_sound)
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 3:
            music_enabled = not music_enabled
            play_music(sge.game.current_room.music)
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 4:
            play_sound(select_sound)
            fps_enabled = not fps_enabled
            OptionsMenu.create_page(default=self.choice)
        elif self.choice == 5:
            FontChooser(gui_handler).show()
            OptionsMenu.create_page(default=self.choice)
        else:
            play_sound(cancel_sound)
            write_to_disk()
            MainMenu.create(default=3)


class ModalMenu(xsge_gui.MenuDialog):

    items = []

    @classmethod
    def create(cls, default=0):
        if cls.items:
            self = cls.from_text(
                gui_handler, sge.game.width / 2, sge.game.height / 2,
                cls.items, font_normal=font,
                color_normal=sge.gfx.Color("gray"),
                color_selected=sge.gfx.Color("white"),
                background_color=menu_color, margin=9, halign="center",
                valign="middle")
            default %= len(self.widgets)
            self.keyboard_focused_widget = self.widgets[default]
            self.show()
            return self

    def event_change_keyboard_focus(self):
        play_sound(select_sound)


class WorldmapMenu(ModalMenu):

    items = [_("Continue Game"), _("View Statistics"), _("View Tangomon"),
             _("View Tangoji"), _("Change Tangoji"), _("Create Tangokan"),
             _("Return to Title Screen")]

    def event_choose(self):
        if self.choice == 1:
            unique_tangomon = len(get_player_unique_tangomon())
            active_tangokans = len(get_player_active_tangokans())
            text = _("PLAYER STATISTICS\n\nName: {name}\nTotal tangomon: {tangomon}\nTangomon types: {unique_tangomon}\nActive tangoji: {tangoji}\nActive tangokans: {tangokans}\nInactive tangokans: {inactive_tangokans}\nCompletion: {completion}%").format(
                name=player_name, tangomon=len(player_tangomon),
                unique_tangomon=unique_tangomon, tangoji=len(player_tangojis),
                tangokans=active_tangokans,
                inactive_tangokans=(len(player_tangokans) - active_tangokans),
                completion=int(100 * unique_tangomon / len(get_all_tangomon())))

            DialogBox(gui_handler, text).show()
            WorldmapMenu.create(default=self.choice)
        elif self.choice == 2:
            play_sound(confirm_sound)
            TangomonInfo().show()
        elif self.choice == 3:
            play_sound(confirm_sound)
            TangojiMenu.create_page()
        elif self.choice == 4:
            play_sound(confirm_sound)
            ChangeTangojiMenu.create_page()
        elif self.choice == 5:
            play_sound(confirm_sound)
            if len(player_tangojis) > TANGOJI_MIN:
                play_sound(confirm_sound)
                CreateTangokanMenu.create_page()
            else:
                msg = _("You don't have enough tangojis in reserve to make a tangokan. You can only create a tangokan if, after spending one of your tangojis to make the tangokan, you have at least {minimum} left over. Fight some tangomon to get more tangojis!").format(minimum=TANGOJI_MIN)
                DialogBox(gui_handler, msg).show()
        elif self.choice == 6:
            save_game()
            sge.game.start_room.start()
        else:
            play_sound(cancel_sound)


class TangojiMenu(ModalMenu):

    current_tangoji = []
    page = 0

    @classmethod
    def create_page(cls, default=0, page=0, refreshlist=False):
        cls.current_tangoji = []
        cls.items = []
        if player_tangojis:
            page_size = TANGOJI_LIST_SIZE
            n_pages = math.ceil(len(player_tangojis) / page_size)
            page = int(page % n_pages)
            page_start = page * page_size
            page_end = min(page_start + page_size, len(player_tangojis))
            current_page = six.moves.range(page_start, page_end)
            cls.current_tangoji = []
            cls.items = []
            for i in current_page:
                cls.current_tangoji.append(i)
                word = player_tangojis[i].get("word", "???")
                cls.items.append(word)

        cls.items.append(_("Next page"))
        cls.items.append(_("Back"))

        cls.page = page
        return cls.create(default)

    def event_choose(self):
        if self.choice == len(self.items) - 2:
            play_sound(select_sound)
            self.create_page(default=-2, page=(self.page + 1))
        elif self.choice is not None and self.choice < len(self.items) - 2:
            play_sound(confirm_sound)
            i = self.current_tangoji[self.choice]
            clue = player_tangojis[i].get("clue", "???")
            DialogBox(gui_handler, clue).show()
            self.create_page(default=self.choice, page=self.page)
        else:
            play_sound(cancel_sound)
            WorldmapMenu.create(default=3)


class ChangeTangojiMenu(TangojiMenu):

    def event_choose(self):
        if self.choice == len(self.items) - 2:
            play_sound(select_sound)
            self.create_page(default=-2, page=(self.page + 1))
        elif self.choice is not None and self.choice < len(self.items) - 2:
            play_sound(confirm_sound)
            i = self.current_tangoji[self.choice]
            text = _("Enter your desired changes to this tangoji.")
            word = player_tangojis[i].get("word", "")
            tangoji_word = xsge_gui.get_text_entry(gui_handler, message=text,
                                                   text=word)
            if tangoji_word:
                player_tangojis[i]["word"] = tangoji_word

            text = _("Enter your desired changes to this tangoji's clue.")
            clue = player_tangojis[i].get("clue", "")
            tangoji_clue = xsge_gui.get_text_entry(gui_handler, message=text,
                                                   text=clue)
            if tangoji_clue:
                player_tangojis[i]["clue"] = tangoji_clue
        else:
            play_sound(cancel_sound)
            WorldmapMenu.create(default=4)


class CreateTangokanMenu(TangojiMenu):

    def event_choose(self):
        if self.choice == len(self.items) - 2:
            play_sound(select_sound)
            self.create_page(default=-2, page=(self.page + 1))
        elif self.choice is not None and self.choice < len(self.items) - 2:
            play_sound(confirm_sound)
            i = self.current_tangoji[self.choice]
            tangoji = player_tangojis.pop(i)
            make_tangokan(tangoji)
            msg = _("New tangokan created! It will activate in 24 hours. At that point, you will be able to use your tangokan to convince a new tangomon to join your team!")
            DialogBox(gui_handler, msg).show()
        else:
            play_sound(cancel_sound)
            WorldmapMenu.create(default=5)


class TangomonInfo(xsge_gui.Dialog):

    def __init__(self, tangomon=0):
        super(TangomonInfo, self).__init__(
            gui_handler, 0, 0, sge.game.width, sge.game.height, border=False,
            background_color=menu_color)

        self.tangomon = tangomon % len(player_tangomon)
        iname = player_tangomon[self.tangomon]
        name = get_tangomon_name(iname)
        sprite = get_tangomon_sprite(iname)
        hp = get_tangomon_hp_max(iname)
        base_power = get_tangomon_base_power(iname)

        padding = 8

        y = padding
        name_label = xsge_gui.Label(
            self, self.width / 2, y, 10, name, width=(self.width - 2 * padding),
            halign=sge.s.center)

        y += font.get_height(name) + padding
        sprite_widget = xsge_gui.DecorativeWidget(
            self, self.width / 2 - sprite.width / 2, y, 10, sprite=sprite)

        y += sprite.height + padding
        info_text = _("HP: {hp}\nPower: {power}").format(
            hp=hp, power=int(base_power))
        info_label = xsge_gui.Label(
            self, self.width / 2, y, 10, info_text,
            width=(self.width - 2 * padding), halign=sge.s.center)

    def event_press_left(self):
        self.destroy()
        sge.game.refresh()
        play_sound(select_sound)
        TangomonInfo(self.tangomon - 1).show()

    def event_press_right(self):
        self.destroy()
        sge.game.refresh()
        play_sound(select_sound)
        TangomonInfo(self.tangomon + 1).show()

    def event_press_enter(self):
        self.destroy()
        sge.game.refresh()
        play_sound(cancel_sound)
        WorldmapMenu.create(default=2)

    def event_press_escape(self):
        self.event_press_enter()


class DialogLabel(xsge_gui.ProgressiveLabel):

    def event_add_character(self):
        if self.text[-1] not in (' ', '\n', '\t'):
            play_sound(type_sound)


class DialogBox(xsge_gui.Dialog):

    def __init__(self, parent, text, portrait=None, rate=TEXT_SPEED):
        width = sge.game.width / 2
        x_padding = 16
        y_padding = 16
        label_x = 8
        label_y = 8
        if portrait is not None:
            x_padding += 8
            label_x += 8
            portrait_w = portrait.width
            portrait_h = portrait.height
            label_x += portrait_w
        else:
            portrait_w = 0
            portrait_h = 0
        label_w = max(1, width - portrait_w - x_padding)
        height = max(1, portrait_h + y_padding,
                     font.get_height(text, width=label_w) + y_padding)
        x = sge.game.width / 2 - width / 2
        y = sge.game.height / 2 - height / 2
        super(DialogBox, self).__init__(
            parent, x, y, width, height,
            background_color=menu_color, border=False)
        label_h = max(1, height - y_padding)

        self.label = DialogLabel(self, label_x, label_y, 0, text, font=font,
                                 width=label_w, height=label_h,
                                 color=sge.gfx.Color("white"), rate=rate)

        if portrait is not None:
            xsge_gui.Widget(self, 8, 8, 0, sprite=portrait)

    def event_press_enter(self):
        if len(self.label.text) < len(self.label.full_text):
            self.label.text = self.label.full_text
        else:
            self.destroy()

    def event_press_escape(self):
        self.destroy()
        room = sge.game.current_room
        if (isinstance(room, Level) and
                room.timeline_skip_target is not None and
                room.timeline_step < room.timeline_skip_target):
            room.timeline_skipto(room.timeline_skip_target)


def get_object(x, y, cls=None, **kwargs):
    cls = TYPES.get(cls, xsge_tmx.Decoration)
    return cls(x, y, **kwargs)


def get_tangomon_name(tangomon):
    return tangomon.replace("_", " ").title()


def get_all_tangomon():
    return grassland_tangomon | forest_tangomon | dungeon_tangomon


def get_player_unique_tangomon():
    return list(set(player_tangomon))


def get_player_active_tangokans():
    active_tangokans = []
    for i in six.moves.range(len(player_tangokans)):
        tangokan = player_tangokans[i]
        tangokan.setdefault("active_time", time.time() + TANGOKAN_WAIT_TIME)
        if time.time() >= tangokan["active_time"]:
            active_tangokans.append(i)

    return active_tangokans


def make_tangokan(tangoji):
    global player_tangokans

    tangokan = tangoji.copy()
    tangokan["active_time"] = time.time() + TANGOKAN_WAIT_TIME
    player_tangokans.append(tangokan)


def schedule_tangojection(tangokan):
    global player_tangojections

    for st in TANGOJECT_TIMES:
        tangojection = tangokan.copy()
        tangojection["time"] = time.time() + st
        player_tangojections.append(tangojection)

    player_tangojections.sort(key=lambda d: d["time"])


def get_tangomon_sprite(tangomon):
    if tangomon in grassland_tangomon:
        d = os.path.join(DATA, "images", "tangomon", "grassland")
    elif tangomon in forest_tangomon:
        d = os.path.join(DATA, "images", "tangomon", "forest")
    elif tangomon in dungeon_tangomon:
        d = os.path.join(DATA, "images", "tangomon", "dungeon")
    else:
        warnings.warn('"{}" is not a valid Tangomon.'.format(tangomon))
        return None

    return sge.gfx.Sprite(tangomon, d)


def evaluate_tangomon(tangomon):
    if tangomon in grassland_tangomon:
        if tangomon not in grassland_tangomon_encountered:
            grassland_tangomon_encountered.append(tangomon)
    elif tangomon in forest_tangomon:
        if tangomon not in forest_tangomon_encountered:
            forest_tangomon_encountered.append(tangomon)
    elif tangomon in dungeon_tangomon:
        if tangomon not in dungeon_tangomon_encountered:
            dungeon_tangomon_encountered.append(tangomon)


def get_tangomon_hp_max(tangomon):
    if tangomon in grassland_tangomon:
        if tangomon not in grassland_tangomon_encountered:
            grassland_tangomon_encountered.append(tangomon)

        i = grassland_tangomon_encountered.index(tangomon)
        return int(HEALTH_MAX_START * (INCREMENT_FACTOR ** i))
    elif tangomon in forest_tangomon:
        if tangomon not in forest_tangomon_encountered:
            forest_tangomon_encountered.append(tangomon)

        i = forest_tangomon_encountered.index(tangomon)
        i += len(grassland_tangomon)
        return int(HEALTH_MAX_START * (INCREMENT_FACTOR ** i))
    elif tangomon in dungeon_tangomon:
        if tangomon not in dungeon_tangomon_encountered:
            dungeon_tangomon_encountered.append(tangomon)

        i = dungeon_tangomon_encountered.index(tangomon)
        i += len(grassland_tangomon) + len(forest_tangomon)
        return int(HEALTH_MAX_START * (INCREMENT_FACTOR ** i))
    else:
        return 1


def get_tangomon_base_power(tangomon):
    if tangomon in grassland_tangomon:
        if tangomon not in grassland_tangomon_encountered:
            grassland_tangomon_encountered.append(tangomon)

        i = grassland_tangomon_encountered.index(tangomon)
        return BASE_POWER_START * (INCREMENT_FACTOR ** i)
    elif tangomon in forest_tangomon:
        if tangomon not in forest_tangomon_encountered:
            forest_tangomon_encountered.append(tangomon)

        i = forest_tangomon_encountered.index(tangomon)
        i += len(grassland_tangomon)
        return BASE_POWER_START * (INCREMENT_FACTOR ** i)
    elif tangomon in dungeon_tangomon:
        if tangomon not in dungeon_tangomon_encountered:
            dungeon_tangomon_encountered.append(tangomon)

        i = dungeon_tangomon_encountered.index(tangomon)
        i += len(grassland_tangomon) + len(forest_tangomon)
        return BASE_POWER_START * (INCREMENT_FACTOR ** i)
    else:
        return 1


def give_player_tangomon(tangomon):
    global player_tangomon
    player_tangomon.append(tangomon)


def add_player_tangoji():
    global player_tangojis

    text = _("Enter your new tangoji.")
    tangoji_word = xsge_gui.get_text_entry(gui_handler, message=text)
    if tangoji_word:
        text = _("Enter the clue for your new tangoji.")
        tangoji_clue = xsge_gui.get_text_entry(gui_handler, message=text)
        if tangoji_clue:
            player_tangojis.append({"word": tangoji_word, "clue": tangoji_clue})
            return True

    return False


def play_sound(sound, x=None, y=None, force=True):
    if sound_enabled and sound:
        sound.play(force=force)


def play_music(music, force_restart=False):
    """Play the given music file, starting with its start piece."""
    if music_enabled and music:
        music_object = loaded_music.get(music)
        if music_object is None:
            try:
                music_object = sge.snd.Music(os.path.join(DATA, "music",
                                                          music))
            except (IOError, OSError):
                sge.snd.Music.clear_queue()
                sge.snd.Music.stop()
                return
            else:
                loaded_music[music] = music_object

        name, ext = os.path.splitext(music)
        music_start = ''.join([name, "-start", ext])
        music_start_object = loaded_music.get(music_start)
        if music_start_object is None:
            try:
                music_start_object = sge.snd.Music(os.path.join(DATA, "music",
                                                                music_start))
            except (IOError, OSError):
                pass
            else:
                loaded_music[music_start] = music_start_object

        if (force_restart or (not music_object.playing and
                              (music_start_object is None or
                               not music_start_object.playing))):
            sge.snd.Music.clear_queue()
            sge.snd.Music.stop()
            if music_start_object is not None:
                music_start_object.play()
                music_object.queue(loops=None)
            else:
                music_object.play(loops=None)
    else:
        sge.snd.Music.clear_queue()
        sge.snd.Music.stop()


def create_fonts():
    # Create the font objects.
    global font
    global font_small
    global font_big

    font = sge.gfx.Font(font_name, size=16)
    font_small = sge.gfx.Font(font_name, size=12)
    font_big = sge.gfx.Font(font_name, size=20)

    # Assign the fonts to xsge_gui
    xsge_gui.default_font = font
    xsge_gui.button_font = sge.gfx.Font(font_name, size=12, bold=True)
    xsge_gui.textbox_font = sge.gfx.Font(font_name, size=12)
    xsge_gui.title_font = sge.gfx.Font(font_name, size=14, bold=True)


def new_game():
    global player_name
    global player_character
    global player_map
    global player_x
    global player_y
    global player_tangojis
    global player_tangokans
    global player_tangomon
    global player_tangojections
    global grassland_tangomon_encountered
    global forest_tangomon_encountered
    global dungeon_tangomon_encountered
    text = _("What is your name?")
    player_name = None
    while not player_name:
        player_name = xsge_gui.get_text_entry(gui_handler, message=text)
    player_character = 0
    player_map = None
    player_x = None
    player_y = None
    player_tangojis = []
    player_tangokans = []
    player_tangomon = []
    player_tangojections = []
    grassland_tangomon_encountered = []
    forest_tangomon_encountered = []
    dungeon_tangomon_encountered = []
    CharacterChooser().start()


def save_game():
    global save_slots

    if current_save_slot is not None:
        save_slots[current_save_slot] = {
            "player_name": player_name, "player_character": player_character,
            "player_map": player_map, "player_x": player_x,
            "player_y": player_y, "player_tangojis": player_tangojis,
            "player_tangokans": player_tangokans,
            "player_tangomon": player_tangomon,
            "player_tangojections": player_tangojections,
            "grassland_tangomon_encountered": grassland_tangomon_encountered,
            "forest_tangomon_encountered": forest_tangomon_encountered,
            "dungeon_tangomon_encountered": dungeon_tangomon_encountered}

    write_to_disk()


def load_game():
    global player_name
    global player_character
    global player_map
    global player_x
    global player_y
    global player_tangojis
    global player_tangokans
    global player_tangomon
    global player_tangojections
    global grassland_tangomon_encountered
    global forest_tangomon_encountered
    global dungeon_tangomon_encountered

    if (current_save_slot is not None and
            save_slots[current_save_slot] is not None):
        slot = save_slots[current_save_slot]
        player_name = slot.get("player_name")
        player_character = slot.get("player_character", 0)
        player_map = slot.get("player_map")
        player_x = slot.get("player_x")
        player_y = slot.get("player_y")
        player_tangojis = slot.get("player_tangojis", [])
        player_tangokans = slot.get("player_tangokans", [])
        player_tangomon = slot.get("player_tangomon", [])
        player_tangojections = slot.get("player_tangojections", [])
        grassland_tangomon_encountered = slot.get("grassland_tangomon_encountered", [])
        forest_tangomon_encountered = slot.get("forest_tangomon_encountered", [])
        dungeon_tangomon_encountered = slot.get("dungeon_tangomon_encountered", [])
        load_map()
    else:
        new_game()


def load_map():
    global player_map
    global player_x
    global player_y

    if not player_tangomon:
        if grassland_tangomon_encountered:
            player_tangomon.append(grassland_tangomon_encountered[0])
        else:
            player_tangomon.append(random.choice(list(grassland_tangomon)))

        player_map = None
        player_x = None
        player_y = None

    if player_map is None:
        player_map = "0.tmx"

    while len(player_tangojis) < TANGOJI_MIN:
        r = add_player_tangoji()
        if not r:
            text = _("You must add a tangoji to continue.")
            DialogBox(gui_handler, text).show()

    room = xsge_tmx.load(os.path.join(DATA, "worldmaps", player_map),
                         cls=Worldmap, types=TYPES)
    room.fname = player_map
    room.start()


def write_to_disk():
    # Write our saves and settings to disk.
    cfg = {"version": 0, "first_run": first_run, "font_name": font_name,
           "fullscreen": fullscreen, "scale_method": scale_method,
           "sound_enabled": sound_enabled, "music_enabled": music_enabled,
           "fps_enabled": fps_enabled}

    with open(os.path.join(CONFIG, "config.json"), 'w') as f:
        json.dump(cfg, f, indent=4)

    with open(os.path.join(CONFIG, "save_slots.json"), 'w') as f:
        json.dump(save_slots, f, indent=4)


TYPES = {"objects": get_object, "player": Player,
         "solid": Solid, "door": Door, "safe_zone": SafeZone, "forest": Forest,
         "dungeon": Dungeon}


print(_("Initializing game system..."))
Game(SCREEN_SIZE[0], SCREEN_SIZE[1], fps=FPS, delta=DELTA, delta_min=DELTA_MIN,
     delta_max=DELTA_MAX, window_text="Tangomon {}".format(__version__),
     window_icon=os.path.join(DATA, "images", "misc", "icon.png"))

sge.keyboard.set_repeat(interval=KEY_REPEAT_INTERVAL, delay=KEY_REPEAT_DELAY)

print(_("Initializing GUI system..."))
xsge_gui.init()
xsge_gui.next_widget_keys = [sge.s.tab, sge.s.down]
xsge_gui.previous_widget_keys = [sge.s.up]
xsge_gui.window_background_color = sge.gfx.Color("black")
xsge_gui.keyboard_focused_box_color = sge.gfx.Color("white")
xsge_gui.text_color = sge.gfx.Color("white")
gui_handler = xsge_gui.Handler()

menu_color = sge.gfx.Color("black")

print(_("Loading media..."))

# Load sprites
fname = os.path.join(DATA, "images", "objects", "characters.png")
character_down_sprites = [
    sge.gfx.Sprite.from_tileset(fname, 64, 0, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 128, 0, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 192, 0, columns=4, width=16, height=16,
                                fps=10)]
character_left_sprites = [
    sge.gfx.Sprite.from_tileset(fname, 64, 16, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 128, 16, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 192, 16, columns=4, width=16, height=16,
                                fps=10)]
character_right_sprites = [
    sge.gfx.Sprite.from_tileset(fname, 64, 32, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 128, 32, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 192, 32, columns=4, width=16, height=16,
                                fps=10)]
character_up_sprites = [
    sge.gfx.Sprite.from_tileset(fname, 64, 48, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 128, 48, columns=4, width=16, height=16,
                                fps=10),
    sge.gfx.Sprite.from_tileset(fname, 192, 48, columns=4, width=16, height=16,
                                fps=10)]

d = os.path.join(DATA, "images", "misc")
logo_sprite = sge.gfx.Sprite("logo", d, origin_x=300)

# Find tangomon
d = os.path.join(DATA, "images", "tangomon", "grassland")
for fname in os.listdir(d):
    root, ext = os.path.splitext(fname)
    try:
        sprite = sge.gfx.Sprite(root, d)
    except (IOError, OSError):
        pass
    else:
        grassland_tangomon.add(root)

d = os.path.join(DATA, "images", "tangomon", "forest")
for fname in os.listdir(d):
    root, ext = os.path.splitext(fname)
    try:
        sprite = sge.gfx.Sprite(root, d)
    except (IOError, OSError):
        pass
    else:
        forest_tangomon.add(root)

d = os.path.join(DATA, "images", "tangomon", "dungeon")
for fname in os.listdir(d):
    root, ext = os.path.splitext(fname)
    try:
        sprite = sge.gfx.Sprite(root, d)
    except (IOError, OSError):
        pass
    else:
        dungeon_tangomon.add(root)

# Create fonts
create_fonts()

# Load sounds
hurt_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "hurt.wav"))
block_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "block.wav"))

select_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "select.ogg"))
confirm_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "confirm.wav"))
cancel_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "cancel.wav"))
type_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "type.wav"))

# Create rooms
sge.game.start_room = xsge_tmx.load(os.path.join(DATA, "screens", "title.tmx"),
                                    cls=TitleScreen)

if not os.path.exists(CONFIG):
    os.makedirs(CONFIG)

try:
    with open(os.path.join(CONFIG, "config.json")) as f:
        cfg = json.load(f)
except (IOError, OSError, ValueError):
    cfg = {}
finally:
    cfg_version = cfg.get("version", 0)
    first_run = cfg.get("first_run", True)

    font_name = cfg.get("font_name", font_name)
    fullscreen = cfg.get("fullscreen", fullscreen)
    sge.game.fullscreen = fullscreen
    scale_method = cfg.get("scale_method", scale_method)
    sge.game.scale_method = scale_method
    sound_enabled = cfg.get("sound_enabled", sound_enabled)
    music_enabled = cfg.get("music_enabled", music_enabled)
    fps_enabled = cfg.get("fps_enabled", fps_enabled)

    create_fonts()

try:
    with open(os.path.join(CONFIG, "save_slots.json")) as f:
        loaded_slots = json.load(f)
except (IOError, OSError, ValueError):
    pass
else:
    for i in six.moves.range(min(len(loaded_slots), len(save_slots))):
        save_slots[i] = loaded_slots[i]


if __name__ == "__main__":
    print(_("Starting game..."))
    try:
        sge.game.start()
    finally:
        save_game()
