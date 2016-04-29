# This module basically defines a subsystem inside which the program is contained.
# this is a subsystem basically in the sense of the output streams
# we define multiple output streams which form a wrapper around sys.stdout.
# thy play a crucial role in allowing redirection

# Note that if there are any modules that modify sys.stdout (e.g. colorama)
# then these streams have to be initialized after the modification

import sys


stdout = sys.stdout
stderr = sys.stderr
stdcon = sys.stdout
stdin  = sys.stdin


def init():
    global stdout
    global stderr
    global stdcon
    global stdin

    stdout = sys.stdout
    stderr = sys.stderr
    stdcon = sys.stdout
    stdin  = sys.stdin
