import os
import re
import RSACode as rsa
import PrettyYAMLFmt as pyf
import shlex
import textwrap

from enum import Enum

CurrentEntityData = []
ExperimentTopDir = ''

class PromptStatus(Enum):
    EXIT          = 1 << 0
    INVALID_ARG   = 1 << 1
    SUCCESS       = 1 << 2
    ITER_OVER    = 1 << 3

def debug_print(PrintString):
    print PrintString

def ProcessPath(Path, RelativetoTop=False):

    '''

    The function
        ProcessedPath = ProcessPath(Path)
    
    It processes the Path either relative to the Top Directory or the current
    working directory and returns a path relative to the Top Directory.

    '''
    # debug_print("ExperimentTopDir = {0}".format(ExperimentTopDir))
    if not ExperimentTopDir:
        print "The Top Level Directory Path has not been determined yet"
        return 0
    
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
        print (
            "The Path {ActPath} does not appear to be a subdirectory\n"
            "of the Top Level Experiment Directory {TopLevelPath}"
        ).format(ActPath=Path, TopLevelPath=ExperimentTopDir)
        Path = ''
        raise ValueError('Incorrect Path')
    else:
        return Path

def BookDirectory(Path, Type, CurrentUIDData, Force=False, RelativetoTop=False):

    Path = ProcessPath(Path,RelativetoTop=RelativetoTop)

    # debug_print("Processed Path = {ProcessedPath}".format(ProcessedPath=Path))
    # debug_print("Inside BookDirectory Function")
    for entry in CurrentUIDData:
        # debug_print(entry)

    # Find the directory if it has already been assigned a number
    ExistingDir = [
        entry
        for entry in CurrentUIDData
        if entry.Type in ['IntermediateDir', 'ExperimentDir'] and entry.Path == Path]

    if ExistingDir:
        # If Directory has already been assigned a
        ExistingDir = ExistingDir[0]
        print (
            "The directory '{DirPath}' has already been assigned the unique ID"
            "{uid:0{len}x}"
        ).format(DirPath=Path, uid=ExistingDir.ID, len=32)
    else:
        # if the parent directory is not the Top Directory
        #   check if the UID for the parent has been assigned and act
        #   appropriately.
        ParentDirPath = os.path.dirname(Path)
        ParentID = None
        ExistingParentDir = [
            entry
            for entry in CurrentUIDData
            if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                entry.Path == ParentDirPath]
        if not ExistingParentDir:
            if not Force:
                print (
                    "The Parent directory '{ParDirPath}' has not been"    "\n"
                    "assigned a UID. use Force=True in order to book an"  "\n"
                    "ID for the Parent Directory itself"
                ).format(ParDirPath=ParentDirPath)
            else:
                # debug_print("ParentDirPath={ParentDirPath}".format(ParentDirPath=ParentDirPath))
                ParentID = BookDirectory(
                    ParentDirPath, 'IntermediateDir', CurrentUIDData,
                    Force=True, RelativetoTop=True)
        else:
            ExistingParentDir = ExistingParentDir[0]
            if ExistingParentDir.Type == 'ExperimentDir':
                print (
                    "The Parent directory '{ParDirPath}' has been booked" "\n"
                    "as an experiment directory. Hence you cannot book a" "\n"
                    "subdirectory."
                ).format(ParDirPath=ParentDirPath)
            else:
                ParentID = ExistingParentDir.ID
        
        if ParentID is not None:
            # calculate the last UID
            LastCode = CurrentUIDData[-1].ID
            # decode it to get sequence number
            LastSeqNumber = rsa.RSADecode(LastCode)
            LastEntry = {}
            LastEntry['ID']       = rsa.RSAEncode(LastSeqNumber+1)
            LastEntry['ParentID'] = ParentID
            LastEntry['Type']     = Type
            LastEntry['Path']     = Path
            CurrentUIDData += [pyf.ExpRepoEntity(**LastEntry)]
            debug_print("LastEntry:\n{0}".format(pyf.ExpRepoEntity(**LastEntry)))
            return LastEntry['ID']
    return 0

def BookExperiments(Path, CurrentUIDData, NumofExps=1, Force=False, RelativetoTop=False):
    
    Path = ProcessPath(Path, RelativetoTop=RelativetoTop)
    
    # See if Path has already been assigned a UID
    ExistingDir = [
                    entry for entry in CurrentUIDData
                          if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                              entry.Path == Path]
    
    ContDirUID = None

    if not ExistingDir:
        if not Force:
            print (
                "The containing directory '{ContDirPath}' has not been "
                "assigned a UID. use Force=True in order to book an "
                "ID for the Parent Directory itself"
            ).format(ContDirPath=Path)
        else:
            ContDirUID = BookDirectory(
                Path, 'ExperimentDir', CurrentUIDData, Force=True, RelativetoTop=True)
    else:
        ExistingDir = ExistingDir[0]
        if ExistingDir.Type == 'IntermediateDir':
            print (
                "The containing directory '{ContDirPath}' has been booked" "\n"
                "as an intermediate directory. Hence you cannot book experiments" "\n"
                "directly under this directory"
            ).format(ContDirPath=Path)
        else:
            ContDirUID = ExistingDir.ID

    # If the folder is defined and has been assigned a UID

    if ContDirUID is not None:
        # Get the Last UID
        LastUID = CurrentUIDData[-1].ID
        # decode it to get sequence number
        LastSeqNumber = rsa.RSADecode(LastUID)
        AddedIDs = []
        
        for i in range(1,NumofExps+1):
            LastEntry = {}
            LastEntry['ID']       = rsa.RSAEncode(LastSeqNumber+i)
            LastEntry['ParentID'] = ContDirUID
            LastEntry['Type']     = 'Experiment'
            LastEntry['Path']     = Path
            CurrentUIDData       += [pyf.ExpRepoEntity(**LastEntry)]
            AddedIDs             += [LastEntry['ID']]
        
        return AddedIDs

    return []

def FlushEntityData():
    """
        This writes the current Entity Data into EntityData.yml
    """
    with open('EntityData.yml', 'w') as Fout:
        CurrentDumpMap = {}
        if CurrentEntityData:
            CurrentDumpMap['EntityData'] = CurrentEntityData

        pyf.PrettyYAMLDump(CurrentDumpMap, Fout)

def BookDirectoryPrompt():
    
    print textwrap.dedent("""\
        You Are currenty BOOKING A DIRECTORY, The following is the format
        of the expected input:
        
          [Path] [--inter] [--force] [--reltop] [--noconf] [--exit]
        
        Here, The options are:
        
          --inter  -- This forces the given directory to be booked as an inter-
                      mediate directory as opposed to an experiment directory
                      (which is the default)
        
          --force  -- Enable Forced Booking (i.e. book IDs for all subdirectories
                      leading to the final directory if they havent been previously
                      booked
        
          --reltop -- Indicates that the path mentioned is not relative to the
                      current working directory, but rather, the path relative to
                      the base of the repository

          --noconf -- This option instructs the program to not request for conf-
                      irmation of input.
          
          --exit   -- This Argument, if specified, causes exit from the console
                      and transfers control back to the main menu. None of the
                      other inputs including [Path] have any effect in this case
        """)
    
    Status = PromptStatus.SUCCESS
    while (Status != PromptStatus.EXIT):
        
        Status = PromptStatus.SUCCESS
        
        ConsoleIn = raw_input(">> ")
        Args = shlex.split(ConsoleIn)

        if Args[0] == '--exit':
            Status = PromptStatus.EXIT
        else:
            Path = Args[0]
        
        Force = False
        RelativetoTop = False
        Type = 'ExperimentDir'
        NeedConf = True

        if Status == PromptStatus.SUCCESS:
            for arg in Args[1::]:
                if arg == '--force':
                    Force = True
                elif arg == '--reltop':
                    RelativetoTop = True
                elif arg == '--inter':
                    Type = 'IntermediateDir'
                elif arg == '--noconf':
                    NeedConf = False
                elif arg == '--exit':
                    Status = PromptStatus.EXIT
                    break
                else:
                    print "Invalid Option {Arg}\n".format(Arg=arg)
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            print "Please confirm your input (confirm: capital Y, not confirm: anything else)"
            print "  "
            print "  Path          : {Path}\n".format(Path=Path)
            print "  Type          : {Type}\n".format(Type=Type)
            print "  Force         : {Force}".format(Force=Force)
            print "  RelativetoTop : {RelTop}".format(RelTop=RelativetoTop)
            print "  "
            Confirmation = raw_input(">> ")
            if Confirmation == 'Y':
                Status = PromptStatus.SUCCESS
            else:
                print "Booking Cancelled"
                Status = PromptStatus.ITER_OVER

        if Status == PromptStatus.SUCCESS:
            try:
                UID = BookDirectory(
                    Path, Type, CurrentEntityData, Force=Force, RelativetoTop=RelativetoTop)
            except ValueError:
                print "It appears as though the directory was invalid\n"
                Status = PromptStatus.EXIT
            if UID != 0:
                print "The following booking was successful:\n"
                print "  ID  : {UID:0{len}x}".format(UID=UID,len=32)
                print "  Path: {Path}\n".format(Path=Path)
                print "  Type: {Type}\n".format(Type=Type)
            else:
                print "The following booking was unsuccessful\n"
                print "  Path: {Path}".format(Path=Path)
                Status = PromptStatus.INVALID_ARG
    
    FlushEntityData()
    return PromptStatus.SUCCESS

def BookExperimentsPrompt():
    
    print textwrap.dedent("""\
        You Are currenty BOOKING A DIRECTORY, The following is the format
        of the expected input:
        
          [Experiment Dir Path] [N] [--force] [--reltop] [--noconf] [--exit]
        
        Here, The options are:
          
          N        -- The number of experiments that you wish to book within the
                      current contining path
          
          --force  -- Enable Forced Booking (i.e. book IDs for all subdirectories
                      leading to the final directory if they havent been previously
                      booked
          
          --reltop -- Indicates that the path mentioned is not relative to the
                      current working directory, but rather, the path relative to
                      the base of the repository
          
          --noconf -- This option instructs the program to not request for conf-
                      irmation of input.
          
          --exit   -- This Argument, if specified, causes exit from the console
                      and transfers control back to the main menu. None of the
                      other inputs including [Path] have any effect in this case
        """)
    
    Status = PromptStatus.SUCCESS
    while (Status != PromptStatus.EXIT):
        
        Status = PromptStatus.SUCCESS
        
        ConsoleIn = raw_input(">> ")
        Args = shlex.split(ConsoleIn)

        if Args[0] == '--exit':
            Status = PromptStatus.EXIT
        else:
            Path = Args[0]
        
        Force = False
        RelativetoTop = False
        NeedConf = True
        NumofExps = 1
        IsNum = re.compile(r"^\d+$")

        if Status == PromptStatus.SUCCESS:
            for arg in Args[1::]:
                if IsNum.match(arg):
                    NumofExps = int(arg)
                elif arg == '--force':
                    Force = True
                elif arg == '--reltop':
                    RelativetoTop = True
                elif arg == '--noconf':
                    NeedConf = False
                elif arg == '--exit':
                    Status = PromptStatus.EXIT
                    break
                else:
                    print "Invalid Option {Arg}\n".format(Arg=arg)
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            print "Please confirm your input (confirm: capital Y, not confirm: anything else)"
            print "  "
            print "  Path            : {Path}\n".format(Path=Path)
            print "  Num of Experims : {NumofExps}\n".format(NumofExps=NumofExps)
            print "  Force           : {Force}".format(Force=Force)
            print "  RelativetoTop   : {RelTop}".format(RelTop=RelativetoTop)
            print "  "
            Confirmation = raw_input(">> ")
            if Confirmation == 'Y':
                Status = PromptStatus.SUCCESS
            else:
                print "Booking Cancelled"
                Status = PromptStatus.ITER_OVER

        if Status == PromptStatus.SUCCESS:
            try:
                UIDs = BookExperiments(
                    Path, CurrentEntityData, NumofExps, Force=Force, RelativetoTop=RelativetoTop)
            except ValueError:
                print "It appears as though the directory was invalid\n"
                Status = PromptStatus.EXIT
            if UIDs:
                print "The following bookings were successful:\n"
                print "  Path: {Path}\n".format(Path=Path)
                print "Experiments Booked (UIDs):\n"
                for i in range(0, len(UIDs)):
                    print "  {Ind:{BulletW}}. ID  : {UID:0{len}x}".format(
                        Ind=i+1, BulletW=4, UID=UIDs[i],len=32)
            else:
                print "The following booking was unsuccessful\n"
                print "  Path: {Path}".format(Path=Path)
                Status = PromptStatus.INVALID_ARG
    
    FlushEntityData()
    return PromptStatus.SUCCESS

def ExitPrompt():
    print "Are you sure you wanna exit? (capital Y/anything else):"
    Confirmation = raw_input(">> ")
    while(True):
        if Confirmation == 'Y':
            return PromptStatus.EXIT
        else:
            return PromptStatus.ITER_OVER

def RunInteractivePrompt():
    
    print "What Would you like to do?"
    print "  "
    print "  1. Book a directory"
    print "  2. Book Experiments"
    print "  3. Exit"
    print ""
    
    Status = PromptStatus.SUCCESS
    while Status != PromptStatus.EXIT:
        Option = input("Enter Your Choice: ")
        print Option
        if Option == 1:
            Status = BookDirectoryPrompt()
        elif Option == 2:
            Status = BookExperimentsPrompt()
        elif Option == 3:
            Status = ExitPrompt()
        else:
            print "Incorrect Option, Enter again\n"
            Status = PromptStatus.INVALID_ARG

def getTopLevelExpDir():
    CurrDir = os.getcwd()
    PrevDirwasRoot = False
    while (not PrevDirwasRoot):
        print "CurrDir: {CurrDir}".format(CurrDir=CurrDir)
        if os.path.isfile(os.path.join(CurrDir, 'EXP_TOP_LEVEL_DIR.indic')):
            return CurrDir

        NewDir = os.path.normpath(os.path.join(CurrDir, '..'))
        PrevDirwasRoot = (NewDir == CurrDir)
        CurrDir = NewDir
    else:
        print (
            "The current working directory '{CWD}' is not inside the"
            " experiment repository and hence the top directory of the"
            " Experiment repository cannot be calculated")
        return ''

def InitialOps():
    
    # find the Top Level Experiment Directory
    global ExperimentTopDir
    global CurrentEntityData

    ExperimentTopDir = getTopLevelExpDir()
    print ExperimentTopDir
    if ExperimentTopDir:
        # read the YAML File
        with open('EntityData.yml', 'r') as Fin:
            CurrentEntityData = pyf.yaml.safe_load(Fin)
        
        if 'EntityData' in CurrentEntityData.keys():
            CurrentEntityData = CurrentEntityData['EntityData']
            CurrentEntityData = [pyf.ExpRepoEntity(**x) for x in CurrentEntityData]
        else:
            CurrentEntityData = []
        
        print CurrentEntityData[0]
        print pyf.PrettyYAMLDump(CurrentEntityData)
        RunInteractivePrompt()

InitialOps()
