import re
import ViewEntities
from os import path
from BasicUtils import errprint

isValidContentStr = r"""
    # A Valid Entity string is as:
    # A Title Line is as below
    (?:
        # Either starts with a '# ' followed by spaces and non-space content,
        # Note '.' doesn't match newline
        \#[ ]+(\S.*)$ |
        # Or, set (0 or more) of spaces followed by non-space characters, without
        # the first character being a #, followed by a line containing only equals
        # (and at least 2 equals)
        (?!\#)[ ]*(\S.*)\r?\n
        ===*(?=\s)[ ]*$
    )
    # Content as below.
    (
        # A sequence of lines. each line is a newline followed by content
        # terminated by end of string. The content must either start with
        # a non-hash or '#' that is followed by another '#'. This is to
        # enforce that only Headers of LEVEL greater than 2
        (?:
            \r?\n
            (?:
                (?:[^\#]|\#(?=\#)).*
            )?
        )*
        \Z
    )
"""
isValidContentRE = re.compile(isValidContentStr, re.VERBOSE | re.MULTILINE)


def getExperimentEntry(EntityData):
    """
    This returns a single entry corresponding to the Experiment Entity
    referred to by EntityData. The returned string is given below
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

    # Validate that EntityData actually corresponds to an Experiment Entity
    if EntityData['Type'] != 'Experiment':
        errprint("\nThe Entity Data does not represent the data of an experiment")
        raise ValueError

    OutputLines = []
    OutputLines.append("")
    OutputLines.append("- ID         : {ID}".format(ID=EntityData['ID']))
    OutputLines.append("  Title      : {Title}".format(Title=EntityData['Title']))
    OutputLines.append("  Description: |-2")
    OutputLines += ["    "+Line for Line in EntityData['Description'].splitlines()]
    OutputLines.append("")
    OutputLines.append(
        "{0:#<100}".format("## End of Experiment {UID} ".format(UID=EntityData['ID'])))

    return "\n".join(OutputLines)


def getFolderEntry(EntityData):
    """
    This returns a single entry corresponding to the Directory Entity
    referred to by EntityData. The returned string is given below
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

    if EntityData['Type'] not in ['IntermediateDir', 'ExperimentDir']:
        errprint('\nThe given EntityData does not represent the data of a directory')
        raise ValueError

    OutputLines = []
    
    OutputLines.append("FolderID         : {UID}".format(UID=EntityData['ID']))
    OutputLines.append("ParentFolderID   : {UID}".format(UID=EntityData['ParentID']))
    OutputLines.append("FolderType       : {Type}".format(Type=EntityData['Type']))
    OutputLines.append("FolderTitle      : {Title}".format(Title=EntityData['Title']))
    OutputLines.append("FolderDescription: |-2")
    OutputLines += ["  "+Line for Line in EntityData['Description'].splitlines()]
    OutputLines.append("")

    return "\n".join(OutputLines)


def EditEntity(EntityID, CurrentEntityList, TopDir, ContentString):
    """
    Edits the entry corresponding to the Entity referred to by EntityID.
    The ContentString must contain as its first (non-empty) line, the
    title of the entity (It MUST be formatted as a level-1 markdown
    header). Else, an exception will be raised.
    """

    # Strip newlines
    ContentString = ContentString.strip("\r\n")

    # Evaluate Title
    A = isValidContentRE.match(ContentString)
    if A:
        Title = A.group(1).strip() if A.group(1) is not None else A.group(2).strip()
        Body = A.group(3).strip('\n')
    elif ContentString:
        errprint(
            "\nThe given content string does not appear to be valid. The following regex must"
            "\nbe satisfied:"
            "\n"
            "\n{ContentRegex}".format(ContentRegex=isValidContentStr))
        raise ValueError
    else:
        errprint("\nAborting Edit because of empty content string.")
        raise ValueError

    # Calculate Entity
    try:
        Entity = CurrentEntityList[EntityID-1]
    except IndexError:
        errprint("\nNo Entity with ID {ID} has been booked.".format(ID=EntityID))
        raise

    # Get current EntityData for the booked entity
    EntityData = ViewEntities.ReadEntityLog(Entity, TopDir)

    if Entity.Type == 'Experiment':
        # Read the explog file
        ExpLogPath = path.join(TopDir, Entity.Path, 'explog.yml')
        try:
            with open(ExpLogPath) as ExpLogIn:
                ExpLogText = ExpLogIn.read()
        except:
            errprint(ViewEntities.ExplogMissingError(Entity))
            raise

        # Split the explog file around the current experiment
        # entry
        CurrentExpEntry = getExperimentEntry(EntityData)
        SplitExpLogText = ExpLogText.split(CurrentExpEntry)

        # Modify data pertaining to the experiment entity
        EntityData['Title'] = Title
        EntityData['Description'] = Body

        # Rejoin the explog text around the new (edited) experiment entity
        NewExpLogText = getExperimentEntry(EntityData).join(SplitExpLogText)

        # Write the new data
        try:
            with open(ExpLogPath, 'w') as ExpLogOut:
                ExpLogOut.write(NewExpLogText)
        except:
            errprint("\nUnable to write to {explogpath}".format(explogpath=ExpLogPath))
            raise
    else:
        EntityData['Title'] = Title
        EntityData['Description'] = Body
        FolderLogPath = path.join(TopDir, Entity.Path, 'folderlog.yml')

        NewFolderLogText = getFolderEntry(EntityData)
        # Write the new data
        try:
            with open(FolderLogPath, 'w') as FolderLogOut:
                FolderLogOut.write(NewFolderLogText)
        except:
            errprint("\nUnable to write to {folderlogpath}".format(folderlogpath=FolderLogPath))
            raise
