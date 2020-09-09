This file has been dedicated to the public domain, to the extent
possible under applicable law, via CC0. See
http://creativecommons.org/publicdomain/zero/1.0/ for more
information. This file is offered as-is, without any warranty.

========================================================================


HOW TO RUN

If you have downloaded a version of the game designated for a particular
system, simply run the executable.

To run the source code, you will need Python 3.6 or later
<https://www.python.org>. You will also need the dependencies listed in
requirements.txt, which you can install automatically by using the
following command:

    python3 -m pip install -r requirements.txt

Once you have installed the dependencies, you can start the game by
running "tangomon.py". On most systems, this should be done by
double-clicking on it; if you are shown a dialog asking you if you want
to display or run the file, choose to run it.

There are some command-line options that can be passed. Run the game in
a terminal with the "-h" command-line option for more information.


HOW TO PLAY

Use the arrow keys to move and the Enter key to select, or to open the
pause menu (where you can access all important in-game actions).  In the
zone selection screen, press Space to start a battle.

This is a simple, fun learning game where you control your learning. It
was designed with vocabulary in mind, but it can be played with any
other information you wish to memorize: phone numbers, produce codes,
mathematical equations, names, and much more. The sky is the limit.

This is a monster battling game centered around what are called
"tangomon" and "tangojis". You start with one tangomon and three
tangojis.

Tangojis are what you use to attack; they are words you need to
memorize. Your tangojis can be whatever you want them to be, but the
idea is for them to be things you are trying to learn, such as
vocabulary words. Add new tangojis with the "Add Tangoji" option in the
pause menu (accessed by pressing Enter). You can have as many tangojis
at one time as you like (down to a minimum of 3). Tangojis degrade in
effectiveness over time as you successfully use them, so it is in your
best interest to learn new tangojis as much as possible. This is also
ideal from a learning perspective.

Tangomon are the creatures which battle using tangojis. You can battle
a tangomon by entering any of the areas shown in the area selection
screen; do this by pressing the Enter key. Below each area, you will
find an indication of how many types of tangomon exist in that area, and
how many of those types you have. Areas further to the right are home to
stronger and stronger tangomon, so do keep that in mind!

During a battle, you will be shown the clues to tangojis randomly
selected from your tangoji list. Type the tangoji corresponding with the
clue being shown and then press the Enter key. If you are correct, your
tangomon will successfully either attack the other tangomon, or defend
against the other tangomon's attack. The faster you enter the correct
tangoji, the more effectiveness the action will have. However, if you
are incorrect, your tangomon will be confused and not perform the
action at all.

Please note that if you run from a battle, your currently battling
tangomon will run away from you. This will also happen if you quit the
game in the middle of a battle.

When you have learned a tangoji, you can convert it to a "tangokan" via
the menu in the map screen accessed by the Escape key. Tangokans are
used to convince other tangomon to join your team. At the end of a
battle, one of your active tangokans may activate. When this happens,
you have to correctly give the tangoji used to create it. If you fail,
the tangokan will revert back into a tangoji.

After using a tangokan, your tangomon will periodically test your memory
of it, so make sure you really know every tangoji you convert into a
tangokan! Any failure to pass your tangomon's test will result in that
tangomon abandoning you and the old tangoji being added back into your
current tangoji list. The interval at which you are tested degrades
exponentially over time.

At any point, you can check your progress by choosing the "View
Statistics" option in the pause menu.

The game does not have an ending. Your goal is to collect all types of
tangomon. If you have successfully collected all tangomon, or if you
just want to start over, you can reset your position and tangomon while
keeping your current tangojis and tangokans via the "Reset Game" option
in the menu.

If, after entering fullscreen mode, the keyboard becomes unresponsive,
you can exit the game by pressing the middle mouse button. This is a
result of a rare bug in SDL 1.2.
