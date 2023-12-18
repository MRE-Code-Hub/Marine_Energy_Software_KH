
from typing import Optional, Union
from pathlib import Path
from urllib.parse import urlparse

import yaml
from yaml import load, dump

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

StrOrPath = Union[str, Path]


def str_presenter(dumper, data):
    """configures yaml for dumping multiline strings
    Ref: https://stackoverflow.com/questions/8640959/how-can-i-control-what-scalar-form-pyyaml-uses-for-my-data"""
    if len(data) > 66 and not urlparse(data).scheme:
        return dumper.represent_scalar('tag:yaml.org,2002:str',
                                       data,
                                       style='>')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)
yaml.representer.SafeRepresenter.add_representer(str, str_presenter)


class IndentDumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(IndentDumper, self).increase_indent(flow, False)


def main(path: Optional[StrOrPath]):
    
    if path is not None:
        format_file(path)
        return
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    records_path = db_repo_path / "records"
    
    assert schema_path.is_file()
    assert records_path.is_dir()
    
    for p in records_path.iterdir():
        format_file(p)


def format_file(path: StrOrPath):
    
    with open(path, 'r') as f:
        data = load(f, Loader=Loader)
    
    with open(path, 'w') as f:
        dump(data,
             f,
             Dumper=IndentDumper,
             allow_unicode=True,
             default_flow_style=False,
             width=69)


if __name__ == "__main__":
    import sys
    path = None
    if len(sys.argv) > 1: path = sys.argv[1]
    main(path)
