import os
import re
import RSACode as rsa
import PrettyYAMLFmt as pyf
import shlex
import textwrap
import copy
from git import Repo, remote
import git
from collections import Counter

from enum import Enum

CurrentEntityData = []
CurrentNumberBooked = 0
NewEntityData = []

ExperimentTopDir = ''


class PromptStatus(Enum):
    EXIT          = 1 << 0
    INVALID_ARG   = 1 << 1
    SUCCESS       = 1 << 2
    ITER_OVER     = 1 << 3


def debug_print(PrintString):
    print(PrintString)


def ProcessPath(Path, RelativetoTop=False):
    '''

    The function
        ProcessedPath = ProcessPath(Path)
    
    It processes the Path either relative to the Top Directory or the current
    working directory and returns a path relative to the Top Directory.

    '''

    # debug_print("ExperimentTopDir = {0}".format(ExperimentTopDir))
    if not ExperimentTopDir:
        print("The Top Level Directory Path has not been determined yet")
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
        print((
            "The Path {ActPath} does not appear to be a subdirectory\n"
            "of the Top Level Experiment Directory {TopLevelPath}"
        ).format(ActPath=Path, TopLevelPath=ExperimentTopDir))
        Path = ''
        raise ValueError('Incorrect Path')
    else:
        return Path


def UnBookEntity(Entities2Unbook, NewUIDData=None):
    '''
    Function Definition:

        RemoveEntity(Entities2Unbook, NewUIDData=None):
    '''

    if NewUIDData is None:
        NewUIDData = NewEntityData

    Entities2Unbook = Counter([(x.Path, x.Type) for x in Entities2Unbook])
    
    for Entity in NewUIDData:
        EntityIdentTuple = (Entity.Path, Entity.Type)
        if Entities2Unbook[EntityIdentTuple]:
            # in this case, The entity is identified by its path
            Entities2Unbook[EntityIdentTuple] -= 1
            Entity.Path = '$null'

    for EntityInfo in sorted(Entities2Unbook.elements()):
        print("('{0}', '{1}') does not correspond to any remaining booked entity.".format(EntityInfo[0], EntityInfo[1]))

    # recreate array by mutating object instead of creating a new object
    # observe the [:]
    NewUIDData[:] = [Entity for Entity in NewUIDData if Entity.Path != '$null']


def BookDirectory(Path, Type,
                  NewUIDData=None, CurrentUIDData=None,
                  Force=False, RelativetoTop=False):

    global NewEntityData
    global CurrentEntityData
    if NewUIDData is None:
        NewUIDData = NewEntityData
    if CurrentUIDData is None:
        CurrentUIDData = CurrentEntityData

    Path = ProcessPath(Path,RelativetoTop=RelativetoTop)

    # debug_print("Processed Path = {ProcessedPath}".format(ProcessedPath=Path))
    # debug_print("Inside BookDirectory Function")
    # for entry in CurrentUIDData:
    #     debug_print(entry)

    BookingSuccessful = False
    ParentisBooked = False

    # Find the directory if it has already been booked
    ExistingDir = [
        entry
        for entry in CurrentUIDData + NewUIDData
        if entry.Type in ['IntermediateDir', 'ExperimentDir'] and entry.Path == Path]

    if ExistingDir:
        # If Directory has already been assigned UID
        ExistingDir = ExistingDir[0]
        UIDString = "{uid:0{len}x}".format(ExistingDir.ID, 32) if ExistingDir.ID else "UnConfirmed"

        print((
            "The directory '{DirPath}' has already been booked\n"
            "   UID : {UIDStr}"
        ).format(DirPath=Path, UIDStr=UIDString))
    else:
        # if the parent directory is not the Top Directory
        #   check if the UID for the parent has been assigned and act
        #   appropriately.
        ParentDirPath = os.path.dirname(Path)

        ExistingParentDir = [
            entry
            for entry in CurrentUIDData + NewUIDData
            if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                entry.Path == ParentDirPath]

        if not ExistingParentDir:
            if not Force:
                print((
                    "The Parent directory '{ParDirPath}' has not been"    "\n"
                    "booked. use Force=True in order to book an"  "\n"
                    "ID for the Parent Directory itself"
                ).format(ParDirPath=ParentDirPath))
            else:
                # debug_print("ParentDirPath={ParentDirPath}".format(ParentDirPath=ParentDirPath))
                ParentisBooked = BookDirectory(
                    ParentDirPath, 'IntermediateDir', Force=True, RelativetoTop=True)
        else:
            ExistingParentDir = ExistingParentDir[0]
            if ExistingParentDir.Type == 'ExperimentDir':
                print((
                    "The Parent directory '{ParDirPath}' has been booked" "\n"
                    "as an experiment directory. Hence you cannot book a" "\n"
                    "subdirectory."
                ).format(ParDirPath=ParentDirPath))
            else:
                ParentisBooked = True
        
        if ParentisBooked:
            
            # Validate The Current Directory name
            PathBaseName = os.path.basename(Path)
            isNameValid = True
            if re.match(r"^[a-zA-Z]((\w|\-)(?!$))*[a-zA-z0-9]?$", PathBaseName) is None:
                print(("The Directory Name {0} is not a valid name.\n"
                       "A valid Name must start with an alphabet,\n"
                       "contain only the characters [-_a-zA-Z0-9],\n"
                       "and end with an alphanumeric character").format(PathBaseName))
                isNameValid = False

            # In add the given path and entity into the NewEntityData
            if isNameValid:
                LastEntry = {}
                LastEntry['ID']       = 0
                LastEntry['ParentID'] = 0
                LastEntry['Type']     = Type
                LastEntry['Path']     = Path
                NewUIDData += [pyf.ExpRepoEntity(**LastEntry)]
                BookingSuccessful = True

    return BookingSuccessful


def UnBookDirectory(Path,
                    NewUIDData=None, CurrentUIDData=None,
                    Force=False, RelativetoTop=False):
    
    global NewEntityData
    global CurrentEntityData
    if NewUIDData is None:
        NewUIDData = NewEntityData
    if CurrentUIDData is None:
        CurrentUIDData = CurrentEntityData
    
    Path = ProcessPath(Path, RelativetoTop=RelativetoTop)

    def isAnc(AncPath, OtherPath):
        AncPath   = os.path.normpath(AncPath)
        OtherPath = os.path.normpath(OtherPath)
        return os.path.commonpath([AncPath, OtherPath]) == AncPath
    CurrPathEntities = [Entity for Entity in NewUIDData if isAnc(Path, Entity.Path)]

    if len(CurrPathEntities) > 1 and not Force:
            print((
                "The Specified directory '{ParDirPath}' has children"     "\n"
                "that have been assigned a UID. use Force=True in order"  "\n"
                "to un-book the directory and all its children/subdirs"
            ).format(ParDirPath=Path))
            UnbookStatus = 0
    elif len(CurrPathEntities) > 0:
        UnBookEntity(CurrPathEntities)
        UnbookStatus = 1
    else:
        print((
                "The Specified directory '{ParDirPath}' has not been"     "\n"
                "booked in this session"                                  "\n"
            ).format(ParDirPath=Path))
        UnbookStatus = 0
    return UnbookStatus


def UnBookExperiments(Path, NumofExps=None,
                      NewUIDData=None, CurrentUIDData=None,
                      RelativetoTop=False):
    
    global NewEntityData
    global CurrentEntityData
    if NewUIDData is None:
        NewUIDData = NewEntityData
    if CurrentUIDData is None:
        CurrentUIDData = CurrentEntityData
    
    Path = ProcessPath(Path, RelativetoTop=RelativetoTop)
    CurrPathExps = [Entity for Entity in NewUIDData
                    if Entity.Type == 'Experiment' and Path == Entity.Path]
    
    # assigning NumofExps
    if NumofExps is None:
        NumofExps = len(CurrPathExps)
    elif NumofExps > len(CurrPathExps):
        print((
            "The number of experiments to be deleted ({0}) exceeds the \n"
            "total number of experiments with specified path ({1}).\n"
            "Truncating the number accordingly.\n"
            ).format(NumofExps, len(CurrPathExps)))
        NumofExps = len(CurrPathExps)

    if len(CurrPathExps) > 0:
        UnBookEntity(CurrPathExps[0:NumofExps])
        DeleteStatus = 1
    else:
        print((
            "The given path has either not been booked, or has no experiments" "\n"
            "booked under it." "\n"
            ).format(NumofExps, len(CurrPathExps)))
        DeleteStatus = 0
    return DeleteStatus


def BookExperiments(
    Path, NumofExps=1,
    NewUIDData=None, CurrentUIDData=None,
    Force=False, RelativetoTop=False):

    global NewEntityData
    global CurrentEntityData
    if NewUIDData is None:
        NewUIDData = NewEntityData
    if CurrentUIDData is None:
        CurrentUIDData = CurrentEntityData
    
    Path = ProcessPath(Path, RelativetoTop=RelativetoTop)
    
    # See if Path has already been assigned a UID
    ExistingDir = [
                    entry for entry in CurrentUIDData+NewUIDData
                          if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                              entry.Path == Path]
    
    ContDirisBooked = False
    BookingSuccessful = False

    if not ExistingDir:
        if not Force:
            print((
                "The containing directory '{ContDirPath}' has not been "
                "assigned a UID. use Force=True in order to book an "
                "ID for the Parent Directory itself"
            ).format(ContDirPath=Path))
        else:
            ContDirisBooked = BookDirectory(
                Path, 'ExperimentDir', Force=True, RelativetoTop=True)
    else:
        ExistingDir = ExistingDir[0]
        if ExistingDir.Type == 'IntermediateDir':
            print((
                "The containing directory '{ContDirPath}' has been booked" "\n"
                "as an intermediate directory. Hence you cannot book experiments" "\n"
                "directly under this directory"
            ).format(ContDirPath=Path))
        else:
            ContDirisBooked = True

    # If the folder has been booked
    if ContDirisBooked:
        for i in range(1,NumofExps+1):
            LastEntry = {}
            LastEntry['ID']       = 0
            LastEntry['ParentID'] = 0
            LastEntry['Type']     = 'Experiment'
            LastEntry['Path']     = Path
            NewUIDData           += [pyf.ExpRepoEntity(**LastEntry)]

        BookingSuccessful = True

    return BookingSuccessful


def ListSessionBookings(NewUIDData=None):
    if NewUIDData is None:
        NewUIDData = NewEntityData

    SortedUIDData = sorted(
        NewUIDData,
        key=lambda x: (
            x.Path,
            (0 if x.Type in ['IntermediateDir','ExperimentDir'] else 1)
            )
        )

    # for each entity, split its path.
    SplitSortedUID = [re.split(r"[\\/]", Entity.Path) for Entity in SortedUIDData]

    # for each entity, do the following
    #   If it is a directory,
    #     search depthwise for the longest matching set of keys.
    #     once a match fails, add the remaining part of the path as a key
    #   If it is an experiment,
    #     search depthwise for the match of its entire path:
    #     Finally, add a subkey NumberofExps: and increment its value
    
    DisplayDict = {}
    for Ent, SplitEntPath in zip(SortedUIDData, SplitSortedUID):
        if Ent.Type in ['IntermediateDir', 'ExperimentDir']:
            CurrentSubDict = DisplayDict
            for PartPath in SplitEntPath:
                if PartPath not in CurrentSubDict:
                    CurrentSubDict[PartPath] = {}
                CurrentSubDict = CurrentSubDict[PartPath]
            if Ent.Type == 'ExperimentDir':
                CurrentSubDict['NumofExps'] = 0
        else:
            # Here Path MUST exist else dragons
            CurrentSubDict = DisplayDict
            for PartPath in SplitEntPath:
                CurrentSubDict = CurrentSubDict[PartPath]
            CurrentSubDict['NumofExps'] += 1
    
    print(pyf.PrettyYAMLDump(DisplayDict).
          replace(':','/').
          replace('  ','   ').
          replace('NumofExps/', 'NumofExps'))


def FlushEntityData(Stream=None, CurrentEntData=None, NewEntData=None):
    """
        This writes the current Entity Data into EntityData.yml
    """
    if CurrentEntData is None:
        CurrentEntData = CurrentEntityData
    if NewEntData is None:
        NewEntData = NewEntityData

    with Stream if Stream else open('EntityData.yml', 'w') as Fout:
        CurrentDumpMap = {}
        if CurrentEntData:
            CurrentDumpMap['EntityData'] = CurrentEntData
        if NewEntData:
            CurrentDumpMap['NewEntityData'] = NewEntData

        pyf.PrettyYAMLDump(CurrentDumpMap, Fout)


def BookDirectoryPrompt():
    
    print(textwrap.dedent("""\
        You Are currenty BOOKING A DIRECTORY, The following is the format
        of the expected input:
        
          [Path] [--inter] [--force] [--reltop] [--unbook|--unb] [--noconf] [--exit]
        
        Here, The options are:
          
          --inter  -- This forces the given directory to be booked as an inter-
                      mediate directory as opposed to an experiment directory
                      (which is the default)
          
          --force  -- Enable Forced Booking (i.e. book IDs for all subdirectories
                      leading to the final directory if they havent been previously
                      booked.
          
                      In case of deletion (--unbook), deletion of the entry of a
                      directory whose children also have their UIDs booked is
                      performed iff this option is specified. In this case, the
                      Entity Data for all of its children will be deleted too.
          
          --reltop -- Indicates that the path mentioned is not relative to the
                      current working directory, but rather, the path relative to
                      the base of the repository
          
          --noconf -- This option instructs the program to not request for conf-
                      irmation of input.
          
          --unbook -- This conveys that the given directory is selected for deletion.
                      Note that this deletion is only applicable to a booking that
                      hasnt been confirmed yet. (i.e. that done in current session)
                      This ignores the option --inter. See the behaviour of --force
                      for this case.
          
          --exit   -- This Argument, if specified, causes exit from the console
                      and transfers control back to the main menu. None of the
                      other inputs including [Path] have any effect in this case
        """))
    
    Status = PromptStatus.SUCCESS
    while (Status != PromptStatus.EXIT):
        
        Status = PromptStatus.SUCCESS
        
        # ConsoleIn = ''
        ConsoleIn = input(">> ")
        Args = shlex.split(ConsoleIn)

        if len(Args) > 0:
            if Args[0] == '--exit':
                Status = PromptStatus.EXIT
            else:
                Path = Args[0]
        else:
            Status = PromptStatus.ITER_OVER
        
        Force = False
        RelativetoTop = False
        Type = 'ExperimentDir'
        NeedConf = True
        Action = 'Book Directory'

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
                elif arg in ['--unbook', '--unb']:
                    Action = 'UNBOOK Directory'
                elif arg == '--exit':
                    Status = PromptStatus.EXIT
                    break
                else:
                    print("Invalid Option {Arg}\n".format(Arg=arg))
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            print(textwrap.dedent(("""
                Please confirm your input (confirm: capital Y, not confirm: anything else)

                  Path          : {Path}
                  Type          : {Type}

                  Action        : {Action}

                  Force         : {Force}
                  RelativetoTop : {RelTop}

                """).format(Action=Action,Path=Path,Type=Type,Force=Force,RelTop=RelativetoTop)))
            Confirmation = ''
            ReceivedConfirmation = False
            while not ReceivedConfirmation:
                Confirmation = input(">> ")
                if Confirmation:
                    ReceivedConfirmation = True
                    if Confirmation == 'Y':
                        Status = PromptStatus.SUCCESS
                    else:
                        print("Booking Cancelled")
                        Status = PromptStatus.ITER_OVER

        if Status == PromptStatus.SUCCESS:
            try:
                if Action == 'Book Directory':
                    UID = BookDirectory(Path, Type, Force=Force, RelativetoTop=RelativetoTop)
                else:
                    DeleteStatus = UnBookDirectory(Path, Force=Force, RelativetoTop=RelativetoTop)
            except ValueError:
                print("It appears as though the directory was invalid\n")
                Status = PromptStatus.INVALID_ARG
                UID = 0
                DeleteStatus = 0

            if Action == 'Book Directory':
                if UID != 0:
                    print("The following booking was successful:\n")
                    print("  Path: {Path}\n".format(Path=Path))
                    print("  Type: {Type}\n".format(Type=Type))
                else:
                    print("The following booking was unsuccessful\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  Type: {Type}\n".format(Type=Type))
                    Status = PromptStatus.INVALID_ARG
            else:
                if DeleteStatus:
                    print("The following path (and children) were successfully unbooked:\n")
                    print("  Path: {Path}\n".format(Path=Path))
                else:
                    print("The following un-booking was unsuccessful\n")
                    print("  Path: {Path}".format(Path=Path))
                    Status = PromptStatus.INVALID_ARG
    
    return PromptStatus.SUCCESS


def BookExperimentsPrompt():
    
    print(textwrap.dedent("""\
        You Are currenty BOOKING A DIRECTORY, The following is the format
        of the expected input:
        
          [Experiment Dir Path] [N] [--force] [--reltop] [--noconf] [--unbook] [--exit]
        
        Here, The options are:
          
          N        -- The number of experiments that you wish to book/unbook within
                      the current contining path. when unspecified, it defaults to 1
                      in case of booking and to 'all' in case of unbooking.
          
          --force  -- Enable Forced Booking (i.e. book IDs for all subdirectories
                      leading to the final directory if they havent been previously
                      booked)
          
          --reltop -- Indicates that the path mentioned is not relative to the
                      current working directory, but rather, the path relative to
                      the base of the repository

          --noconf -- This option instructs the program to not request for conf-
                      irmation of input.
          
          --unbook -- This conveys that the given parameters are to perform an
                      unbooking for the experiments in the current directory. Note
                      that this deletion is only applicable to a booking that hasnt
                      been confirmed yet (i.e. that done in current session).
          
          --exit   -- This Argument, if specified, causes exit from the console
                      and transfers control back to the main menu. None of the
                      other inputs including [Path] have any effect in this case
        """))
    
    Status = PromptStatus.SUCCESS
    while (Status != PromptStatus.EXIT):
        
        Status = PromptStatus.SUCCESS
        
        ConsoleIn = input(">> ")
        Args = shlex.split(ConsoleIn)

        if Args:
            if Args[0] == '--exit':
                Status = PromptStatus.EXIT
            else:
                Path = Args[0]
        else:
            Status = PromptStatus.ITER_OVER

        Force = False
        RelativetoTop = False
        NeedConf = True
        NumofExps = None
        Action = 'Book Experiments'
        IsNum = re.compile(r"^\d+$")

        if Status == PromptStatus.SUCCESS:
            for arg in Args[1::]:
                if IsNum.match(arg):
                    NumofExps = int(arg)
                elif arg == '--force':
                    Force = True
                elif arg == '--reltop':
                    RelativetoTop = True
                elif arg in ['--unbook', '--unb']:
                    Action = 'UNBOOK Experiment'
                elif arg == '--noconf':
                    NeedConf = False
                elif arg == '--exit':
                    Status = PromptStatus.EXIT
                    break
                else:
                    print("Invalid Option {Arg}\n".format(Arg=arg))
                    Status = PromptStatus.INVALID_ARG
                    break
        
        if Status == PromptStatus.SUCCESS and NeedConf:
            print("Please confirm your input (confirm: capital Y, not confirm: anything else)")
            print("  ")
            print("  Path            : {Path}".format(Path=Path))
            print("  Num of Experims : {NumofExps}\n".format(NumofExps=NumofExps if NumofExps else 'Default'))
            print("  Action          : {Action}\n".format(Action=Action))
            print("  Force           : {Force}".format(Force=Force))
            print("  RelativetoTop   : {RelTop}".format(RelTop=RelativetoTop))
            print("  ")
            Confirmation = input(">> ")
            if Confirmation == 'Y':
                Status = PromptStatus.SUCCESS
            else:
                print("Booking Cancelled")
                Status = PromptStatus.ITER_OVER

        if Status == PromptStatus.SUCCESS:
            if (Action == 'Book Experiments'):
                try:
                    BookingStatus = BookExperiments(Path, NumofExps, Force=Force, RelativetoTop=RelativetoTop)
                except ValueError:
                    print("It appears as though the directory was invalid\n")
                    Status = PromptStatus.EXIT
                    BookingStatus = False
                if BookingStatus:
                    print("The following bookings were successful:\n")
                    print("  Path          : {Path}\n".format(Path=Path))
                    print("  Number of Exps: {0}\n".format(NumofExps if NumofExps else 1))
                else:
                    print("The following booking was unsuccessful\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  Number of Exps: {0}\n".format(NumofExps if NumofExps else 1))
                    Status = PromptStatus.INVALID_ARG
            else:
                try:
                    UnbookStatus = UnBookExperiments(Path, NumofExps, RelativetoTop=RelativetoTop)
                except ValueError:
                    print("It appears as though the directory was invalid\n")
                    Status = PromptStatus.EXIT
                    UnbookStatus = False
                if UnbookStatus:
                    print("The following un-booking was successful:\n")
                    print("  Path          : {Path}\n".format(Path=Path))
                    print("  Number of Exps: {0}\n".format(NumofExps if NumofExps else 'All'))
                else:
                    print("The following un-booking was unsuccessful\n")
                    print("  Path: {Path}".format(Path=Path))
                    print("  Number of Exps: {0}\n".format(NumofExps if NumofExps else 'All'))
                    Status = PromptStatus.INVALID_ARG
    
    return PromptStatus.SUCCESS


def ClearSessionPrompt():

    global NewEntityData

    Status = PromptStatus.SUCCESS
    print(textwrap.dedent("""
            All the booked entities that have no been confirmed will be deleted.

            Type 'clearsession' if you wish to confirm the clearing of the session.
            any other (non-empty) input will result in the cancelling of the clear
            option and the console will return to the main menu
            """))
    ConfirmationStr = ''
    ReceivedInput = False
    while not ReceivedInput:
        ConfirmationStr = input(">> ")
        if ConfirmationStr:
            ReceivedInput = True
    else:
        if ConfirmationStr.lower() == 'clearsession':
            NewEntityData = []
            Status = PromptStatus.SUCCESS
        else:
            Status = PromptStatus.ITER_OVER
    return Status


def SessionStateDisplayPrompt():
    ListSessionBookings()
    return PromptStatus.SUCCESS


def AssignUIDs(NewUIDData=None, CurrentUIDData=None):
    if NewUIDData is None:
        NewUIDData = NewEntityData
    if CurrentUIDData is None:
        CurrentUIDData = CurrentEntityData

    AssignedUIDData = [copy.copy(x) for x in NewUIDData]
    # The above is to create deep copy
    # i.e. the references to each corresponding Entity in
    # the two arrays must be different

    for i in range(0, len(AssignedUIDData)):
        AssignedUIDData[i].ID = rsa.RSAEncode(i+CurrentNumberBooked+1)

    # Assigning Parent ID
    # hashing dirs by path
    DirHashbyPath = {Entity.Path:Entity.ID for Entity in AssignedUIDData + CurrentUIDData
                     if Entity.Type in ['IntermediateDir', 'ExperimentDir']}
    for Entity in AssignedUIDData:
        if Entity.Type == 'Experiment':
            Entity.ParentID = DirHashbyPath[Entity.Path]
        else:
            Entity.ParentID = DirHashbyPath[os.path.dirname(Entity.Path)]

    return AssignedUIDData


def GetCommitMessage(NewUIDDataWithID):

    SortedUIDData = sorted(
        NewUIDDataWithID,
        key=lambda x: (
            x.Path,
            (0 if x.Type in ['IntermediateDir','ExperimentDir'] else 1)
            )
        )

    OutputStrArr = []
    OutputStrArr += ["Entity Booking Commit\n"]
    OutputStrArr += ["The Bookings in this commit are: \n"]

    for Entity in SortedUIDData:
        OutputStrArr += [textwrap.dedent("""\
                -  Path: {Path}
                   Type: {Type}
                   ID  : {ID:0{len}x}
                """.format(Path=Entity.Path, Type=Entity.Type, ID=Entity.ID, len=32))]

    OutputStr = '\n'.join(OutputStrArr)
    return OutputStr


def PrepareStage():

    CurrDir = os.getcwd()
    ScriptDir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(ScriptDir)

    # Then rename EntityData.yml temporarily
    if os.path.isfile('EntityData.ymlorig'):
        os.remove('EntityData.ymlorig')
    os.rename('EntityData.yml', 'EntityData.ymlorig')
    
    # checkout EntityData.yml from head and reset it from index
    CurrentRepo = Repo('.')
    CurrentHead = CurrentRepo.head
    CurrentHead.reset('HEAD',"-- EntityData.yml")
    CurrentRepo.git.checkout("HEAD", "EntityData.yml")

    os.chdir(CurrDir)


def RollBackStage():
    # Then rename EntityData.yml temporarily
    if os.path.isfile('EntityData.yml'):
        os.remove('EntityData.yml')
    if os.path.isfile('EntityData.ymlorig'):
        os.rename('EntityData.ymlorig', 'EntityData.yml')
    

def ValidateStage():
    StageValid = False
    
    # check if the current working directory is not dirty
    ScriptDir = os.path.dirname(os.path.realpath(__file__))
    ScriptRepo = Repo(ScriptDir)
    StageValid = not ScriptRepo.is_dirty()

    return StageValid


def CheckoutandPull():
    CurrDir = os.getcwd()
    ScriptDir = os.path.dirname(os.path.realpath(__file__))

    os.chdir(ScriptDir)

    RepoMngmtRepo = Repo(os.getcwd())
    origin = RepoMngmtRepo.remote('origin')

    CheckoutSuccess = False
    PullSuccess = False
    
    # attempt to checkout to master. This should
    # succeed if clean
    try:
        RepoMngmtRepo.git.checkout('master')
        CheckoutSuccess = True
    except git.exc.GitCommandError as GitError:
        print(GitError.stderr.decode('utf-8'))
        CheckoutSuccess = False

    if CheckoutSuccess:
        # Pull changes into master. This will be success
        PullResult = origin.pull('master:master')
        if not PullResult or PullResult[0].flags & PullResult[0].ERROR:
            print("origin/master could not be successfully pulled")
        elif PullResult and \
            PullResult[0].flags & (PullResult[0].FAST_FORWARD | PullResult[0].HEAD_UPTODATE):
            PullSuccess = True

    os.chdir(CurrDir)
    return PullSuccess


def CommitandPush(CommitMessage):
    # Assumes that the branch is already checked into master
    # and that the changes have been pulled
    # And that the required EntityData.yml has been edited
    # in the working tree

    CurrDir = os.getcwd()
    ScriptDir = os.path.dirname(os.path.realpath(__file__))

    os.chdir(ScriptDir)

    RepoMngmtRepo = Repo(os.getcwd())
    origin = RepoMngmtRepo.remote('origin')

    PushSuccess = False
    isSuccess = False
        
    # attempt to add EntityData.yml This step may lead to
    # dragons if EntityData.yml has been edited manually
    # and does not exist
    
    CurrentIndex = RepoMngmtRepo.index
    try:
        CurrentIndex.add(['EntityData.yml'])
        DataAdditionSuccess = True
    except OSError:
        print("The addition of EntityData.yml to index was unsuccessful. This is likely becau"
              "se the file does not exist. This is an undefined state. In this case, your bes"
              "t option would be to checkout the file from the latest commit and try again\n")
        DataAdditionSuccess = False

    if DataAdditionSuccess:
        # Commit and Push
        CurrentIndex.commit(CommitMessage)  # Im assuming that this NEVER fails
        MasterRetList = origin.push('master:master')
        if not MasterRetList or (MasterRetList[0].flags & remote.PushInfo.ERROR):
            print("The Push was unsuccessful. This is possibly due to the current branch not being\n"
                  "downstream of the remote branch. In this case, simply try again.  This could\n"
                  "possibly also be due to a network error. The current commit will be rolled back.\n")
            git.refs.head.HEAD(RepoMngmtRepo, path='HEAD').reset('HEAD~1')
        elif MasterRetList[0].flags & remote.PushInfo.FAST_FORWARD:
            print("Fast Forward Merge was successful\n")
            PushSuccess = True
        else:
            print("Wierd shits goin down")
            RepoMngmtRepo.heads.master.reset('HEAD~1')

    isSuccess = PushSuccess
    os.chdir(CurrDir)
    return isSuccess


def ConfirmBookingsPrompt():
    
    global CurrentEntityData
    global NewEntityData

    StageisClean = False
    PullSuccess = False
    CnPSuccess = False
    
    # First, assign UIDs to the bookings
    NewEntitiesWithUID = AssignUIDs()
    NewEntitiesAppended = CurrentEntityData + NewEntitiesWithUID

    # Then calculate working directory and
    # directory of script and change to it
    CurrentDir = os.getcwd()
    ScriptDir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(ScriptDir)

    PrepareStage()
    StageisClean = ValidateStage()
    if not StageisClean:
        print("The working directory cannot have uncommitted changes. This will potentially cause issues\n"
              "with pulling and checkouts. Please reset/commit all changes except to EntityData.yml/ymlorig\n")
        RollBackStage()
    else:
        # attempt checkout and pull
        PullSuccess = CheckoutandPull()

    if PullSuccess:
        # Then rewrite EntityData.yml
        with open('EntityData.yml', 'w') as Fout:
            FlushEntityData(Stream=Fout, CurrentEntData=NewEntitiesAppended, NewEntData=[])

        # Attempt Commit and push
        CommitMessage = GetCommitMessage(NewEntitiesWithUID)
        CnPSuccess = CommitandPush(CommitMessage)
        
        if CnPSuccess:
            print("The following bookings are confirmed:\n")
            print(CommitMessage)
            os.remove('EntityData.ymlorig')
            CurrentEntityData = NewEntitiesAppended
            NewEntityData = []
            Status = PromptStatus.SUCCESS
        else:
            print("The Given Bookings could not be confirmed:\n")
            RollBackStage()
            Status = PromptStatus.ITER_OVER

            os.chdir(CurrentDir)
            return Status


def ExitPrompt():
    print("Are you sure you wanna exit? (capital Y/anything else):")
    Confirmation = input(">> ")
    while(True):
        if Confirmation == 'Y':
            return PromptStatus.EXIT
        else:
            return PromptStatus.ITER_OVER


def RunInteractivePrompt():
    
    Status = PromptStatus.SUCCESS
    while Status != PromptStatus.EXIT:
        
        print(textwrap.dedent("""
            What Would you like to do?
              
              1. Book a directory
              2. Book Experiments
              3. Clear Session
              4. Display Session State
              5. Confirm Bookings
              6. Exit
            """))

        Option = input("Enter Your Choice: ")
        print(Option)
        if Option == '1':
            Status = BookDirectoryPrompt()
        elif Option == '2':
            Status = BookExperimentsPrompt()
        elif Option == '3':
            Status = ClearSessionPrompt()
        elif Option == '4':
            Status = ListSessionBookings()
        elif Option == '5':
            Status = ConfirmBookingsPrompt()
        elif Option == '6':
            Status = ExitPrompt()
            if Status == PromptStatus.EXIT and NewEntityData:
                with open('EntityData.yml', 'w') as Fout:
                    FlushEntityData(Fout)
        else:
            print("Incorrect Option, Enter again\n")
            Status = PromptStatus.INVALID_ARG


def getTopLevelExpDir():
    CurrDir = os.getcwd()
    PrevDirwasRoot = False
    TopDir = ''
    while (not PrevDirwasRoot):
        print("CurrDir: {CurrDir}".format(CurrDir=CurrDir))
        if os.path.isfile(os.path.join(CurrDir, 'EXP_TOP_LEVEL_DIR.indic')):
            TopDir = CurrDir
            break

        NewDir = os.path.normpath(os.path.join(CurrDir, '..'))
        PrevDirwasRoot = (NewDir == CurrDir)
        CurrDir = NewDir
    else:
        print(
            "The current working directory '{CWD}' is not inside the"
            " experiment repository and hence the top directory of the"
            " Experiment repository cannot be calculated")
        TopDir = ''

    return TopDir


def InitialOps():
    
    # find the Top Level Experiment Directory
    global ExperimentTopDir
    global CurrentEntityData
    global NewEntityData
    global CurrentNumberBooked

    ExperimentTopDir = getTopLevelExpDir()
    print(ExperimentTopDir)
    if ExperimentTopDir:
        # read the YAML File
        with open('EntityData.yml', 'r') as Fin:
            YamlEntityData = pyf.yaml.safe_load(Fin)
        
        if 'EntityData' in YamlEntityData.keys():
            # read the Entity Data
            CurrentEntityData = YamlEntityData['EntityData']
            CurrentEntityData = [pyf.ExpRepoEntity(**x) for x in CurrentEntityData]
            CurrentNumberBooked = len(CurrentEntityData)
            if 'NewEntityData' in YamlEntityData.keys():
                NewEntityData = YamlEntityData['NewEntityData']
                NewEntityData = [pyf.ExpRepoEntity(**x) for x in NewEntityData]
                NewEntityData = NewEntityData if NewEntityData else []
            # run the interactive prompt
            RunInteractivePrompt()
        else:
            # Complain about invalid data file
            print(textwrap.dedent("""\
                The file EntityData.yml is invalid. The file must be as follows
                (file content is indented 4 spaces):

                    NumBookedIDs: <The Total number of IDs successfully booked by repo>
                    EntityData:

                    - ID      : '00000000000000000000000000000001'
                      ParentID: '00000000000000000000000000000000'
                      Type    : IntermediateDir
                      Path    : ''

                    - ID      :
                      .
                      .
                      .
                      .

                    NewEntityData:
                    <format similar to EntityData> (can have zero elements)
                """))

InitialOps()
