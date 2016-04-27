import os
from os import path
import re
import Entities
import yaml
import textwrap
import copy
from BasicUtils import errprint, conprint
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


def getTreeFromNewEntities(NewEntityData, CurrentEntityData=[]):
    """
    The following parses NewEntityData to create a tree-like structure
    which can be used to traverse it. The structure of the tree is as
    below.
    
    It is stored as a dictionary as below:
    
    TreeDict = {
                   0:TopLevelParents,
                   ParentEntity1:ParentEntity1sChildrenList,
                   ParentEntity2:ParentEntity2sChildrenList,
                   .
                   .
               }
    
    Where each key except 0 is A PARENT Entity of some element in
    NewEntityData. The tree heirarch is inferred from the PATH and
    NOT the ID / ParentID relation. This is because it is possible
    for NewEntityData to not have assigned UIDs

    The values of the keys are as below:

    if ParentEntity is an IntermediateDir:
        TreeDict[ParentEntity] = ParentEntitysChildrenList is a
        TreeDict containing as keys all the children of ParentEntity
        (each of which must be a directory entity). The values
        will be a ChildrenList corresponding to the children of
        the keys.

    if ParentEntity is an ExperimentDir:
        TreeDict[ParentEntity] = ParentEntitysChildrenList is a
        list of entities representing the children (in this case
        experiments) of ParentEntity.

    for key 0:
        TopLevelParents represents all parents which are
        NOT in NewEntityData (i.e. are the deepest (from root) parents
        who are in CurrentEntityData). Every element in NewEntityData
        is a child of at least one element from TopLevelParents because
        the Top Level Directory is a part of CurrentEntityData

        In the Event that CurrentEntityData is NOT Specified, (i.e. None)
        Then A Spurious parent entity path as dirname of the entity will
        be created and used instead.
    
    At any time using Pythons Copy-by-object-id policy, we ensure that
    the following Equivalence is maintained

    TreeDict[EntitysParent][Entity] == TreeDict[Entity]

    i.e. There is only one copy of ChildrenList in the tree and
    TreeDict[..][..][..][Entity] points to it no matter what the ..'s
    are.
    """

    # Assuming that children come after parents
    # Construct Tree as dict of {Entity: dict}
    TreeDict = {0:{}}
    CurrentEntityParentDict = {
        Ent.Path:Ent
        for Ent in CurrentEntityData
        if Ent.Type in ['IntermediateDir', 'ExperimentDir']
    }
    NewEntityParentDict = {
        Ent.Path:Ent
        for Ent in NewEntityData
        if Ent.Type in ['IntermediateDir', 'ExperimentDir']
    }

    for Entity in NewEntityData:
        
        if Entity.Type == 'Experiment':
            ParentPath = Entity.Path
            ParentType = 'ExperimentDir'
        else:
            ParentPath = path.dirname(Entity.Path)
            ParentType = 'IntermediateDir'

        if ParentPath not in NewEntityParentDict:
            if ParentPath not in CurrentEntityParentDict:
                ParentEntity = Entities.ExpRepoEntity(
                    ID=Entity.ParentID,
                    ParentID=Entity.ParentID,
                    Type=ParentType,
                    Path=ParentPath
                )
            else:
                ParentEntity = CurrentEntityParentDict[ParentPath]

            TreeDict[ParentEntity] = {}
            TreeDict[0][ParentEntity] = TreeDict[ParentEntity]
        else:
            ParentEntity = NewEntityParentDict[ParentPath]

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
