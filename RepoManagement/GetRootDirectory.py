import os
from RepoManagement.BasicUtils import errprint


def getRootDirectory(CurrentDirectory=None):
    # Check if the current folder has EntityData.yml
    # if not keep going up until you find EntityData.yml
    # if you do then read the path and declare it as top directory.
    # else if you reach the root return error saying that current directory
    # is not in any managed experiment repository
    #
    # Note that this is NOT linked to any particular experiment repository via
    # the configuration settings. It applies to any directory specified as a
    # CurrentDirectory
    #
    # It basically returns the path of the first subdirectory that contains a
    # file named EntityData.yml

    if not CurrentDirectory:
        CurrentDirectory = os.getcwd()
    else:
        CurrentDirectory = os.path.abspath(CurrentDirectory)

    PrevDirectoryTemp = None
    CurrentDirectoryTemp = CurrentDirectory
    ContainsEntityData = False
    ReachedRoot = False
    while not ContainsEntityData and not ReachedRoot:
        if PrevDirectoryTemp == CurrentDirectoryTemp:
            ReachedRoot = True
        EntityDataPath = os.path.join(CurrentDirectoryTemp, 'EnityData.yml')
        ContainsEntityData = os.path.isfile(os.path.join(CurrentDirectoryTemp, EntityDataPath))
        PrevDirectoryTemp = CurrentDirectoryTemp
        CurrentDirectoryTemp = os.path.normpath(os.path.join(CurrentDirectoryTemp, '..'))
    
    if not ContainsEntityData:
        errprint("\nThe Following Directory:")
        errprint("")
        errprint("  {CurrentDir}".format(CurrentDir=CurrentDirectory))
        errprint("\nIs not a subdirectory of any managed experiment repository")
    else:
        return PrevDirectoryTemp
