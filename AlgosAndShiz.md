## ImportantRandom Info

To enable stdout redirection in windows, must set some registry key. 

http://stackoverflow.com/questions/3018848/cannot-redirect-output-when-i-run-python-script-on-windows-using-just-scripts-n

##  Algo for readme generations for experiment readme.

###   Format of explog.yml .

```yaml
ExpFolderID: <The Unique 32-bit ID of the Experiment Folder>
NumberofEntries: <The number of experiment entities stored>
ExpEntries:
- ID          : <The Unique 32-bit ID assigned to Current Experiment>
  Title       : <Title Describing Experiment>
  Description : |
    The Detailed description of the experiment,
    including any special instructions apart from the
    setup script. This is to be written in Markdown 
    (level-3 header onwards).
    
    Roughly break it down into 5 Steps
    
    1. Motivation and Objective
    2. Procedure
    3. Observations
    4. Inference
    5. Future Work

## End of Experiment <ID> ##################<upto 100 chars>#####

- ID          :
  Title       :
  Description :
  
  # And So On
  # ...
 
```

### Format of folderlog.yml

```yaml
FolderID: <The Unique ID of the Folder>
ParentFolderID: <The Unique ID of the Parent Folder>
FolderTitle: <A short title describing contents>
FolderDescription: |
  The Detailed description of the contents of the folder. Note that
  it should NOT be an element by element description of its contents.
  Rather it should be something that gives an overall description of 
  the kind of entities (experiments/directories) that it contains.
  (You can use Markdown level-3 header onwards).
```

###   Committing Algo

####    Prerequisites

One MUST be on an UPDATED master branch (there will be no pull attempted by the program itself, this is because there is a potential for conflicts in the session. i.e. it is possible that the folder you are booking, which is new in the current directory, is already booked in the main repository). 

It is possible that you're on an updated master branch, but before committing 
changes, the upstream branh moves ahead. In such case, you will have no choice 
but to pull the branch again and perform the bookings again (Manually for now. 
Will try to ease this later)

Before the commit procedure, there must be no changes in the working tree / index. (i.e. you would be advised to run reset --hard before you perform bookings in case you have some other changes pending.)

####    High level Algo

    Initialize EntityList from Entities.yml file in RepoManagement
    
    ForwardTree = getForwardTree(EntityList)
    EntityDict  = {e.ID:e for e in EntityList}
    ProcessFolder(Root, EntityDict, ForwardTree)
    
    define ProcessFolder(entity, EntityDict, ForwardTree):
        if entity is intermediate folder,
            if folder readme has not been created,
                create folder readme.
            for each child folder,
                ProcessEntity(child folder)
        else if entity is experiment folder,
            if folder readme has not been created,
                create folder readme.
            ProcessExperimentsIn(Current Folder).
    
    define ProcessExperimentsIn(entity, EntityDict, ForwardTree):
        if Folder is not an ExperimentDir,
            return error message
        else,
            EntPath = path of entity.
            if explog.yml exists,
                read explog.yml into ExpList
            else,
                ExpList = []


###   Editing Algos:

Various features required:

Ability to browse through experiments:

1.  Ability to list IDs and Titles of all experiments in a folder. 
    (like dir/ls)
2.  Ability to get the text of a particular experiment or folder 
    (like git show)
3.  Ability to edit an experiment. Figure out a way to make this secure. For 
    now, just enable that any experiment / folder can be edited after printing 
    a confirmation message.

3 commands required dir/ls, show, edit


1.  ls/dir:
    
    syntax:

      ls <ID/Path> --fulltext --dirdetails

2.  show:
    
    syntax:

      show <ID/Path> --details

3.  edit:

    syntax:

      edit <ID/Path>

####    The ls command.

The ls command has an alias `dir`

dir <ID/Path> --fulltext --dirdetails --filter <regexp>

#####     Output Format

```
Folder Details
==============

  ID      : <Directory ID>
  ParentID:
  Path    : <Directory Path>
  Type    : <Directory Type>

# <Directory Title>

<Directory Description content>

Folder Contents
===============
<without --fulltext>
<In case of intermediate directory>
ID    Folder Name  Folder Title
<ID1> <Name1>      Title1
<ID2> <Name2>      Title2
<ID3> <Name3>      Title3

<In case of Experiment Directory>
ID    Experiment Title
<ID1> Title1
<ID2> Title2
<ID3> Title3

<with --fulltext>

  ID  :
  Name: # this line is only there if there is a folder
  Type: 

# Title

Content

####################################################
.
.
.

```
