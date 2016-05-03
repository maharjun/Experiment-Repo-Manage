import re
from os import path
import BasicUtils as BU
import LogProcessing as LP
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
        errprint(
            "\nThe content string is empty. Does this mean that you wish to reset the log"
            "\ncorresponding to the entity {ID}?".format(ID=EntityID))
        EditConfirm = BU.getNonEmptyInput("Reset Confirm (<anything else>/n)")
        if EditConfirm in ['n', 'N']:
            raise ValueError
        else:
            Title = ''
            Body = ''

    # Calculate Entity
    try:
        Entity = CurrentEntityList[EntityID-1]
    except IndexError:
        errprint("\nNo Entity with ID {ID} has been booked.".format(ID=EntityID))
        raise

    # Get current EntityData for the booked entity
    RelEntityData = LP.ReadEntityLog(Entity, TopDir)

    if Entity.Type == 'Experiment':
        # Read the explog file
        ExpLogPath = path.join(TopDir, Entity.Path, 'explog.yml')
        try:
            with open(ExpLogPath) as ExpLogIn:
                ExpLogText = ExpLogIn.read()
        except:
            errprint(LP.ExplogMissingError(Entity))
            raise

        # Split the explog file around the current experiment
        # entry
        CurrentExpEntry = LP.getExperimentEntry(RelEntityData)
        SplitExpLogText = ExpLogText.split(CurrentExpEntry)

        # Modify data pertaining to the experiment entity
        RelEntityData = LP.EntityData(
            Entity,
            Title=Title,
            Description=Body)

        # Rejoin the explog text around the new (edited) experiment entity
        NewExpLogEntry = LP.getExperimentEntry(RelEntityData)
        NewExpLogText  = NewExpLogEntry.join(SplitExpLogText)

        # Write the new data
        try:
            with open(ExpLogPath, 'w') as ExpLogOut:
                ExpLogOut.write(NewExpLogText)
        except:
            errprint("\nUnable to write to {explogpath}".format(explogpath=ExpLogPath))
            raise
    else:
        RelEntityData = LP.EntityData(
            Entity,
            Title=Title,
            Description=Body)
        FolderLogPath = path.join(TopDir, Entity.Path, 'folderlog.yml')

        NewFolderLogText = LP.getFolderEntry(RelEntityData)
        # Write the new data
        try:
            with open(FolderLogPath, 'w') as FolderLogOut:
                FolderLogOut.write(NewFolderLogText)
        except:
            errprint("\nUnable to write to {folderlogpath}".format(folderlogpath=FolderLogPath))
            raise
