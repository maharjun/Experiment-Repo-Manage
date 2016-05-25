import textwrap


class ExpRepoEntity:
    """
    This class basically defines the structure for the entries in the
    main entity database. An entity is either a directory (intermediate
    or experiment), or an experiment. This class simplifies the procedures
    of converting between the pyYaml generated dicts, and the internal
    representation of entities. It also has the output function coded.
    """

    def __init__(self, ID=None, ParentID=None, Type=None, Path=None):
        
        if ID.__class__ == str:
            self.ID = int(ID)
        elif ID.__class__ == int:
            self.ID = int(ID)
        else:
            self.ID = None
        
        if ParentID.__class__ == str:
            self.ParentID = int(ParentID)
        elif ParentID.__class__ == int:
            self.ParentID = int(ParentID)
        else:
            self.ParentID = None
        
        if Type in ['IntermediateDir', 'ExperimentDir', 'Experiment']:
            self.Type = Type
        
        self.Path = Path if Path is not None else ''
    
    def getYAMLElemList(self):
        """
        This function returns a list containing the strings (currently 4)
        representing the value of each variable in the YAML form. look at
        code below
        """
        YamlOutput = []
        YamlOutput += ["ID      : {0}".format(self.ID      , 32)]
        YamlOutput += ["ParentID: {0}".format(self.ParentID, 32)]
        YamlOutput += ["Type    : {0}".format(self.Type)]
        YamlOutput += ["Path    : {0}".format(self.Path)]
        return YamlOutput

    def __int__(self):
        return int(self.data)

    def __str__(self):
        return (
            "ID      : {0}\n".format(self.ID      , 32) +
            "ParentID: {0}\n".format(self.ParentID, 32) +
            "Type    : {0}\n".format(self.Type) +
            "Path    : {0}\n".format(self.Path)
        )


def getPrettyYAMLDump(EntityList):
    """
    This function returns a string that basically corresponds to the
    formatted (see formatting in code) dump of data. data must be an
    array of ExpRepoEntity objects. The objects are formatted as though
    part of an array
    """

    # check if data is an array of ExpRepoEntity objects
    if any([x.__class__ != ExpRepoEntity for x in EntityList]):
        print("The data to be dumped must be an array of ExpRepoEntity objects")
        raise ValueError

    EntityYAMLStrList = []
    
    # adding '- ' before the first member and tabbing the
    # others by 2 spaces.
    # adding an empty line followed by a series of '#'
    # followed by a newline
    for entity in EntityList:
        CurrEntityMembs      = entity.getYAMLElemList()
        CurrEntityMembs[0]   = '- ' + CurrEntityMembs[0]
        CurrEntityMembs[1:]  = ['  ' + Elems for Elems in CurrEntityMembs[1:]]
        CurrEntityMembs.append('')
        CurrEntityMembs.append('#'*100)
        CurrEntityMembs.append('')

        EntityYAMLStrList.append("\n".join(CurrEntityMembs))

    PrettyYAMLDump = "\n".join(EntityYAMLStrList)
    return PrettyYAMLDump


def FlushData(Stream, EntityList):
    """
    This writes the given EntityList into the stream specified.
    """
    
    with Stream as Fout:

        # Writing the Number of Entities
        # and the entity data

        Fout.write(textwrap.dedent(
            """\
            NumEntities: {EntityCount}

            EntityData:

            """.format(EntityCount=len(EntityList))
        ))
        if EntityList:
            Fout.write(getPrettyYAMLDump(EntityList))
