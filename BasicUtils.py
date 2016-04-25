import os
import re
import inspect

isValidPathREStr = r"""
    ^
    (?: # A path is a sequence of path words separated by slashes
        (?: # each path word must be as below
            
            # It must either be a valid folder name i.e.
            [a-zA-Z]          # must start with alphabetic character
            (?: # if it contains any other characters, they must be as below
                [a-zA-Z_0-9\-]* # must only contain alphanumeric, underscore or hypen
                [a-zA-Z0-9]     # must end in an alphanumeric character
            )? |
            # Or, it must be one of '.' and '..'
            \. |
            \.\.|
            # Or, it must be nothing ('')
        )
        (?:[\\/]|$) # and must be followed by either a separator or end
    )+
    
    $   # followed by end
"""

isValidPathRE = re.compile(isValidPathREStr,re.VERBOSE)


def getNonEmptyInput(InputPrompt):
    Input = ''
    ReceivedInput = False
    while not ReceivedInput:
        Input = input(InputPrompt)
        if Input.strip():
            ReceivedInput = True
    return Input


def debug_print(PrintString):
    print(PrintString)


def ProcessPath(Path, ExperimentTopDir, RelativetoTop=False):
    '''

    The function
        ProcessedPath = ProcessPath(Path)
    
    It processes the Path either relative to the Top Directory or the current
    working directory and returns a path relative to the Top Directory.

    '''
    
    # Get Path relative to top experiment directory
    # replace all backslash by forward slash
    # debug_print("RelativetoTop inside ProcessedPath = {0}".format(RelativetoTop))
    if RelativetoTop:
        Path = os.path.normpath(os.path.join(ExperimentTopDir, Path))
    else:
        Path = os.path.abspath(Path)
    Path = os.path.relpath(Path, ExperimentTopDir)
    Path = Path.replace("\\","/")

    if Path[0:2] == '..' or Path[0] == '/' or Path[0] == '\\':
        print((
            "The Path {ActPath} does not appear to be a subdirectory\n"
            "of the Top Level Experiment Directory {TopLevelPath}"
        ).format(ActPath=Path, TopLevelPath=ExperimentTopDir))
        Path = ''
        raise ValueError('Incorrect Path')
    else:
        return Path


def getFrameDir():
    """
    Gets the direcctory of the script calling this function.
    """
    CurrentFrameStack = inspect.stack()
    if len(CurrentFrameStack) > 1:
        ParentFrame   = CurrentFrameStack[1].frame
        FrameFileName = inspect.getframeinfo(ParentFrame).filename
        FrameDir      = os.path.dirname(os.path.abspath(FrameFileName))
    else:
        FrameDir = None

    return FrameDir

