import os
from os import path
import re
import Entities
import yaml
import textwrap
import copy
import BasicUtils as BU
from BasicUtils import errprint, conprint
from collections import Counter
import colorama as cr


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


def getSessionBookingsString(NewEntityData, Color=False):
    
    # get tree for NewEntityData
    NewEntityTree = getTreeFromNewEntities(NewEntityData)

    def getContentString(EntityTree, IsInit, Color=False):
        """
        This function returns a string representing the subelements of the Tree
        EntityTree. The Path ParentPath is stripped from the the Paths of the
        subelements.
        """
        
        ReturnStringList = []
        ParentType = 'IntermediateDir' if type(EntityTree) is dict else 'ExperimentDir'

        # initializing color ANSI Seqs
        ColorPrefix = cr.Fore.GREEN + cr.Style.BRIGHT if Color and not IsInit else ""
        ColorSuffix = cr.Style.RESET_ALL if Color and not IsInit else ""

        if ParentType == 'IntermediateDir':
            for (Entity, EntityChildren) in EntityTree.items():
                if IsInit:
                    StrippedEntityPath = Entity.Path
                else:
                    StrippedEntityPath = path.basename(Entity.Path)
                
                if StrippedEntityPath == '':
                    StrippedEntityPath = "<Top Dir>"

                # add line corresponding to current element
                ReturnStringList.append(StrippedEntityPath + "/\n")
                ReturnStringList[-1] = ColorPrefix + ReturnStringList[-1] + ColorSuffix

                # concatenate lines corresponding to subelements to this string
                # note that the above line is not to be separated from the
                # subelements string as ReturnStringList is sorted below.
                ReturnStringList[-1] += (
                    "  " +
                    getContentString(EntityChildren, False, Color=Color).replace("\n", "\n  ")
                )  # the above is basically tabbing the output by 2 spaces
        else:
            ReturnStringList.append("Number of Exps: {NExps}".format(NExps=len(EntityTree)))
            ReturnStringList[-1] = ColorPrefix + ReturnStringList[-1] + ColorSuffix

        # Join Lines and return
        return "\n".join(sorted(ReturnStringList))
    
    return getContentString(NewEntityTree[0], IsInit=True, Color=Color)


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

    # Creating array for pseudo parents so that a parent with a
    # particular path will have a unique object ID i.e. it doesnt get
    # created again and again with identical values and different
    # object IDs
    PseudoParentsDict = {}

    for Entity in NewEntityData:
        
        # Calculate Parent Attributes
        if Entity.Type == 'Experiment':
            ParentPath = Entity.Path
            ParentType = 'ExperimentDir'
        else:
            ParentPath = path.dirname(Entity.Path)
            ParentType = 'IntermediateDir'

        if ParentPath not in NewEntityParentDict:
            # In this case, we have to either get parent from
            # CurrentEntityParentDict or create a pseudo-parent
            if ParentPath not in CurrentEntityParentDict:
                if ParentPath not in PseudoParentsDict:
                    ParentEntity = Entities.ExpRepoEntity(
                        ID=Entity.ParentID,
                        ParentID=Entity.ParentID,
                        Type=ParentType,
                        Path=ParentPath
                    )
                    PseudoParentsDict[ParentPath] = ParentEntity
                else:
                    ParentEntity = PseudoParentsDict[ParentPath]
            else:
                ParentEntity = CurrentEntityParentDict[ParentPath]

            # also, if the parent is not yet added to TreeDict,
            # an entry needs to be made under the key 0
            if ParentEntity not in TreeDict:
                if ParentEntity.Type == 'IntermediateDir':
                    TreeDict[ParentEntity] = {}
                else:
                    TreeDict[ParentEntity] = []
                TreeDict[0][ParentEntity] = TreeDict[ParentEntity]
        else:
            # in this case it is assumed by virtue of the parent
            # coming before the child in the list, that the
            # ParentEntity is never not in the TreeDict
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


def getEntityID(RepStr, TopDir, CurrentEntityData):
    """
    This function takes a string RepStr that is representative of the Entity that
    you want to do something about. It then gets the corresponding entity. The
    RepStr can Either be an ID or a Path.

    If it is a Path then the entity corresponding to the DIRECTORY (Not experiments)
    having that path will be returned
    """

    isID = False
    isPath = False
    if RepStr.isnumeric():
        isID = True
    elif re.match(BU.isValidPathRE, RepStr):
        isPath = True
        EntPath = BU.ProcessPath(RepStr, TopDir)
        if EntPath == '.':
            EntPath = ''
    else:
        errprint("\nInvalid Representative string for entity: {Str}".format(Str=RepStr))
        raise ValueError

    if isID:
        try:
            ReturnEnt = CurrentEntityData[int(RepStr)-1]
        except IndexError:
            errprint("\nEntity with ID {EntID} Has not been booked.".format(EntID=RepStr))
            raise
    elif isPath:
        try:
            EntPaths = [E.Path for E in CurrentEntityData]
            ReturnEnt = CurrentEntityData[EntPaths.index(EntPath)]
        except ValueError:
            errprint("\nEntity with Path {EntPath} Has not been booked".format(EntPath=EntPath))
            raise

    return ReturnEnt.ID


def getTreeFromCurrentEntities(CurrentEntityData):
    """
    The following parses NewEntityData to create a tree-like structure
    which can be used to traverse it. The structure of the tree is as
    below.
    
    It is stored as a dictionary as below:
    
    TreeDict = {
                   0:{TopLevelEntity},
                   ParentEntity1ID:[ChildEntities1],
                   ParentEntity2ID:[ChildEntities2],
                   .
                   .
               }
    """
    
    # Assuming that children come after parents
    # Construct Tree as dict of {Entity: dict}
    TreeDict = {0:[]}

    for Entity in CurrentEntityData:
        
        # Create key in treedict if Entity is a directory
        if Entity.Type == 'IntermediateDir':
            TreeDict[Entity.ID] = {}
        elif Entity.Type == 'ExperimentDir':
            TreeDict[Entity.ID] = []
        
        # link entity to parent
        TreeDict[Entity.ParentID].append(Entity)
        
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
