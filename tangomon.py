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

__version__ = "2.0a0"

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
    "--nosave",
    help=_("Disable saving (for testing purposes)"),
    action="store_true")
parser.add_argument(
    "--nodelta",
    help=_("Disable delta timing. Causes the game to slow down when it can't run at full speed instead of becoming choppier."),
    action="store_true")
parser.add_argument(
    "-d", "--datadir",
    help=_('Where to load the game data from (Default: "{}")').format(DATA))
parser.add_argument(
    "-c", "--configdir",
    help=_('Where to store save data in (Default: "{}")').format(CONFIG))
args = parser.parse_args()

NOSAVE = args.nosave
DELTA = not args.nodelta
if args.datadir:
    DATA = args.datadir
if args.configdir:
    CONFIG = args.configdir

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
FPS = 60
DELTA_MIN = FPS / 20
DELTA_MAX = FPS * 4

KEY_REPEAT_INTERVAL = 20
KEY_REPEAT_DELAY = 400

SAVE_NSLOTS = 5

TEXT_SPEED = 1000
TANGOJI_LIST_SIZE = 10

TANGOJI_MIN = 3

ZONES = [
    "grassland", "oceanic_abyss", "dark_forest", "haunted_castle",
    "oasial_crypt", "mountains_of_malevolence", "death_valley",
    "doom_dungeon"]
ZONE_NAMES = {
    "grassland": _("Grassland"),
    "oceanic_abyss": _("Oceanic Abyss"),
    "dark_forest": _("Dark Forest"),
    "haunted_castle": _("Haunted Castle"),
    "oasial_crypt": _("Oasial Crypt"),
    "mountains_of_malevolence": _("Mountains of Malevolence"),
    "death_valley": _("Death Valley"),
    "doom_dungeon": _("Doom Dungeon")}

HEALTH_MAX_START = 500
BASE_POWER_START = 75
HEALTH_INCREMENT_FACTOR = 1.025
BASE_POWER_INCREMENT_FACTOR = 1.025
ZONE_BUFFER = 3
NEW_TANGOMON_REDUNDANCY = 3

BATTLE_START_WAIT = 2 * FPS
TEST_WAIT = FPS / 2
TEST_LIMIT = 5
ATTACK_INTERVAL_TIME = 4 * FPS
ATTACK_INTERVAL_FAIL_TIME = 8 * FPS
TANGOJI_ENTRY_TIME = 30 * FPS
TANGOJI_MULT_START = 1.0
TANGOJI_MULT_DECREMENT = 0.025
TANGOJI_MULT_MIN = 0.25
TANGOJI_MULT_PERSISTENT_MIN = 0.5
TANGOJI_MULT_BULK_BONUS = 0.005
TANGOJI_MULT_TIME_BONUS = 0.5 / TANGOJI_ENTRY_TIME
CRITICAL_CHANCE = 0.02
CRITICAL_MULT = 2
ENEMY_NERF = 0.5

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR
MONTH = 30 * DAY
TANGOKAN_WAIT_TIME = 12 * HOUR

first_run = True

font_name = ""
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
tangomon_sets = {}

current_save_slot = None

player_name = None
player_zone = 0
player_tangojis = []
player_tangokans = []
player_tangomon = []
player_tangojections = []
tangomon_encountered = {}


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

        sge.dsp.Object.create(self.width / 2, 16, sprite=logo_sprite,
                              tangible=False)

        self.menu = MainMenu.create()

    def event_room_resume(self):
        super(TitleScreen, self).event_room_resume()

        if self.menu not in gui_handler.windows:
            self.menu = MainMenu.create()


class Worldmap(Room):

    """
    Selection screen for the different zones.
    """
    
    zone_w = 240
    zone_h = 240

    def event_room_start(self):
        super(Worldmap, self).event_room_start()

        zone_w = self.zone_w
        zone_h = self.zone_h
        unknown_zone_sprite = sge.gfx.Sprite(
            width=zone_w, height=zone_h, origin_x=(zone_w / 2),
            origin_y=(zone_h / 2))
        unknown_zone_sprite.draw_text(
            font_big, "?", zone_w / 2, zone_h / 2, halign=sge.s.center,
            valign=sge.s.middle)
        unknown_zone_sprite.draw_rectangle(
            0, 0, zone_w, zone_h, outline=sge.gfx.Color(sge.s.white))
        self.zone_sprites = []
        d = os.path.join(DATA, "images", "zones")
        for zone in ZONES:
            new_sprite = unknown_zone_sprite
            try:
                new_sprite = sge.gfx.Sprite(
                    zone, d, width=zone_w, height=zone_h,
                    origin_x=(zone_w / 2), origin_y=(zone_h / 2))
            except (IOError, OSError):
                pass
            else:
                new_sprite.draw_rectangle(
                    0, 0, zone_w, zone_h,
                    outline=sge.gfx.Color(sge.s.white))

            self.zone_sprites.append(new_sprite)

    def event_step(self, time_passed, delta_mult):
        zone_distance = self.zone_w + 16
        text_distance = self.zone_h / 2 + 8
        x = self.width / 2 - player_zone * zone_distance
        y = self.height / 2
        name_y = y - text_distance
        progress_y = y + text_distance
        unique_tangomon = set(player_tangomon)
        tangomon_caught = {}
        for zone in ZONES:
            tangomon_caught[zone] = len(unique_tangomon & tangomon_sets[zone])

        for i in six.moves.range(len(self.zone_sprites)):
            zone = ZONES[i]
            zone_sprite = self.zone_sprites[i]
            self.project_sprite(zone_sprite, 0, x, y, 0)
            self.project_text(font, ZONE_NAMES[zone], x, name_y, 0,
                              halign=sge.s.center, valign=sge.s.bottom)
            caught = tangomon_caught[zone]
            avail = len(tangomon_sets[zone])
            prog_text = "{}/{} ({}%)".format(
                caught, avail, int(100 * caught / avail))
            self.project_text(font, prog_text, x, progress_y, 0,
                              halign=sge.s.center, valign=sge.s.top)
            x += zone_distance

    def event_key_press(self, key, char):
        global player_zone

        if key == sge.s.left:
            play_sound(select_sound)
            player_zone -= 1
            player_zone %= len(ZONES)
        elif key == sge.s.right:
            play_sound(select_sound)
            player_zone += 1
            player_zone %= len(ZONES)
        elif key in {sge.s.enter, sge.s.kp_enter}:
            zone = ZONES[player_zone]
            tset = tangomon_sets[zone]

            choices = list(tset)
            for tangomon in tset:
                if tangomon not in player_tangomon:
                    # Not caught, so we give it a couple redundant
                    # entries to make encountering it more likely.
                    for i in six.moves.range(NEW_TANGOMON_REDUNDANCY):
                        choices.append(tangomon)
            tangomon = random.choice(choices)

            ect = tangomon_encountered[zone]
            music = "battle.ogg"
            if tangomon in ect:
                if ect.index(tangomon) >= len(tset) - 1:
                    music = "battle_dungeon.ogg"
            elif len(ect) == len(tset) - 1:
                music = "battle_dungeon.ogg"

            arena = Arena(tangomon, music=music)
            arena.start()
        elif key in {sge.s.escape, sge.s.space, sge.s.tab, sge.s.backspace}:
            WorldmapMenu.create()


class Arena(Room):

    """Arena where monsters fight."""

    def __init__(self, enemy, **kwargs):
        self.player = random.randrange(len(player_tangomon))
        self.enemy = enemy
        self.tangoji = None
        self.tangoji_bonus = 0
        self.callback = None
        self.test_num = 0
        super(Arena, self).__init__(**kwargs)

    def event_room_start(self):
        global player_tangomon

        super(Arena, self).event_room_start()
        self.add(gui_handler)

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

        self.pt_name = player_tangomon[self.player]
        self.player_name = get_tangomon_name(self.pt_name)
        self.player_hp = get_tangomon_hp_buffed(self.pt_name)
        self.player_base_power = get_tangomon_power_buffed(self.pt_name)
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

        self.init_tangoject(BATTLE_START_WAIT)

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

    def init_tangoject(self, wait_time=BATTLE_START_WAIT):
        global player_tangojections

        player_tangojections.sort(key=lambda d: d.get("time"))
        if (player_tangojections and
                player_tangojections[0].get("time", time.time()) <= time.time()):
            self.tangoji = player_tangojections.pop(0)
            self.alarms["init_tangoject"] = wait_time
        else:
            self.alarms["init_player_attack"] = wait_time

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
            self.tangoji.setdefault("power", TANGOJI_MULT_START)
            if self.textbox.text.lower().strip() == word.lower().strip():
                self.tangoji_bonus = self.tangoji["power"]
                self.tangoji["power"] -= TANGOJI_MULT_DECREMENT
                self.tangoji["power"] = max(self.tangoji["power"],
                                            TANGOJI_MULT_MIN)

                bulk_bonus = TANGOJI_MULT_BULK_BONUS * len(player_tangojis)
                self.tangoji_bonus += bulk_bonus

                if ("time_limit" in self.alarms and
                        self.alarms["time_limit"] > 0):
                    self.tangoji_bonus += (self.alarms["time_limit"] *
                                           TANGOJI_MULT_TIME_BONUS)
                    del self.alarms["time_limit"]
            else:
                self.tangoji["power"] += TANGOJI_MULT_DECREMENT
                self.tangoji["power"] = min(self.tangoji["power"],
                                            TANGOJI_MULT_START)
                self.tangoji_bonus = 0

            self.callback()
            self.callback = None

    def tangoject(self):
        global player_tangojis
        global player_tangojections

        self.reset_state()

        word = self.tangoji.get("word", "")
        if self.tangoji_bonus:
            self.test_num += 1
            nt = self.tangoji.setdefault("next_time", DAY)
            dev = random.uniform(-nt / 10, nt / 10)
            self.tangoji["time"] = time.time() + nt + dev
            self.tangoji["next_time"] *= 2
            player_tangojections.append(self.tangoji)
            player_tangojections.sort(key=lambda d: d.get("time"))

            if (player_tangojections and self.test_num < TEST_LIMIT and
                    player_tangojections[0].get("time", time.time()) <= time.time()):
                self.init_tangoject(TEST_WAIT)
            else:
                self.notification_text = _("You passed the test given to you by {tangomon}!").format(
                    tangomon=self.player_name)
                self.alarms["init_player_attack"] = ATTACK_INTERVAL_TIME
        else:
            self.notification_text = _("You failed the test given to you by {tangomon}! {tangomon} loses faith in you and \"{tangoji}\" is transformed back into a tangoji!").format(
                tangomon=self.player_name, tangoji=word)
            self.tangoji["power"] = TANGOJI_MULT_START
            player_tangojis.append(self.tangoji)
            self.alarms["player_lose"] = ATTACK_INTERVAL_FAIL_TIME

    def player_attack(self):
        global player_tangomon

        self.reset_state()

        word = self.tangoji.get("word", "")
        if self.tangoji_bonus:
            damage = int(self.player_base_power * self.tangoji_bonus)

            # Critical hit
            if random.random() < CRITICAL_CHANCE:
                damage *= CRITICAL_MULT
                play_sound(critical_sound)
                self.notification_text = _("{player} attacks with \"{tangoji}\", inflicting {damage} damage! It's super effective!").format(
                    player=self.player_name, tangoji=word, damage=damage)
            else:
                self.notification_text = _('{player} attacks with "{tangoji}", inflicting {damage} damage!').format(
                    player=self.player_name, tangoji=word, damage=damage)

            self.enemy_hp -= damage
            self.enemy_object.image_alpha = 128
            interval = ATTACK_INTERVAL_TIME
            play_sound(hurt_sound)
        else:
            damage = self.enemy_base_power * ENEMY_NERF
            damage += random.uniform(-damage / 10, damage / 10)
            damage = int(damage)
            self.player_hp -= damage
            self.player_object.image_alpha = 128
            interval = ATTACK_INTERVAL_FAIL_TIME
            play_sound(block_sound)
            play_sound(hurt_sound)
            self.notification_text = _("Attack failed! Correct Tangoji (\"{tangoji}\") not entered. {enemy} counterattacks, inflicting {damage} damage.").format(
                tangoji=word, enemy=self.enemy_name, damage=damage)

        if self.enemy_hp <= 0:
            self.alarms["player_win"] = interval
        elif self.player_hp <= 0:
            self.alarms["player_lose"] = interval
        else:
            self.alarms["init_player_attack"] = interval

    def use_tangokan(self):
        global player_tangomon
        global player_tangojis
        global player_tangojections

        self.reset_state()

        if self.tangoji_bonus:
            interval = ATTACK_INTERVAL_TIME
            player_tangomon.append(self.enemy)
            tangoji = self.tangoji.copy()
            wait = DAY
            tangoji["time"] = time.time() + wait
            tangoji["next_time"] = wait * 2
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
                self.reset_state()
                self.alarms = {}
                self.event_alarm("player_lose")

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
        elif alarm_id == "player_lose":
            self.player_run()
            del player_tangomon[self.player]
            self.alarms["leave_arena"] = ATTACK_INTERVAL_TIME
        elif alarm_id == "player_win":
            self.reset_state()

            tangokans = get_player_active_tangokans()
            if tangokans and (self.enemy not in player_tangomon or
                              random.random() < 0.1):
                i = random.choice(tangokans)
                self.tangoji = player_tangokans.pop(i)
                self.show_clue()
                self.callback = self.use_tangokan
                self.alarms["time_limit"] = TANGOJI_ENTRY_TIME
            else:
                self.enemy_run()
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
        elif key in {sge.s.enter, sge.s.kp_enter, sge.s.escape}:
            sge.game.start_room.start()


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
             _("View Tangoji"), _("Add Tangoji"), _("Change Tangoji"),
             _("Create Tangokan"), _("Reset Game"),
             _("Return to Title Screen")]

    def event_choose(self):
        if self.choice == 1:
            unique_tangomon = set(player_tangomon)
            my_tangomon = len(unique_tangomon)
            active_tangokans = len(get_player_active_tangokans())
            text = _("PLAYER STATISTICS\n\nName: {name}\nTotal tangomon: {tangomon}\nTangomon types: {unique_tangomon}\nActive tangoji: {tangoji}\nActive tangokans: {tangokans}\nInactive tangokans: {inactive_tangokans}\nCompletion: {completion}%").format(
                name=player_name, tangomon=len(player_tangomon),
                unique_tangomon=my_tangomon, tangoji=len(player_tangojis),
                tangokans=active_tangokans,
                inactive_tangokans=(len(player_tangokans) - active_tangokans),
                completion=int(100 * my_tangomon / len(get_all_tangomon())))

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
            add_player_tangoji()
            WorldmapMenu.create(default=self.choice)
        elif self.choice == 5:
            play_sound(confirm_sound)
            ChangeTangojiMenu.create_page()
        elif self.choice == 6:
            play_sound(confirm_sound)
            if len(player_tangojis) > TANGOJI_MIN:
                play_sound(confirm_sound)
                CreateTangokanMenu.create_page()
            else:
                msg = _("You don't have enough tangojis in reserve to make a tangokan. You can only create a tangokan if, after spending one of your tangojis to make the tangokan, you have at least {minimum} left over. You can create more tangojis with the \"Add Tangoji\" option.").format(minimum=TANGOJI_MIN)
                DialogBox(gui_handler, msg).show()
                WorldmapMenu.create(default=self.choice)
        elif self.choice == 7:
            text = _("This will only reset your location and tangomon. Are you sure?")
            buttons = [_("No"), _("Yes")]
            if xsge_gui.show_message(gui_handler, message=text, buttons=buttons):
                reset_game()
            else:
                WorldmapMenu.create(default=self.choice)
        elif self.choice == 8:
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
            word = player_tangojis[i].get("word", "???")
            clue = player_tangojis[i].get("clue", "???")
            power = player_tangojis[i].get("power", TANGOJI_MULT_START)
            text = _("{word}\n\n{clue}\n\nPower: {power}%").format(
                word=word, clue=clue, power=int(power * 100))
            DialogBox(gui_handler, text).show()
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

            WorldmapMenu.create(default=5)
        else:
            play_sound(cancel_sound)
            WorldmapMenu.create(default=5)


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
            msg = _("New tangokan created! It will activate in 2 hours. At that point, you will be able to use your tangokan to convince a new tangomon to join your team!")
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
        hp = get_tangomon_hp_buffed(iname)
        base_power = get_tangomon_power_buffed(iname)

        padding = 8

        y = padding
        name_text = _("#{position}: {tangomon}".format(
            position=(self.tangomon + 1), tangomon=name))
        name_label = xsge_gui.Label(
            self, self.width / 2, y, 10, name_text, font=font_big,
            width=(self.width - 2 * padding), halign=sge.s.center)

        y += font.get_height(name) + padding
        sprite_widget = xsge_gui.DecorativeWidget(
            self, self.width / 2 - sprite.width / 2, y, 10, sprite=sprite)

        y += sprite.height + padding
        zone = "N/A"
        for i in tangomon_sets:
            if iname in tangomon_sets[i]:
                zone = ZONE_NAMES[i]
                break
        info_text = _("Zone: {zone}\nHP: {hp}\nPower: {power}").format(
            zone=zone, hp=hp, power=int(base_power))
        info_label = xsge_gui.Label(
            self, self.width / 2, y, 10, info_text, font=font_big,
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


def get_tangomon_name(tangomon):
    return tangomon.replace("_", " ").title()


def get_all_tangomon():
    all_tangomon = set()
    for i in tangomon_sets:
        all_tangomon |= tangomon_sets[i]
    return all_tangomon


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
    for i in tangomon_sets:
        if tangomon in tangomon_sets[i]:
            d = os.path.join(DATA, "images", "tangomon", i)
            return sge.gfx.Sprite(tangomon, d)

    warnings.warn('"{}" is not a valid Tangomon.'.format(tangomon))
    return None


def evaluate_tangomon(tangomon):
    for i in tangomon_sets:
        if tangomon in tangomon_sets[i]:
            assert i in tangomon_encountered
            tangomon_encountered[i].append(tangomon)
            return

    warnings.warn('"{}" is not a valid Tangomon.'.format(tangomon))


def get_tangomon_hp_max(tangomon):
    for i in tangomon_sets:
        if tangomon in tangomon_sets[i]:
            assert i in ZONES and i in tangomon_encountered
            if tangomon not in tangomon_encountered[i]:
                tangomon_encountered[i].append(tangomon)

            j = tangomon_encountered[i].index(tangomon)
            for k in ZONES[:ZONES.index(i)]:
                j += len(tangomon_sets[i]) + ZONE_BUFFER
            return int(HEALTH_MAX_START * (HEALTH_INCREMENT_FACTOR ** j))

    warnings.warn('"{}" is not a valid Tangomon.'.format(tangomon))
    return 1


def get_tangomon_base_power(tangomon):
    for i in tangomon_sets:
        if tangomon in tangomon_sets[i]:
            assert i in ZONES and i in tangomon_encountered
            if tangomon not in tangomon_encountered[i]:
                tangomon_encountered[i].append(tangomon)

            j = tangomon_encountered[i].index(tangomon)
            for k in ZONES[:ZONES.index(i)]:
                j += len(tangomon_sets[i]) + ZONE_BUFFER
            return BASE_POWER_START * (BASE_POWER_INCREMENT_FACTOR ** j)

    warnings.warn('"{}" is not a valid Tangomon.'.format(tangomon))
    return 1


def get_tangomon_hp_buffed(tangomon):
    # HP of a player's tangomon, buffed by its peers.
    hp = get_tangomon_hp_max(tangomon)
    n = 0
    total_hp = 0
    for s in player_tangomon:
        ihp = get_tangomon_hp_max(s)
        if ihp >= hp:
            total_hp += ihp
            n += 1
    if n:
        avg_hp = int(total_hp / n)
        hp = max(hp, avg_hp)

    return hp


def get_tangomon_power_buffed(tangomon):
    # HP of a player's tangomon, buffed by its peers.
    power = get_tangomon_base_power(tangomon)
    n = 0
    total_power = 0
    for s in player_tangomon:
        ipower = get_tangomon_base_power(s)
        if ipower >= power:
            total_power += ipower
            n += 1
    if n:
        avg_power = int(total_power / n)
        power = max(power, avg_power)

    return power


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


def reset_game():
    global player_zone
    global player_tangomon
    global tangomon_encountered
    player_zone = 0
    player_tangomon = []
    tangomon_encountered = {}
    for i in ZONES:
        tangomon_encountered[i] = []
    load_map()


def new_game():
    global player_name
    global player_zone
    global player_tangojis
    global player_tangokans
    global player_tangomon
    global player_tangojections
    global tangomon_encountered
    text = _("What is your name?")
    player_name = None
    while not player_name:
        player_name = xsge_gui.get_text_entry(gui_handler, message=text)
    player_zone = 0
    player_tangojis = []
    player_tangokans = []
    player_tangomon = []
    player_tangojections = []
    tangomon_encountered = {}
    for i in ZONES:
        tangomon_encountered[i] = []
    load_map()


def save_game():
    global save_slots

    if not NOSAVE:
        if current_save_slot is not None:
            save_slots[current_save_slot] = {
                "version": 1,
                "player_name": player_name,
                "player_zone": player_zone, "player_tangojis": player_tangojis,
                "player_tangokans": player_tangokans,
                "player_tangomon": player_tangomon,
                "player_tangojections": player_tangojections,
                "tangomon_encountered": tangomon_encountered}

        write_to_disk()


def load_game():
    global player_name
    global player_zone
    global player_tangojis
    global player_tangokans
    global player_tangomon
    global player_tangojections
    global tangomon_encountered

    if (current_save_slot is not None and
            save_slots[current_save_slot] is not None):
        slot = save_slots[current_save_slot]
        player_name = slot.get("player_name")
        player_zone = slot.get("player_zone", 0)
        player_tangojis = slot.get("player_tangojis", [])
        player_tangokans = slot.get("player_tangokans", [])
        player_tangomon = slot.get("player_tangomon", [])
        player_tangojections = slot.get("player_tangojections", [])
        tangomon_encountered = {}
        for i in ZONES:
            tangomon_encountered[i] = []
        tangomon_encountered = slot.get("tangomon_encountered", tangomon_encountered)

        if slot.get("version", 0) < 1:
            tjs = list(set([(d["word"], d["clue"]) for d in player_tangojections]))
            for word, clue in tjs:
                ilist = []
                for i in six.moves.range(len(player_tangojections)):
                    if (player_tangojections[i]["word"] == word and
                            player_tangojections[i]["clue"] == clue):
                        ilist.append(i)

                assert ilist
                if len(ilist) >= 2:
                    tj1 = player_tangojections[ilist[0]]
                    tj2 = player_tangojections[ilist[1]]
                    tj1["next_time"] = tj2["time"] - tj1["time"]
                else:
                    player_tangojections[ilist[0]]["next_time"] = 36 * MONTH

                for i in reversed(ilist[1:]):
                    del player_tangojections[i]

        load_map()
    else:
        new_game()


def load_map():
    if not player_tangomon:
        zone = ZONES[0]
        if tangomon_encountered[zone]:
            player_tangomon.append(tangomon_encountered[zone][0])
        else:
            player_tangomon.append(random.choice(list(tangomon_sets[zone])))

    while len(player_tangojis) < TANGOJI_MIN:
        r = add_player_tangoji()
        if not r:
            text = _("You must add a tangoji to continue.")
            DialogBox(gui_handler, text).show()

    room = Worldmap(music="overworld.ogg")
    room.start()


def write_to_disk():
    if not NOSAVE:
        # Write our saves and settings to disk.
        cfg = {"version": 0, "first_run": first_run, "font_name": font_name,
               "fullscreen": fullscreen, "scale_method": scale_method,
               "sound_enabled": sound_enabled, "music_enabled": music_enabled,
               "fps_enabled": fps_enabled}

        with open(os.path.join(CONFIG, "config.json"), 'w') as f:
            json.dump(cfg, f, indent=4)

        with open(os.path.join(CONFIG, "save_slots.json"), 'w') as f:
            json.dump(save_slots, f, indent=4)


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
d = os.path.join(DATA, "images", "misc")
logo_sprite = sge.gfx.Sprite("logo", d, origin_x=300)

# Find tangomon
for zone in ZONES:
    tangomon_sets[zone] = set()
    d = os.path.join(DATA, "images", "tangomon", zone)
    for fname in os.listdir(d):
        root, ext = os.path.splitext(fname)
        try:
            sprite = sge.gfx.Sprite(root, d)
        except (IOError, OSError):
            pass
        else:
            tangomon_sets[zone].add(root)

# Create fonts
create_fonts()

# Load sounds
hurt_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "hurt.wav"))
block_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "block.wav"))
critical_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "critical.wav"))

select_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "select.ogg"))
confirm_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "confirm.wav"))
cancel_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "cancel.wav"))
type_sound = sge.snd.Sound(os.path.join(DATA, "sounds", "type.wav"))

# Create rooms
sge.game.start_room = TitleScreen()

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
