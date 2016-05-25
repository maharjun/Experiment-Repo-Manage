from RepoManagement.BasicUtils import errprint
from RepoManagement import LogProcessing as LP
import re
import colorama as cr
from colorclass import Color as ColorStr
from terminaltables import SingleTable
import textwrap


def getEntityContentStr(EntData, *args, Color=""):
    """
    This returns a string that represents the content of a particular entity. The
    *args represents the metadata that one wishes to add to the string. The possible
    values are: ['ID', 'ParentID', 'Type', 'Name', 'Path']

    The format of the return string is as below (between ---Start--- and ---End---)
    ---Start---
      <metadatakey1>: <metadatavalue1>
      <metadatakey2>: <metadatavalue2>
      <metadatakey3>: <metadatavalue3>

    # <Entity Title (in Color if asked)>

    <Entity Content as in file>
    ---End---

    Entity     - The ExpRepoEntity object for which the string is required
    EntData    - The EntityData representing data read from either folderlog.yml
                 or explog.yml corresponding to the current entity
    Color      - A colorama color prefix with which to print header. "" means
                 no color.
    """

    OutputLines = []
    # determine valid metadata
    if EntData.Type == 'Experiment':
        ValidMetadata = ['ID', 'ParentID', 'Type', 'Path']
    else:
        ValidMetadata = ['ID', 'ParentID', 'Type', 'Name', 'Path']

    # appending metadata
    args = [x for x in args if x in ValidMetadata]
    for MetaData in args:
        OutputLines.append("  {MetaDataKey}: {MetaDataValue}".format(
            MetaDataKey=MetaData,
            MetaDataValue=EntData.get(MetaData)
        ))
    if args:
        OutputLines.append("")

    # Appending Title
    ColorPrefix = Color
    ColorSuffix = cr.Style.RESET_ALL if Color else ""

    OutputLines.append("# {ColorPrefix}{TitleString}{ColorSuffix}".format(
        ColorPrefix=ColorPrefix,
        TitleString=EntData.Title if EntData.Title else '<untitled>',
        ColorSuffix=ColorSuffix
    ))

    # appending content
    StrippedDescription = EntData.Description.strip('\n')
    if StrippedDescription:
        OutputLines.append("")
        OutputLines.append(StrippedDescription)

    return "\n".join(OutputLines)


def getShortListString(EntityDataList, ParentType):
    """
    Assumption: The Entities in EntityDataList are either all of Directory Type or
    all of Experiment Type
    """
    Table = SingleTable([])
    Table.inner_heading_row_border = True
    Table.outer_border = False
    Table.inner_row_border = False
    Table.inner_footing_row_border = False

    if ParentType == 'IntermediateDir':
        Table.justify_columns = {0:'right', 1:'left', 2:'left'}
        Table.table_data.append(['ID', 'Folder Name', 'Folder Title'])
        # Add all IDs and Names.
        for E in EntityDataList:
            Table.table_data.append([
                ColorStr(cr.Fore.GREEN + cr.Style.BRIGHT + str(E.ID) + cr.Style.RESET_ALL),
                E.Name,
                ""
            ])
        # Add wrapped Titles
        MaxWidth = Table.column_max_width(2)
        for E, TableRow in zip(EntityDataList, Table.table_data[1:]):
            TableRow[2] = "\n".join(textwrap.wrap(E.Title, MaxWidth)) if E.Title else '<Untitled>'
    else:
        Table.justify_columns = {0:'right', 1:'left'}
        Table.table_data.append(['ID', 'Experiment Title'])
        # Adding IDs
        for E in EntityDataList:
            Table.table_data.append([
                ColorStr(cr.Fore.GREEN + cr.Style.BRIGHT + str(E.ID) + cr.Style.RESET_ALL),
                ''
            ])
        # Adding wrapped Titles
        MaxWidth = Table.column_max_width(1)
        for E, TableRow in zip(EntityDataList, Table.table_data[1:]):
            TableRow[1] = "\n".join(textwrap.wrap(E.Title, MaxWidth)) if E.Title else '<Untitled>'
    
    return Table.table


def getDirString(EntityID, CurrentEntityList, TopDir, RegexFilter="", FullText=False, DirDetails=False):
    """
    This function returns the string representing the contents of the Entity given
    by EntityID.

    NOTE: This function makes use of the fact that entity IDs are sequential and
    there are no breaks i.e. CurrentEntityList[i-1].ID = i. The format of the output
    is described in AlgosandShiz.m
    """

    try:
        CurrentEntity = CurrentEntityList[EntityID-1]
    except IndexError:
        errprint("\nEntity with ID {EntityID} is non-existant.".format(EntityID=EntityID))
        raise

    if CurrentEntity.Type not in ['IntermediateDir', 'ExperimentDir']:
        errprint("\nEntity with ID {EntityID} is not a directory.".format(EntityID=EntityID))

    DirData = LP.ReadEntityLog(CurrentEntity, TopDir)
    ChildEntData = LP.ReadChildrenData(CurrentEntity, CurrentEntityList, TopDir)

    # Filtering
    if RegexFilter:
        ChildEntData = [D for D in ChildEntData if re.match(r".*?"+RegexFilter, D['Title'])]

    OutputLines = []

    if DirDetails:
        OutputLines.append('Folder Details')
        OutputLines.append('==============')
        OutputLines.append('')
        OutputLines.append(
            getEntityContentStr(
                DirData,
                'ID', 'ParentID', 'Path', 'Type',
                Color=cr.Fore.GREEN+cr.Style.BRIGHT
            )
        )
        OutputLines.append('')
        OutputLines.append('Folder Contents')
        OutputLines.append('===============')

    if FullText:
        for D in ChildEntData:
            OutputLines.append('')
            OutputLines.append(getEntityContentStr(D, 'ID', 'Name', 'Type', Color=cr.Fore.YELLOW + cr.Style.BRIGHT))
            OutputLines.append('')
            OutputLines.append('#'*80)
    else:
        OutputLines.append('')
        OutputLines.append(getShortListString(ChildEntData, CurrentEntity.Type))

    return "\n".join(OutputLines)


def getShowString(EntityID, CurrentEntityList, TopDir, Details=False):
    """
    This Function returns the string representing the contents of the specified
    entity. If Details is Mentioned, The Following Details are mentioned as well.
    
      ID:
      ParentID:
      Type:
      Path:
    """

    CurrEntityData = LP.ReadEntityLog(CurrentEntityList[EntityID-1], TopDir)
    if Details:
        return getEntityContentStr(
            CurrEntityData,
            'ID', 'ParentID', 'Type', 'Path',
            Color=cr.Fore.GREEN+cr.Style.BRIGHT)
    else:
        return getEntityContentStr(
            CurrEntityData,
            Color=cr.Fore.GREEN+cr.Style.BRIGHT)
