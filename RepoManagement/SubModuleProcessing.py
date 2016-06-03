import os
from git import Repo, GitCommandError
import yaml
import copy

from RepoManagement.GetRootDirectory import getRootDirectory
from RepoManagement.BasicUtils import errprint, conprint

# Submodule attribut
#   1.  SubModuleReference = <list of submodule names listing the
#                             ancestory of the given submodule>
#   3.  Commit SHA = <commit to which you wish to initialize it>
#   3.  Update Sub-SubModules = True/False


class SubModuleEntry:
    SubModuleReference = None
    CommitSHA = None
    SubSubModuleUpdate = None

    def __init__(self, **kwargs):
        """
        Possible ArgumentS:
        
        SubModuleReference ||
        [ TopRepo,
          AddressType='Path',
          AddressString]
        CommitSHA='',
        SubSubModuleUpdate=True,
        """
        if 'SubModuleReference' in kwargs:
            self.SubModuleReference = kwargs['SubModuleReference']
        elif 'AddressString' in kwargs and 'TopRepo' in kwargs:
            AddressType = kwargs['AddressType'] if 'AddressType' in kwargs else 'Path'
            self.SubModuleReference = getSubModuleHeirarchy(kwargs['TopRepo'], AddressType, kwargs['AddressString'])
        else:
            errprint("\nNeed either SubModuleReference OR (AddressType and AddressString)")
            raise(TypeError)

        self.CommitSHA = kwargs['CommitSHA'] if 'CommitSHA' in kwargs else ''

        self.SubSubModuleUpdate = kwargs['SubSubModuleUpdate'] if 'SubSubModuleUpdate' in kwargs else True


def getSubModuleEntryText(SubModuleEntry):
    """
    The following format is followed (between ---Begin--- ---End---)
    
    ---Begin---
    - AddressType: <Address Type either 'Name' or 'Path'>
      AddressString: <Address String>
      CommitSHA: <SHA of commit>
      SubSubModuleUpdate: <whether to update sub-submodules 'yes' or 'no'>

    ---End---
    """

    OutputLines = []
    OutputLines.append("- SubModuleReference: ")
    for SubModName in SubModuleEntry.SubModuleReference:
        OutputLines.append("  - {SubModName}".format(SubModName=SubModName))
    OutputLines.append("  CommitSHA: '{CommitSHA}'".
                       format(CommitSHA=SubModuleEntry.CommitSHA))
    OutputLines.append("  SubSubModuleUpdate: {SubSubModuleUpdate}".
                       format(SubSubModuleUpdate='yes'
                              if SubModuleEntry.SubSubModuleUpdate else 'no'))
    OutputLines.append("")
    return "\n".join(OutputLines)


def getSubModuleHeirarchy(TopRepo, AddressType, AddressString):
    """
    This function finds the submodule of the given address and returns it.
    """
    
    if AddressType.lower() == 'name':
        # Get list of submodules in TopRepo
        try:
            TopRepo.submodule(AddressString)
        except ValueError:
            errprint("\nThere is no submodule of the following name:")
            errprint("\n  {SubModuleName}".format(SubModuleName=AddressString))
            raise
        return [AddressString]
    elif AddressType.lower() == 'path':
        # Find all submodules whose paths are ancestors of the specified path
        def isAnc(AncPath, OtherPath):
            AncPath   = os.path.normpath(AncPath)
            OtherPath = os.path.normpath(OtherPath)
            return os.path.commonpath([AncPath, OtherPath]) == AncPath

        PathUptoNow = ''
        CurrentRepo = TopRepo
        SubModuleHeirarchy = []
        CurrentSubMod = None
        while PathUptoNow != AddressString:
            if CurrentSubMod:
                if not CurrentSubMod.module_exists():
                    CurrentRepo.git.submodule('update', '--init', CurrentSubMod.path)
                CurrentRepo = CurrentSubMod.module()
            
            try:
                SubModList = [x for x in CurrentRepo.submodules if isAnc(os.path.join(PathUptoNow, x.path), AddressString)]
            except:
                errprint("\nThere is some inconsistency in the state of submodules in the repository.")

            if SubModList:
                CurrentSubMod = SubModList[0]
                PathUptoNow = os.path.join(PathUptoNow, CurrentSubMod.path)
                SubModuleHeirarchy.append(CurrentSubMod.name)
            else:
                errprint('\nThere is no submodule by the following path:')
                errprint('\n  {SubModulePath}'.format(SubModulePath=AddressString))
                raise(ValueError)

        return SubModuleHeirarchy


def readSubModuleFile(FilePath):
    try:
        with open(FilePath) as Fin:
            SubModuleEntryData = yaml.safe_load(Fin)
    except:
        errprint("\nThe following file is not a valid YAML File")
        errprint("\n  {SubModuleYaml}".format(SubModuleYaml=FilePath))

    SubModuleEntryData = SubModuleEntryData if SubModuleEntryData else []
    SubModuleEntries = [SubModuleEntry(**x) for x in SubModuleEntryData]
    return SubModuleEntries


def AddSubmoduleEntry(Path,
                      SubModAddressType,
                      SubModAddressString,
                      SubSubModuleUpdate=False):
    # fix path
    Path = os.path.abspath(Path)
    TopRepo = Repo(getRootDirectory(Path))

    # check if path exists
    if not os.path.isdir(Path):
        errprint("The Following Path does not exist:")
        errprint("\n {Path}".format(Path=Path))
        raise(ValueError)

    # Initialize Submodule Repository to add.
    NewSubModuleEntry = SubModuleEntry(TopRepo=TopRepo,
                                       AddressType=SubModAddressType,
                                       AddressString=SubModAddressString,
                                       CommitSHA='',
                                       SubSubModuleUpdate=SubSubModuleUpdate)

    # Check if submodules.yml file already exists
    # Create file if not exists
    SubModuleFile = os.path.join(Path, 'submodules.yml')
    if not os.path.isfile(SubModuleFile):
        with open(SubModuleFile, 'w') as Fout:
            Fout.write("")

    # get Submodule entries
    ExistingSubModEntries = readSubModuleFile(SubModuleFile)

    # Check if the current SubModule already has an entry
    SubModuleExists = bool([x
                            for x in ExistingSubModEntries
                            if x.SubModuleReference == NewSubModuleEntry.SubModuleReference])
    if SubModuleExists:
        conprint("\nSubModule Already Exists")
    else:
        ExistingSubModEntries.append(NewSubModuleEntry)
        SubModuleFileLines = [getSubModuleEntryText(x) for x in ExistingSubModEntries]
        with open(SubModuleFile, 'w') as Fout:
            Fout.write("\n".join(SubModuleFileLines))


def getSubModule(SubModuleEntry, TopRepo, Force=False):
    """
    Returns the SubModule object corresponding to the given SubModuleEntry
    """
    CurrentSubMod = None
    CurrentRepo = TopRepo
    PathUptoNow = ''
    for SubModName in SubModuleEntry.SubModuleReference:
        if CurrentSubMod:
            PathUptoNow = os.path.join(PathUptoNow, CurrentSubMod.path)
            if not CurrentSubMod.module_exists():
                if Force:
                    CurrentRepo.git.submodule('update', CurrentSubMod.path, init=True)
                else:
                    errprint("\nThe Following SubModule repository is not created, unable to "
                             "retrieve sub-submodule. Alternatively, use Force=True to force "
                             "update")
                    errprint("\n  {CurrentSubModPath}".format(CurrentSubModPath=PathUptoNow))
                    raise(ValueError)
            CurrentRepo = CurrentSubMod.module()
        CurrentSubMod = CurrentRepo.submodule(SubModName)

    return CurrentSubMod


def assignSubModuleCommit(SubModuleEntry, TopRepo):
    """
    This function assumes that the SubModuleEntry represents a valid submodule
    Else Exception is thrown when submodule cannot be found.
    """
    
    SubModuleObject = getSubModule(SubModuleEntry, TopRepo)
    if SubModuleObject.module_exists():
        SubModuleSHA = SubModuleObject.module().head.commit.hexsha
    else:
        SubModuleSHA = SubModuleObject.hexsha

    SubModuleEntry = copy.deepcopy(SubModuleEntry)
    SubModuleEntry.CommitSHA = SubModuleSHA
    return SubModuleEntry


def RetrieveSubModuleCommits(Path):
    """
    Picks the commit versions. If it is able to find the commit versions for all the
    """

    # fix path
    Path = os.path.abspath(Path)
    TopRepo = Repo(getRootDirectory(Path))

    # Check if path exists
    if not os.path.isdir(Path):
        errprint("The Following Path does not exist:")
        errprint("\n {Path}".format(Path=Path))
        raise(ValueError)

    SubModuleFile = os.path.join(Path, 'submodules.yml')
    if os.path.isfile(SubModuleFile):
        SubModuleEntries = readSubModuleFile(SubModuleFile)
        NewSubModuleEntries = []
        for SubMod in SubModuleEntries:
            try:
                NewSubModuleEntries.append(assignSubModuleCommit(SubMod, TopRepo))
            except ValueError:
                errprint("\nCould not get the commit of SHA The following submodule:")
                errprint("")
                errprint(getSubModuleEntryText(SubMod).strip("\r\n"))
                raise
        NewSubModuleEntriesText = "\n".join([getSubModuleEntryText(SubMod)
                                             for SubMod in NewSubModuleEntries])
        with open(SubModuleFile, 'w') as Fout:
            Fout.write(NewSubModuleEntriesText)
    else:
        errprint("\nThe file submodules.yml does not exist in the given path:")
        errprint("\n  {Path}".format(Path=Path))


def UpdateSubModules(Path):

    # fix path
    Path = os.path.abspath(Path)
    TopRepo = Repo(getRootDirectory(Path))

    # Check if path exists
    if not os.path.isdir(Path):
        errprint("The Following Path does not exist:")
        errprint("\n {Path}".format(Path=Path))
        raise(ValueError)

    SubModuleFile = os.path.join(Path, 'submodules.yml')

    if os.path.isfile(SubModuleFile):
        SubModuleEntries = readSubModuleFile(SubModuleFile)
        for SubModEntry in SubModuleEntries:
            CurrentSubMod = getSubModule(SubModEntry, TopRepo, Force=True)
            if not CurrentSubMod.module_exists():
                CurrentSubMod.repo.git.submodule('update', "--init", CurrentSubMod.path)
            CurrentModule = CurrentSubMod.module()

            # Checkout commit
            try:
                CurrentModule.git.checkout(SubModEntry.CommitSHA)
            except GitCommandError as Err:
                errprint("\n{ErrorMessage}".format(ErrorMessage=Err.encode('utf-8')))
                errprint("\nCheckout of Following Module and commit failed:")
                errprint("")
                errprint(getSubModuleEntryText(SubModEntry).strip("\r\n"))
                raise

            # if SubSubModules need to be updated then do so.
            if SubModEntry.SubSubModuleUpdate:
                try:
                    CurrentModule.git.submodule('update', '--init')
                except GitCommandError as Err:
                    errprint("\n{ErrorMessage}".format(Err.args[0]))
                    errprint("\nUpdating of Sub-SubModules of Following Module and commit failed:")
                    errprint("")
                    errprint(getSubModuleEntryText(SubModEntry).strip("\r\n"))
                    raise
    else:
        errprint("\nThe file submodules.yml does not exist in the given path:")
        errprint("\n  {Path}".format(Path=Path))
