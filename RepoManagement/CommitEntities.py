from os import path
import os

from RepoManagement.BasicUtils import conprint, errprint, outprint
from git import remote
from RepoManagement import ManipEntities
from RepoManagement import Entities
from RepoManagement import LogProcessing as LP
from RepoManagement.LogProcessing import EntityData
import re
import textwrap


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
    NewEntries = [LP.getExperimentEntry(EntityData(Ent)) for Ent in NewEntityList]
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
    FolderLogText = LP.getFolderEntry(EntityData(NewEntity))
    with open(FolderLogPath, 'w') as FolderLogFout:
        FolderLogFout.write(FolderLogText)

    # add folderlog.yml to index
    ExperimentRepo.git.add(FolderLogPath)

    if NewEntity.Type == 'ExperimentDir':
        # create explog.yml
        ExplogPath = path.join(FullPath, 'explog.yml')
        ExplogText = LP.getExplogHeader(NewEntity.ID, 0)

        with open(ExplogPath, 'w') as ExplogFout:
            ExplogFout.write(ExplogText)

        # add explog.yml to index
        ExperimentRepo.git.add(ExplogPath)


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
    EntityTree = ManipEntities.getTreeFromNewEntities(NewEntityDataWithID)

    try:
        # create entities in working tree
        for Entity in EntityTree[0]:
            CreateContents(EntityTree[0][Entity], Entity.Type, ExperimentRepo)
        
        # Update EntityData.yml with new bookings added.
        NewEntitiesAppended = CurrentEntityData + NewEntityDataWithID
        TopDir = ExperimentRepo.working_tree_dir
        with open(path.join(TopDir, 'EntityData.yml'), 'w') as Fout:
            Entities.FlushData(Fout, NewEntitiesAppended)
        ExperimentRepo.git.add('EntityData.yml')
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
    NewEntitiesWithUID = ManipEntities.AssignUIDs(NewEntityData, CurrentEntityData)

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
        outprint("\n" + CommitMessage)

    return isSuccess
