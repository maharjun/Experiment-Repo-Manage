import yaml

YAMLKey_SpaceRepString = '`!#'

class ExpRepoEntity:
    def __init__(self, ID=None, ParentID=None, Type=None, Path=None):
        
        if ID.__class__ == str:
            self.ID = int(ID,16)
        elif ID.__class__ == int:
            self.ID = int(ID)
        else:
            self.ID = None
        
        if ParentID.__class__ == str:
            self.ParentID = int(ParentID,16)
        elif ParentID.__class__ == int:
            self.ParentID = int(ParentID)
        else:
            self.ParentID = None
        
        if Type in ['IntermediateDir', 'ExperimentDir', 'Experiment']:
            self.Type = Type
        
        self.Path = Path
    
    def __int__(self):
        return int(self.data)

    def __str__(self):
        return (
            "ID      : {0:0{1}x}\n".format(self.ID      , 32) +
            "ParentID: {0:0{1}x}\n".format(self.ParentID, 32) +
            "Type    : {0}\n".format(self.Type) +
            "Path    : {0}\n".format(self.Path)
        )


def ExpRepoEntity_representer(dumper, Entity, rep_str="`!#"):
    ExpRepoEntityMembs = []
    
    ExpRepoEntityMembs += [('ID'      , "{0:0{1}x}".format(Entity.ID, 32))]
    ExpRepoEntityMembs += [('ParentID', "{0:0{1}x}".format(Entity.ParentID, 32))]
    ExpRepoEntityMembs += [('Type'    , Entity.Type)]
    ExpRepoEntityMembs += [('Path'    , Entity.Path)]
    
    keyWidth = max([len(k[0]) for k in ExpRepoEntityMembs])
    AlignedMembs = [(k+rep_str*(keyWidth-len(k)), v) for k,v in ExpRepoEntityMembs]
    
    return dumper.represent_mapping('tag:yaml.org,2002:map', AlignedMembs)

# def dict_representer(dumper, data, rep_str=''):
#     keyWidth = max([len(k) for k,v in data.keys()])
#     aligned = {k+rep_str*(keyWidth-len(k)):v for k,v in data.iteritems()}
#     # .items() convers aligned into a list of tuples in the order of insertion
#     return dumper.represent_mapping('tag:yaml.org,2002:map', aligned.items())


def str_presenter(dumper, data):
    if len(data.splitlines()) > 1:  # check for multiline string
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)


yaml.add_representer(str, str_presenter)
yaml.add_representer(ExpRepoEntity, lambda dumper,Entity: ExpRepoEntity_representer(dumper,Entity,YAMLKey_SpaceRepString))
# yaml.add_representer(dict,lambda dumper,data: dict_representer(dumper,data,YAMLKey_SpaceRepString))


def PrettyYAMLDump(data, stream=None):
    YamlDump = yaml.dump(data, default_flow_style=False)
    YamlDump = YamlDump.replace(": |-", ": |")
    YamlDump = YamlDump.replace("\n- ", "\n\n- ")
    YamlDump = YamlDump.replace(YAMLKey_SpaceRepString, ' ')
    
    if stream is not None:
        stream.write(YamlDump)
    return YamlDump
