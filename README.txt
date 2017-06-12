This file has been dedicated to the public domain, to the extent
possible under applicable law, via CC0. See
http://creativecommons.org/publicdomain/zero/1.0/ for more
information. This file is offered as-is, without any warranty.

========================================================================


HOW TO RUN

If you have downloaded a version of Tangomon designated for a particular
system, simply run the executable.

To run the Tangomon source code, you will need the following
dependencies:

- Python 2 (2.7 or later) or 3 (3.1 or later) <http://www.python.org>
- Pygame 1.9.1 or later <http://pygame.org>
- uniseg <https://pypi.python.org/pypi/uniseg>

Once you have installed the dependencies, you can start Tangomon by
running tangomon.py. On most systems, this should be done by
double-clicking on it; if you are shown a dialog asking you if you want
to display or run the file, choose to run it.

The default Python version will be used. To use a different version of
Python, change the shebang on line 1 of tangomon.py from "python" to
"python2" or "python3" (or any other valid Python version).

There are some command-line options that can be passed. Run Tangomon in a
terminal with the "-h" command-line option for more information.


HOW TO PLAY

Use the arrow keys to move and the Enter key to select, or to open the
pause menu (where you can access all important in-game actions).

The game is simple: You start with one "tangomon" and three "tangojis".
Tangojis are what you use to attack; they are words you need to
memorize. Your tangojis can be whatever you want them to be, but the
idea is for them to be things you are trying to learn, such as
vocabulary words. Tangomon are the creatures which battle using
tangojis. You can find them by exploring the map, but not while you are
on a road or other safe area.

During a battle, you will be shown the clues to tangojis randomly
selected from your tangoji list. Type the tangoji corresponding with the
clue being shown and then press the Enter key. If you are correct, your
tangomon will successfully either attack the other tangomon, or defend
against the other tangomon's attack. The faster you enter the correct
tangoji, the more effectiveness the action will have. However, if you
are incorrect, your tangomon will be confused and not perform the
action at all.

When you defeat a tangomon, that tangomon will offer to teach you a new
tangoji. Again, you choose your tangojis if you accept their offer.
Tangojis degrade in effectiveness over time, so it is in your best
interest to learn new tangojis as much as possible.

When you have learned a tangoji, you can convert it to a "tangokan".
Tangokans are used to convince other tangomon to join your team. At the
end of a battle, if you have any active tangokans, you will be given the
opportunity to use one. You will have to correctly give the tangoji used
to create the tangokan used. If you fail, the tangokan will revert back
into a tangoji.

After using a tangokan, your tangomon will test your memory of it
several times over the course of the next several months, so make sure
you really know every tangoji you convert into a tangokan! Any failure
to pass your tangomon's test will result in that tangomon abandoning
you.

That's it! See if you can collect all types of tangomon!

If, after entering fullscreen mode, the keyboard becomes unresponsive,
you can exit the game by pressing the middle mouse button. This is a
result of a rare bug in Pygame, explained in detail here:

https://savannah.nongnu.org/forum/forum.php?forum_id=8113
