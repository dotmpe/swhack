"""
Use this with diagnostics so that it can be changed as necessary
For example, sometimes want on stdout maybe or in a scroll window....
"""

import sys
import os

def progress(*args):
    global chatty_level  # verbosity indent level
    sys.stderr.write(" "*chatty_level)
    for a in args:
        sys.stderr.write("%s " % (a,))
    sys.stderr.write("\n")
#        sys.stderr.write(  str + "\n")

global chatty_flag # verbosity debug flag
chatty_flag  =0
chatty_flag = int(os.environ.get("CWM_VERBOSITY", 0))

global chatty_level  # verbosity indent level
chatty_level = 0

global tracking
tracking = 0  # Are we keeping reason information for proof generation?

def setTracking(x):
    global tracking
    chatty_flag = x

def setVerbosity(x):
    global chatty_flag
    chatty_flag = x

def verbosity():
    global chatty_flag
    return chatty_flag

def progressIndent(delta):
    global chatty_level
    chatty_level = chatty_level + delta
    return chatty_level
    
def printState(prefix="#trace# "):
    """Output the (caller's) function name and local variables
    """
    import sys
    frame = sys._getframe(1)    # caller's state
    sys.stderr.write(prefix+
                     str(frame.f_code.co_name)+" "+
                     str(frame.f_locals['self'])+"\n")
    for varname in frame.f_locals.keys():
        if varname == "self": continue
        sys.stderr.write("%s    %-8s: %s\n" %
                         (prefix, varname, frame.f_locals[varname]))
    sys.stderr.write(prefix+"\n")
   

