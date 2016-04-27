import os
from os import path
import re
import Entities
import yaml
import textwrap
import copy
from BasicUtils import errprint, conprint
from git import remote
from collections import Counter


def UnBookEntity(Entities2Unbook, NewEntityData):
    '''
    Function Definition:
        
        RemoveEntity(Entities2Unbook, NewEntityData):
    '''
    
    Entities2Unbook = Counter([(x.Path, x.Type) for x in Entities2Unbook])
    
    for Entity in NewEntityData:
        EntityIdentTuple = (Entity.Path, Entity.Type)
        if Entities2Unbook[EntityIdentTuple]:
            # in this case, The entity is identified by its path
            Entities2Unbook[EntityIdentTuple] -= 1
            if not Entities2Unbook[EntityIdentTuple]:
                Entities2Unbook.pop(EntityIdentTuple)
            Entity.Path = '$null'
    
    for EntityInfo in sorted(Entities2Unbook.elements()):
        errprint("\n('{0}', '{1}') does not correspond to any remaining booked entity.".format(EntityInfo[0], EntityInfo[1]))
    
    # recreate array by mutating object instead of creating a new object
    # observe the [:]
    NewEntityData[:] = [Entity for Entity in NewEntityData if Entity.Path != '$null']


def BookDirectory(Path, Type,
                  NewEntityData, CurrentEntityData,
                  Force=False):
    
    # debug_print("Processed Path = {ProcessedPath}".format(ProcessedPath=Path))
    # debug_print("Inside BookDirectory Function")
    # for entry in CurrentEntityData:
    #     debug_print(entry)
    
    BookingSuccessful = False
    ParentisBooked = False
    
    # Find the directory if it has already been booked
    ExistingDir = [
        entry
        for entry in CurrentEntityData + NewEntityData
        if entry.Type in ['IntermediateDir', 'ExperimentDir'] and entry.Path == Path]
    
    if ExistingDir:
        # If Directory has already been assigned UID
        ExistingDir = ExistingDir[0]
        errprint((
            "\nThe directory '{DirPath}' has already been booked\n"
            "   UID : {UID}"
        ).format(DirPath=Path, UID=ExistingDir.ID))
    else:
        # if the parent directory is not the Top Directory
        #   check if the UID for the parent has been assigned and act
        #   appropriately.
        ParentDirPath = path.dirname(Path)
        
        ExistingParentDir = [
            entry
            for entry in CurrentEntityData + NewEntityData
            if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                entry.Path == ParentDirPath]
        
        if not ExistingParentDir:
            if not Force:
                errprint((
                    "\nThe Parent directory '{ParDirPath}' has not been"    "\n"
                    "booked. use Force=True in order to book an"  "\n"
                    "ID for the Parent Directory itself"
                ).format(ParDirPath=ParentDirPath))
            else:
                # debug_print("ParentDirPath={ParentDirPath}".format(ParentDirPath=ParentDirPath))
                ParentisBooked = BookDirectory(
                    ParentDirPath, 'IntermediateDir', NewEntityData, CurrentEntityData,
                    Force=True)
        else:
            ExistingParentDir = ExistingParentDir[0]
            if ExistingParentDir.Type == 'ExperimentDir':
                errprint((
                    "\nThe Parent directory '{ParDirPath}' has been booked" "\n"
                    "as an experiment directory. Hence you cannot book a" "\n"
                    "subdirectory."
                ).format(ParDirPath=ParentDirPath))
            else:
                ParentisBooked = True
        
        if ParentisBooked:
            
            # Validate The Current Directory name
            PathBaseName = path.basename(Path)
            isNameValid = True
            if re.match(r"^[a-zA-Z]((\w|\-)(?!$))*[a-zA-z0-9]?$", PathBaseName) is None:
                errprint((
                    "\nThe Directory Name {0} is not a valid name. A valid Name must start\n"
                    "with an alphabet, contain only the characters [-_a-zA-Z0-9], and\n"
                    "end with an alphanumeric character"
                ).format(PathBaseName))
                isNameValid = False
            
            # In add the given path and entity into the NewEntityData
            if isNameValid:
                LastEntry = {}
                LastEntry['ID']       = 0
                LastEntry['ParentID'] = 0
                LastEntry['Type']     = Type
                LastEntry['Path']     = Path
                NewEntityData += [Entities.ExpRepoEntity(**LastEntry)]
                BookingSuccessful = True
    
    return BookingSuccessful


def UnBookDirectory(Path, NewEntityData, Force=False):
    
    def isAnc(AncPath, OtherPath):
        AncPath   = path.normpath(AncPath)
        OtherPath = path.normpath(OtherPath)
        return path.commonpath([AncPath, OtherPath]) == AncPath
    CurrPathEntities = [Entity for Entity in NewEntityData if isAnc(Path, Entity.Path)]
    
    if len(CurrPathEntities) > 1 and not Force:
            errprint((
                "\nThe Specified directory '{ParDirPath}' has children"     "\n"
                "that have been assigned a UID. use Force=True in order"  "\n"
                "to un-book the directory and all its children/subdirs"
            ).format(ParDirPath=Path))
            UnbookStatus = 0
    elif len(CurrPathEntities) > 0:
        UnBookEntity(CurrPathEntities, NewEntityData)
        UnbookStatus = 1
    else:
        errprint((
                "\nThe Specified directory '{ParDirPath}' has not been"     "\n"
                "booked in this session"
        ).format(ParDirPath=Path))
        UnbookStatus = 0
    return UnbookStatus


def UnBookExperiments(Path, NewEntityData, NumofExps=None):
    
    CurrPathExps = [Entity for Entity in NewEntityData
                    if Entity.Type == 'Experiment' and Path == Entity.Path]

    # assigning NumofExps
    if NumofExps is None:
        NumofExps = len(CurrPathExps)
    elif NumofExps > len(CurrPathExps):
        conprint((
            "\nThe number of experiments to be deleted ({0}) exceeds the \n"
            "total number of experiments with specified path ({1}).\n"
            "Truncating the number accordingly."
        ).format(NumofExps, len(CurrPathExps)))
        NumofExps = len(CurrPathExps)
    
    if len(CurrPathExps) > 0:
        UnBookEntity(CurrPathExps[0:NumofExps], NewEntityData)
        DeleteStatus = 1
    else:
        errprint((
            "\nThe given path has either not been booked, or has no experiments" "\n"
            "booked under it."
        ).format(NumofExps, len(CurrPathExps)))
        DeleteStatus = 0
    return DeleteStatus


def BookExperiments(Path, NewEntityData, CurrentEntityData,
                    NumofExps=1,
                    Force=False):
    
    # See if Path has already been assigned a UID
    ExistingDir = [
                    entry for entry in CurrentEntityData + NewEntityData
                          if  entry.Type in ['IntermediateDir', 'ExperimentDir'] and
                              entry.Path == Path]
    
    ContDirisBooked = False
    BookingSuccessful = False
    
    if not ExistingDir:
        if not Force:
            errprint((
                "\nThe containing directory '{ContDirPath}' has not been "
                "assigned a UID. use Force=True in order to book an "
                "ID for the Parent Directory itself"
            ).format(ContDirPath=Path))
        else:
            ContDirisBooked = BookDirectory(
                Path, 'ExperimentDir', NewEntityData, CurrentEntityData,
                Force=True)
    else:
        ExistingDir = ExistingDir[0]
        if ExistingDir.Type == 'IntermediateDir':
            errprint((
                "\nThe containing directory '{ContDirPath}' has been booked" "\n"
                "as an intermediate directory. Hence you cannot book experiments" "\n"
                "directly under this directory"
            ).format(ContDirPath=Path))
        else:
            ContDirisBooked = True
    
    # If the folder has been booked
    if ContDirisBooked:
        for i in range(1, NumofExps+1):
            LastEntry = {}
            LastEntry['ID']       = 0
            LastEntry['ParentID'] = 0
            LastEntry['Type']     = 'Experiment'
            LastEntry['Path']     = Path
            NewEntityData           += [Entities.ExpRepoEntity(**LastEntry)]
        
        BookingSuccessful = True
    
    return BookingSuccessful


def getSessionBookingsString(NewEntityData):
    
    SortedEntityData = sorted(
        NewEntityData,
        key=lambda x: (
            x.Path,
            (0 if x.Type in ['IntermediateDir','ExperimentDir'] else 1)
        )
    )
    
    # for each entity, split its path.
    SplitSortedUID = [re.split(r"[\\/]", Entity.Path) for Entity in SortedEntityData]
    
    # for each entity, do the following
    #   If it is a directory,
    #     search depthwise for the longest matching set of keys.
    #     once a match fails, add the remaining part of the path as a key
    #   If it is an experiment,
    #     search depthwise for the match of its entire path:
    #     Finally, add a subkey NumberofExps: and increment its value
    
    DisplayDict = {}
    for Ent, SplitEntPath in zip(SortedEntityData, SplitSortedUID):
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
    
    def getDirStringList(PathListDict):
        """
        This function returns a a string representing te specified entity heirarcy
        in PathListDict
        """
        ReturnStringList = []
        
        PathListDictItems = PathListDict.items()
        for (DictKey, DictValue) in PathListDictItems:
            if DictKey == 'NumofExps' and DictValue.__class__ == int:
                ReturnStringList.append(DictKey + ": " + str(DictValue))
            else:
                ReturnStringList.append(DictKey + "/\n")
                ReturnStringList[-1] += (
                    "  " +
                    getDirStringList(DictValue).replace("\n", "\n  ")
                )  # the above is basically tabbing the output by 2 spaces
        return "\n".join(sorted(ReturnStringList))
    
    return getDirStringList(DisplayDict)


def AssignUIDs(NewEntityData, CurrentEntityData):
    
    CurrentNumberBooked = len(CurrentEntityData)
    AssignedEntityData = [copy.copy(x) for x in NewEntityData]

    # The above is to create deep copy
    # i.e. the references to each corresponding Entity in
    # the two arrays must be different
    
    for i in range(0, len(AssignedEntityData)):
        AssignedEntityData[i].ID = i+CurrentNumberBooked+1
    
    # Assigning Parent ID
    # hashing dirs by path
    DirHashbyPath = {Entity.Path:Entity.ID for Entity in AssignedEntityData + CurrentEntityData
                     if Entity.Type in ['IntermediateDir', 'ExperimentDir']}
    for Entity in AssignedEntityData:
        if Entity.Type == 'Experiment':
            Entity.ParentID = DirHashbyPath[Entity.Path]
        else:
            Entity.ParentID = DirHashbyPath[path.dirname(Entity.Path)]
    
    return AssignedEntityData


def getCommitMessage(NewEntityDataWithID):
    
    SortedEntityData = sorted(
        NewEntityDataWithID,
        key=lambda x: (
            x.Path,
            (0 if x.Type in ['IntermediateDir','ExperimentDir'] else 1)
        )
    )
    
    OutputStrArr = []
    OutputStrArr += ["Entity Booking Commit\n"]
    OutputStrArr += ["The Bookings in this commit are: \n"]
    
    for Entity in SortedEntityData:
        OutputStrArr += [textwrap.dedent("""\
                -  Path: {Path}
                   Type: {Type}
                   ID  : {ID}
                """.format(Path=Entity.Path, Type=Entity.Type, ID=Entity.ID))]
    
    OutputStr = '\n'.join(OutputStrArr)
    return OutputStr


def getExplogHeader(FolderID, NumberofExps):
    """
    Gets the header of the explog.yml file. the returned text is as below.
    (between ---Start--- and ---End---):
    
    ---Start---
    
    - ID         : <The Unique 32-bit ID assigned to Current Experiment>
      Title      : <blank>
      Description: |
      
    ## End of Experiment <ID> ##################<upto 100 chars>#####
    ---End---
    """
    HeaderLines = []
    HeaderLines.append("ExpFolderID: {ExpDirID}".format(ExpDirID=FolderID))
    HeaderLines.append("NumberofEntries: {NumExps}".format(NumExps=NumberofExps))
    HeaderLines.append("ExpEntries: ")

    return "\n".join(HeaderLines)


def getExplogEntry(ExperimentEntity):
    """
    This function returns the string corresponding to the entry in
    explog.yml (empty i.e. without content) corresponding to the
    above ExperimentEntity. the string it returns is given below
    (between ---Start--- and ---End---):

    ---Start---

    - ID         : <The Unique 32-bit ID assigned to Current Experiment>
      Title      : <blank>
      Description: |
      
    ## End of Experiment <ID> ##################<upto 100 chars>#####
    ---End---

    Note that at the end there is no newline
    """

    Lines = []

    Lines.append("")
    Lines.append("- ID         : {UID}".format(UID=ExperimentEntity.ID))
    Lines.append("  Title      : ")
    Lines.append("  Description: |")
    Lines.append("")
    Lines.append("{0:#<100}".format("## End of Experiment {UID}".format(UID=ExperimentEntity.ID)))

    return "\n".join(Lines)


def getFolderlogEntry(DirectoryEntity):
    """
    This function returns the string corresponding to the entry in
    folderlog.yml (empty i.e. without content) corresponding to the
    above ExperimentEntity. the string it returns is given below
    (between ---Start--- and ---End---):

    ---Start---
    FolderID         : <The Unique ID of the Folder>
    ParentFolderID   : <The Unique ID of the Parent Folder>
    FolderType       : <Either 'IntermediateDir' or ExperimentDir'>
    FolderTitle      : <blank>
    FolderDescription: |

    ---End---
    """

    Lines = []
    
    Lines.append("FolderID         : {UID}".format(UID=DirectoryEntity.ID))
    Lines.append("ParentFolderID   : {UID}".format(UID=DirectoryEntity.ParentID))
    Lines.append("FolderType       : {Type}".format(Type=DirectoryEntity.Type))
    Lines.append("FolderTitle      : ")
    Lines.append("FolderDescription: |")

    return "\n".join(Lines)


def CreateExperiments(NewEntityList, ExperimentRepo):
    """
    This takes a list of new entities to be added to a particular explog file,
    and edits the explog file appropriately, and adds the changes to the index
    of repo after validating the above data. The validations are below:
    
    1.  All Entities in NewEntityList must have the same path i.e. must be
        added to the same explog file. They must also be of type 'Experiment'
        
    2.  The path above must already exist in the system. Moreover, explog.yml
        must also exist in the said path. If the directory has been created
        correctly, the creation of explog.yml should also be complete
        
    3.  The above entity IDs must NOT conflict with The Existing IDs in
        explog.yml. This is not enforced explicitly but is rather assumed.
        Later on, we will attempt to keep this legit by ensuring that
        EntityData.yml is indeed uptodate in all processings
    """

    if not NewEntityList:
        # Dont do anything
        return

    TopDir = ExperimentRepo.working_tree_dir

    # Ensure condition 1. (Uniqueness of Path / Validity of Type)
    # If Path is unique then store the path
    UniquePaths = {Ent.Path for Ent in NewEntityList}
    if len(UniquePaths) == 1:
        ExpLogPath = path.join(TopDir, UniquePaths.pop())
    else:
        errprint("\nAll Entities given to CreateExperiments(...) must correspond to the same Path")
        raise ValueError
    UniqueTypes = {Ent.Type for Ent in NewEntityList}
    if len(UniqueTypes) != 1 or UniqueTypes.pop() != 'Experiment':
        errprint("\nAll Entities given to CreateExperiments(...) must have Type == 'Experiment'.")
        raise ValueError

    # Ensure Condition 2. (Existence of explog.yml Path)
    # If Path Exists, check if file exist
    FilePath = path.join(ExpLogPath, "explog.yml")
    FileExists = path.isfile(path.join(ExpLogPath, "explog.yml"))
    if not FileExists:
        errprint(
            "\nThe path into which the experiment entries are to be inserted either does not\n"
            "exist, or does not contain explog.yml.")
        raise ValueError

    # Calculate the 'Previous Text' i.e. text to which we append
    # the current Entity Entries

    # Here we read explog.yml, modify the EntityCount to create PrevText
    with open(FilePath) as CurrentExplogFin:
        PrevText = CurrentExplogFin.read()
    CurrentExpCount = int(re.match(r".*\nNumberofEntries: ([0-9]+)", PrevText).group(1))
    NewExpCount = CurrentExpCount + len(NewEntityList)
    PrevText = re.sub("(?<=NumberofEntries: )[0-9]+", str(NewExpCount), PrevText, count=1)

    # Now get the text corresponding to all the New entries
    NewEntries = [getExplogEntry(Ent) for Ent in NewEntityList]
    NewEntriesText = "\n".join(NewEntries)

    NewText = "\n".join([PrevText, NewEntriesText])

    # Write explog.yml with new data
    with open(FilePath, 'w') as NewExplogFout:
        NewExplogFout.write(NewText)

    # add to index
    ExperimentRepo.index.add([FilePath])


def CreateDirectory(NewEntity, ExperimentRepo):
    """
    This takes a new entity (a directory entity) to be added and creates the
    directory, its folderlog.yml, and in case the directory is an experimentDir file after validating the NewEntity and edits
    the explog file appropriately. The validations
    are below:

    1.  The NewEntity must be of Directory type.
    2.  The path of the parent directory must already be booked
    3.  The path of the above directory must NOT already contain folderlog.yml.
    4.  It is assumed that this objects Entity ID will not be in conflict with any
        others. This will later be ensured by ensuring updatedess of EntityData.yml
    """

    TopDir = ExperimentRepo.working_tree_dir

    # Ensuring Condition 1. (Validity of Entity Type)
    if NewEntity.Type not in ['IntermediateDir', 'ExperimentDir']:
        errprint(
            "\nThe type of the entity given as argument to CreateDirectory(...) must be of\n"
            "directory type i.e. Type == 'IntermediateDir' or 'ExperimentDir'")
        raise ValueError

    # Ensuring Condition 2. (Existence of Parent Path)
    FullPath = path.join(TopDir, NewEntity.Path)
    ParentDirPath = path.dirname(FullPath)
    FolderLogPath = path.join(FullPath, 'folderlog.yml')
    if not path.isfile(path.join(ParentDirPath, 'folderlog.yml')):
        errprint(textwrap.dedent(
            """
            The Parent Directory of the Dir that you are booking does not seem to
            have been validly created. Either It doesnt exist or doesnt contain a
            'folderlog.yml' file. This really shouldn't be happening
            
            Parent Directory Path: '{Path}'\
            """.format(Path=ParentDirPath)))
        raise ValueError
    
    # Ensuring Condition 3. (Unbookedness of Path)
    if path.isfile(FolderLogPath):
        errprint(textwrap.dedent(
            """
            The Directory that you are booking already seems to exist and
            contain folderlog.yml indicating that it has been booked. This should
            not be the case:
            
            1.  This could be caused by having pulled some changes in which this
                directory has been created.
                
                In this case, try rebooking and changing the name of the directory

            Path of Directory: {Path}\
            """.format(Path=ParentDirPath)))
        raise ValueError
    
    # create directory (if necessary)
    if not path.isdir(FullPath):
        os.mkdir(FullPath)

    # create folderlog.yml
    FolderLogText = getFolderlogEntry(NewEntity)
    with open(FolderLogPath, 'w') as FolderLogFout:
        FolderLogFout.write(FolderLogText)

    # add folderlog.yml to index
    ExperimentRepo.index.add([FolderLogPath])

    if NewEntity.Type == 'ExperimentDir':
        # create explog.yml
        ExplogPath = path.join(FullPath, 'explog.yml')
        ExplogText = getExplogHeader(NewEntity.ID, 0)

        with open(ExplogPath, 'w') as ExplogFout:
            ExplogFout.write(ExplogText)

        # add explog.yml to index
        ExperimentRepo.index.add([ExplogPath])


def CreateContents(Contents, ParentType, ExperimentRepo):
    """
    This argument takes a list of either Trees (in case of IntermediateDir) or
    Experiments (in case of ExperimentDir) and creates them. It recursively
    calls itself if the Elements in Contents are directories/trees
    """
    if ParentType == 'IntermediateDir':
        SubElements = list(Contents.keys())
    else:
        SubElements = Contents

    if ParentType == 'ExperimentDir':
        CreateExperiments(SubElements, ExperimentRepo)
    else:
        for Entity in SubElements:
            CreateDirectory(Entity, ExperimentRepo)
            CreateContents(Contents[Entity], Entity.Type, ExperimentRepo)


def getTreeFromNewEntities(CurrentEntityData, NewEntityData):

    # Assuming that children come after parents
    # Construct Tree as dict of {Entity: dict}
    TreeDict = {0:{}}
    CurrentEntityDict = {Ent.ID:Ent for Ent in CurrentEntityData}
    NewEntityDict = {Ent.ID:Ent for Ent in NewEntityData}

    for Entity in NewEntityData:
        if Entity.ParentID not in NewEntityDict:
            ParentEntity = CurrentEntityDict[Entity.ParentID]
            TreeDict[ParentEntity] = {}
            TreeDict[0][ParentEntity] = TreeDict[ParentEntity]
        else:
            ParentEntity = NewEntityDict[Entity.ParentID]

        if ParentEntity.Type == 'IntermediateDir':
            if Entity.Type == 'ExperimentDir':
                TreeDict[Entity] = []
            elif Entity.Type == 'IntermediateDir':
                TreeDict[Entity] = {}
            TreeDict[ParentEntity][Entity] = TreeDict[Entity]
        else:
            # Entity.Type is equal to Experiment necessarily
            TreeDict[ParentEntity].append(Entity)

    return TreeDict


def PrepareTreeandIndex(CurrentEntityData, NewEntityDataWithID, ExperimentRepo):
    """
    This function is a very important function in that it actually creates the
    directories and experiment entities that have been booked and adds them to
    the git index
    """
    
    # Ensure that EntityData.yml is uptodate
    # this piece of code will be added later

    # Get the tree, and {ID:Entity} Dict corresponding to
    # NewEntityData
    EntityTree = getTreeFromNewEntities(CurrentEntityData, NewEntityDataWithID)

    try:
        # create entities in working tree
        for Entity in EntityTree[0]:
            CreateContents(EntityTree[0][Entity], Entity.Type, ExperimentRepo)
        
        # Update EntityData.yml with new bookings added.
        NewEntitiesAppended = CurrentEntityData + NewEntityDataWithID
        TopDir = ExperimentRepo.working_tree_dir
        with open(path.join(TopDir, 'EntityData.yml'), 'w') as Fout:
            Entities.FlushData(Fout, NewEntitiesAppended)
        ExperimentRepo.index.add(['EntityData.yml'])
    except:
        errprint("\nEntity Creation Failed.")
        raise


def ValidateStage(ExperimentRepo):
    StageValid = True

    # check if current branch is master branch
    CurrentBranch = ExperimentRepo.active_branch
    if CurrentBranch.name != 'master':
        errprint("\nHEAD must be master")
        StageValid = False

    # check if current branch is up-to-date
    if StageValid:
        Origin = ExperimentRepo.remote("origin")
        FetchStatus = Origin.fetch()  # it is expected that this doesnt return an error.
        if FetchStatus[0].flags & remote.FetchInfo.ERROR:
            errprint(
                "\n"
                "Fetch could not be performed. This is likely an issue with the internet\n"
                "connection. Enable internet connection and then run the command again.")
            StageValid = False

    if StageValid:
        if Origin.refs["master"].commit != CurrentBranch.commit:
            errprint(
                "\n"
                "The master is either ahead or behind origin/master. Do ensure that this\n"
                "is not the case. Either pull or push master to acheive the same. Note that\n"
                "Ideally, it should never be the case that your master is AHEAD of origin/\n"
                "master. If that is the case, there is a possibility of some shit having gone\n"
                "seriously wrong")
            StageValid = False

    # check if the current working directory is not dirty.
    # This includes the existence of untracked files as they should
    # no be checked into the index upon running git add.
    if StageValid:
        def isClean(ExpRepo):
            Diff = ExpRepo.index.diff('HEAD')
            DiffVect = [d for d in Diff]
            isRepoClean = not bool(DiffVect)

            if isRepoClean:
                Diff = ExpRepo.head.commit.diff(None)
                # change is dirty if it is not a submodule or an untracked file
                # note that 57344 = 0o160000 which is the mode for submodule
                IsDirtyChange = [not (d.b_mode == 57344 or d.new_file) for d in Diff]
                if any(IsDirtyChange):
                    isRepoClean = False

            return isRepoClean

        DirectoryIsClean = isClean(ExperimentRepo)
        if not DirectoryIsClean:
            errprint(textwrap.dedent("""
                There appears to be changes in either the index or working
                directory, this is not allowed. perform hard reset i.e.
                
                    git reset HEAD --hard\
                """))
            StageValid = False

    return StageValid


def CommitandPush(CommitMessage, ExperimentRepo):
    # Assumes that the branch is already checked into master
    # and that the changes have been pulled
    # And that the required EntityData.yml has been edited
    # in the working tree
        
    PushSuccess = False
    isSuccess = False
        
    # Commit
    ExperimentRepo.index.commit(CommitMessage)  # Im assuming that this NEVER fails
    
    # and Push
    MasterRetList = ExperimentRepo.remote('origin').push('master:master')
    if not MasterRetList or (MasterRetList[0].flags & remote.PushInfo.ERROR):
        errprint(
            "\n"
            "The Push was unsuccessful. This is possibly due to the current branch not being\n"
            "downstream of the remote branch. In this case, simply try again.  This could\n"
            "possibly also be due to a network error. The current commit will be rolled back."
        )
        ExperimentRepo.heads.master.reset('HEAD~1')
    elif MasterRetList[0].flags & remote.PushInfo.FAST_FORWARD:
        conprint("\nFast Forward Merge was successful")
        PushSuccess = True
    else:
        errprint("\nWierd shits goin down")
        ExperimentRepo.heads.master.reset('HEAD~1')
    
    isSuccess = PushSuccess
    return isSuccess


def ConfirmBookings(CurrentEntityData, NewEntityData, ExperimentRepo):
    """
    Confirms Bookings
    """

    isSuccess = True
    ResetNeeded = False
    # First, assign UIDs to the bookings
    NewEntitiesWithUID = AssignUIDs(NewEntityData, CurrentEntityData)

    # Then we validate the stage.
    isStageValid = ValidateStage(ExperimentRepo)

    if not isStageValid:
        isSuccess = False

    if isSuccess:
        try:
            PrepareTreeandIndex(CurrentEntityData, NewEntitiesWithUID, ExperimentRepo)
        except:
            errprint("\nFailed To prepare working directory for commit.")
            isSuccess = False
            ResetNeeded = True

    if isSuccess:
        CommitMessage = getCommitMessage(NewEntitiesWithUID)
        isPushSuccess = CommitandPush(CommitMessage, ExperimentRepo)
        if not isPushSuccess:
            isSuccess = False
            ResetNeeded = True

    if not isSuccess:
        errprint("\nConfirmation of Bookings Failed.")
        if ResetNeeded:
            errprint("\nPerforming Hard reset.")
            ExperimentRepo.head.reset(working_tree=True)
            errprint("\nReset Complete.")
    else:
        conprint("\nConfirmation of Bookings successful:")
        print("\n" + CommitMessage)

    return isSuccess


def getTopLevelExpDir():
    """
    This function is left here just in case it is needed later.
    Cyrrently the top directory is just defined to be the parent
    directory of RepoManagement
    """
    CurrDir = os.getcwd()
    PrevDirwasRoot = False
    TopDir = ''
    while (not PrevDirwasRoot):
        if path.isfile(path.join(CurrDir, 'EXP_TOP_LEVEL_DIR.indic')):
            TopDir = CurrDir
            break
        
        NewDir = path.normpath(path.join(CurrDir, '..'))
        PrevDirwasRoot = (NewDir == CurrDir)
        CurrDir = NewDir
    else:
        errprint(
            "\nThe current working directory '{CWD}' is not inside the"
            " experiment repository and hence the top directory of the"
            " Experiment repository cannot be calculated")
        TopDir = ''
    
    return TopDir


def getEntityDataFromStream(Stream):
    """
    This function reads the file represented by Stream (which MUST represent a
    valid Entity-Data storing YAML file, and returns the corresponding list of
    ExpRepoEntity objects. In case the read failed due to any reason, the fun-
    ction returns None
    """

    EntityList = None

    # read the YAML File
    with Stream as Fin:
        YamlEntityData = yaml.safe_load(Fin)
    
    if 'EntityData' in YamlEntityData.keys():
        # read the Entity Data
        EntityList   = YamlEntityData['EntityData']
        if EntityList:
            EntityList   = [Entities.ExpRepoEntity(**x) for x in EntityList]
        else:
            EntityList = []
    else:
        # Complain about invalid data file
        errprint(textwrap.dedent("""
            The file containing Entity Data is invalid. The file must be as follows
            (file content is indented 4 spaces):
                
                NumEntities: <The Total number of Entities booked by repo>
                
                EntityData:
                
                - ID      : 1
                  ParentID: 0
                  Type    : IntermediateDir
                  Path    : ''
                
                #####################<100 times>...##

                - ID      :
                  .
                  .
                  .
                
                #####################<100 times>...##

                  .
                  .
                  .

                - ID      :
                  .
                  .
                  .
                
                #####################<100 times>...##\
            """))
    
    return EntityList
