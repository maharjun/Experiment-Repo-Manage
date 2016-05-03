from os import path
from BasicUtils import errprint
import yaml


class EntityData:
    """
    This class is used to represent data pertaining to an entity as read from the
    log files. The following members are common between all types of entities

        ID
        ParentID
        Type
        Path
        Title
        Description

    The following members are exclusive to directory type entities

        Name
    """
    ID          = None
    ParentID    = None
    Type        = None
    Path        = None
    Title       = None
    Description = None

    def __init__(self, Entity, Title=None, Description=None):
        """
        Initializes an EntityData instance as follows:

        1.  ID, ParentID, Type, and Path are initialized from the 'Entity' parameter
            (it is expected that 'Entity' is of type ExpRepoEntity)

        2.  Name (if directory) is initialized as the base of path.

        3.  Title and Description from keyword parameters. Description is only init-
            ialized if Title is a non-empty string
        """
        self.ID          = Entity.ID
        self.ParentID    = Entity.ParentID
        self.Type        = Entity.Type
        self.Path        = Entity.Path
        if self.Type in ['IntermediateDir', 'ExperimentDir']:
            self.Name    = path.basename(self.Path)
        self.Title       = Title if Title else ''
        self.Description = Description if Title and Description else ''

    def get(self, MemberName):
        return getattr(self, MemberName)


def FolderlogMissingError(Entity):
    pass


def ExplogMissingError(Entity):
    pass


def getExplogHeader(FolderID, NumberofExps):
    """
    Gets the header of the explog.yml file. the returned text is as below.
    (between ---Start--- and ---End---):
    
    ---Start---
    ExpFolderID: <Experiment Directory ID>
    NumberofEntries: <Number of Experiments>
    ExpEntries: <blank>
    ---End---
    """
    HeaderLines = []
    HeaderLines.append("ExpFolderID: {ExpDirID}".format(ExpDirID=FolderID))
    HeaderLines.append("NumberofEntries: {NumExps}".format(NumExps=NumberofExps))
    HeaderLines.append("ExpEntries: ")

    return "\n".join(HeaderLines)


def getFolderEntry(FolderEntityData):
    """
    This returns a single entry corresponding to the Directory Entity
    referred to by FolderEntityData. The returned string is given below
    (between ---Start--- and ---End---)

    ---Start---
    FolderID         : <The Unique ID of the Folder>
    ParentFolderID   : <The Unique ID of the Parent Folder>
    FolderType       : <Either 'IntermediateDir' or ExperimentDir'>
    FolderTitle      : <A short title describing contents>
    FolderDescription: |-2
      The Detailed description of the contents of the folder. Note that
      it should NOT be an element by element description of its contents.
      Rather it should be something that gives an overall description of
      the kind of entities (experiments/directories) that it contains.
      (You can use Markdown level-2 header onwards).

    ---End---
    """

    if FolderEntityData.Type not in ['IntermediateDir', 'ExperimentDir']:
        errprint('\nThe given EntityData does not represent the data of a directory')
        raise ValueError

    OutputLines = []
    
    OutputLines.append("FolderID         : {UID}".format(UID=FolderEntityData.ID))
    OutputLines.append("ParentFolderID   : {UID}".format(UID=FolderEntityData.ParentID))
    OutputLines.append("FolderType       : {Type}".format(Type=FolderEntityData.Type))
    OutputLines.append("FolderTitle      : {Title}".format(Title=FolderEntityData.Title))
    OutputLines.append("FolderDescription: |-2")
    OutputLines += ["  "+Line for Line in FolderEntityData.Description.splitlines()]
    OutputLines.append("")

    return "\n".join(OutputLines)


def getExperimentEntry(ExpEntityData):
    """
    This returns a single entry corresponding to the Experiment Entity
    referred to by ExpEntityData. The returned string is given below
    (between ---Start--- and ---End---)

    ---Start---

    - ID         : <The Unique 32-bit ID assigned to Current Experiment>
      Title      : <A short title describing contents>
      Description: |-2
        The Detailed description of the experiment,
        including any special instructions apart from the
        setup script. This is to be written in Markdown
        (level-2 header onwards).

    ## End of Experiment <ID> ##################<up to 100 chars>#####
    ---End---
    """

    # Validate that ExpEntityData actually corresponds to an Experiment Entity
    if ExpEntityData.Type != 'Experiment':
        errprint("\nThe Entity Data does not represent the data of an experiment")
        raise ValueError

    OutputLines = []
    OutputLines.append("")
    OutputLines.append("- ID         : {ID}".format(ID=ExpEntityData.ID))
    OutputLines.append("  Title      : {Title}".format(Title=ExpEntityData.Title))
    OutputLines.append("  Description: |-2")
    OutputLines += ["    "+Line for Line in ExpEntityData.Description.splitlines()]
    OutputLines.append("")
    OutputLines.append(
        "{0:#<100}".format("## End of Experiment {UID} ".format(UID=ExpEntityData.ID)))

    return "\n".join(OutputLines)


def ReadEntityLog(Entity, TopDir):

    EntPath = path.join(TopDir, Entity.Path)
    
    if Entity.Type in ['IntermediateDir', 'ExperimentDir']:
        LogPath = path.join(EntPath, 'folderlog.yml')
    else:
        LogPath = path.join(EntPath, 'explog.yml')

    # Open Current Directory folderlog.yml file and read it.
    if Entity.Type in ['IntermediateDir', 'ExperimentDir']:
        try:
            with open(LogPath) as LogIn:
                LogData = yaml.safe_load(LogIn)
        except:
            errprint(FolderlogMissingError(Entity))
            raise

        # Create EntityData instance to represent given Entity Log
        LogData = EntityData(
            Entity,
            Title=LogData['FolderTitle'],
            Description=LogData['FolderDescription'])
    else:
        try:
            with open(LogPath) as LogIn:
                LogData = yaml.safe_load(LogIn)
        except:
            errprint(ExplogMissingError(Entity))
            raise

        # select Entry corresponding to current experiment
        LogData = [x for x in LogData['ExpEntries'] if x['ID'] == Entity.ID]
        LogData = LogData[0]

        # Create EntityData instance to represent given Entity Log
        LogData = EntityData(Entity, Title=LogData['Title'], Description=LogData['Description'])
        
    return LogData


def ReadChildrenData(Entity, CurrentEntityList, TopDir):

    if Entity.Type not in ['IntermediateDir', 'ExperimentDir']:
        errprint("\nEntity with ID {EntityID} is not a directory".format(EntityID=Entity.ID))
        raise ValueError
    elif Entity.Type == 'IntermediateDir':
        # Get List of Children
        ChildEntities = [E for E in CurrentEntityList if E.ParentID == Entity.ID]
        # get data by reading folderlogs
        ChildEntData = [ReadEntityLog(E, TopDir) for E in ChildEntities]
    else:
        ExpLogPath = path.join(TopDir, Entity.Path, 'explog.yml')
        try:
            with open(ExpLogPath) as ExpLogIn:
                ExpLogYAMLData = yaml.safe_load(ExpLogIn)
            ChildEntData = ExpLogYAMLData['ExpEntries']
            # Handling the case where there are no experiments in the current directory
            if ChildEntData is None:
                ChildEntData = []
            ChildEntities = [CurrentEntityList[EData['ID']-1] for EData in ChildEntData]

            # converting to list of EntityData objects
            ChildEntData = [
                EntityData(ChildEnt, EData['Title'], EData['Description'])
                for ChildEnt, EData in zip(ChildEntities, ChildEntData)
            ]
        except:
            errprint(ExplogMissingError(Entity))
            raise

    if not ChildEntData:
        ChildEntData = []

    return ChildEntData
