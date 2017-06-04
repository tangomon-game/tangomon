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
- Pygame 1.9.1 or later <http://pygame.org/download.shtml>

Once you have installed the dependencies, you can start Tangomon by
running tangomon.py. On most systems, this should be done by
double-clicking on it; if you are shown a dialog asking you if you want
to display or run the file, choose to run it.

Python 2 will be used by default. To run Tangomon with Python 3 instead,
you can either change the shebang on line 1 from "python2" to "python3",
or explicitly run the Python 3 executable, e.g. with
"python3 tangomon.py" (the exact command may be different depending on
your system).

There are some command-line options that can be passed. Run Tangomon in a
terminal with the "-h" command-line option for more information.


HOW TO PLAY

Use the arrow keys to move and the Enter key to select, or to open the
pause menu.

The game is simple: You start with one "tangomon" and three "tangojis".
Tangojis are what you use to attack; they are words you need to
memorize. Your tangojis can be whatever you want them to be, but the
idea is for them to be things you are trying to learn, such as
vocabulary words. Tangomon are the creatures which battle using
tangojis. You can find them by exploring the map, but not while you are
on a road or in a town.

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
