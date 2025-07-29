# src/helpers/yaml.py
import yaml

from collections import OrderedDict


def represent_ordereddict(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', data.items())


class OrderedDictDumper(yaml.Dumper):
    def __init__(self, *args, **kwargs):
        yaml.Dumper.__init__(self, *args, **kwargs)
        self.add_representer(OrderedDict, type(self).represent_ordereddict)

    represent_ordereddict = represent_ordereddict
