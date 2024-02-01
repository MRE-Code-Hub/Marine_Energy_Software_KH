
import json
import argparse
from typing import Any, Optional, Union
from pathlib import Path
from urllib.parse import urlparse

import yaml
import ruamel.yaml
import jsonref
from yaml import load, dump
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import FoldedScalarString

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

StrOrPath = Union[str, Path]

LONG_PROPS = ["Description"]
SHORT_TEXT = "Hello world!"
LONG_TEXT = (
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat. Duis aute irure dolor in reprehenderit in voluptate "
    "velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
    "occaecat cupidatat non proident, sunt in culpa qui officia deserunt "
    "mollit anim id est laborum."
    "\n\n"
    "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod "
    "tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim "
    "veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea "
    "commodo consequat. Duis aute irure dolor in reprehenderit in voluptate "
    "velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint "
    "occaecat cupidatat non proident, sunt in culpa qui officia deserunt "
    "mollit anim id est laborum."
)


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


def main():
    
    parser = argparse.ArgumentParser(
        description="Create templates and format records")
    subparsers = parser.add_subparsers(help='sub-command help',
                                       required=True)
    
    setup_format(subparsers)
    setup_template(subparsers)
    setup_glossary(subparsers)
    
    args = parser.parse_args()
    args.func(args)


def setup_format(subparsers):
    parser = subparsers.add_parser(
        'format',
        help='format records')
    parser.add_argument('file', nargs='?')
    parser.set_defaults(func=lambda args: formatter(args.file))


def setup_template(subparsers):
    parser = subparsers.add_parser(
        'template',
        help='create template record')
    parser.add_argument('--dir', default=".")
    parser.add_argument('--name', default="template.yaml")
    parser.set_defaults(func=lambda args: make_template(args.dir, args.name))


def setup_glossary(subparsers):
    parser = subparsers.add_parser(
        'glossary',
        help='create glossary')
    parser.add_argument('--dir', default=".")
    parser.add_argument('--name', default="dictionary.json")
    parser.set_defaults(func=lambda args: make_glossary(args.dir, args.name))


def formatter(path: Optional[StrOrPath]):
    
    if path is not None:
        with open(path, 'r') as f:
            data = load(f, Loader=Loader)
        dump_formatted(data, p)
        return
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    records_path = db_repo_path / "records"
    
    assert schema_path.is_file()
    assert records_path.is_dir()
    
    for p in records_path.iterdir():
        with open(p, 'r') as f:
            data = load(f, Loader=Loader)
        dump_formatted(data, p)


def dump_formatted(data: dict[str, Any],
                   path: StrOrPath):
    
    with open(path, 'w') as f:
        dump(data,
             f,
             Dumper=IndentDumper,
             allow_unicode=True,
             default_flow_style=False,
             width=69)


def make_template(template_dir: StrOrPath = ".",
                  template_name: str = "template.yaml"):
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    assert schema_path.is_file()
    
    with open(schema_path, 'r') as f:
        schema = load(f, Loader=Loader)
    
    json_schema = json.dumps(schema)
    template, descriptions = get_template(json_schema)
    
    template_path = Path(template_dir) / template_name
    dump_commented(template_path, schema, template, descriptions)


def dump_commented(path: StrOrPath,
                   schema: dict[str, Any],
                   data: dict[str, Any],
                   descriptions: dict[str, str]):
    
    cmap = CommentedMap(data)
    
    for k, v in descriptions.items():
        if k in schema['required']:
            msg = "REQUIRED: "
        else:
            msg = "OPTIONAL: "
        msg += v
        cmap.yaml_set_comment_before_after_key(k, before=msg)
    
    yaml = ruamel.yaml.YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 69
    
    with open(path, 'w') as f:
        yaml.dump(cmap, f)


def get_template(json_schema: str) -> tuple[dict[str, Any],
                                            dict[str, str]]:
    
    schema_deref = jsonref.loads(json_schema)
    template = {}
    descriptions = {}
    
    for k, v in schema_deref['properties'].items():
        _add_prop_to_template(template, k, v)
        if "description" in v:
            descriptions[k] = v["description"]
    
    return template, descriptions


def _add_prop_to_template(capture, k, v):
    
    if 'oneOf' in v:
        _add_multi_to_template(capture, k, v, 'oneOf')
    elif 'anyOf' in v:
        _add_multi_to_template(capture, k, v, 'anyOf')
    elif 'array' in v['type']:
        if 'enum' in v['items']:
            capture[k] = v['items']['enum']
        else:
            raise RuntimeError(f"Unrecognised items in {(v['items'])} for {k}")
    elif v['type'] == 'string':
        _add_string_to_template(capture, k, v)
    else:
        raise RuntimeError(f"Unrecognised type ({(v['type'])}) for {k}")


def _add_string_to_template(capture, k, v):
    
    if 'format' in v:
        if v['format'] == 'uri':
            capture[k] = 'https://example.com/'
            return
    elif 'enum' in v:
        capture[k] = v['enum'][0]
        return
    
    if k in LONG_PROPS:
        capture[k] = FoldedScalarString(LONG_TEXT)
    else:
        capture[k] = SHORT_TEXT


def _add_multi_to_template(capture, k, v, pk):
    
    vpk = v[pk]
    types = {d['type']: i for i, d in enumerate(vpk)}
    
    if 'array' in types:
        sub = vpk[types['array']]
        if 'anyOf' in sub['items']:
            capture[k] = []
            for subsub in sub['items']['anyOf']:
                if 'enum' in subsub:
                    capture[k].extend(subsub['enum'])
                if 'properties' in subsub:
                    for sk, sv in subsub['properties'].items():
                        sd = {}
                        _add_prop_to_template(sd, sk, sv)
                        if sk in capture[k]:
                            capture[k].remove(sk)
                        capture[k].append(sd)
        elif 'enum' in sub['items']:
            capture[k] = sub['items']['enum']
        elif 'type' in sub['items'] and sub['items']['type'] == 'string':
            capture[k] = [SHORT_TEXT]
        else:
            msg = f"Unrecognised items in {(sub['items'])} for {k}"
            raise RuntimeError(msg)
    elif 'string' in types:
        sub = vpk[types['string']]
        _add_string_to_template(capture, k, sub)
    else:
        msg = f"Unrecognised types ({types}) for {k}"
        raise RuntimeError(msg)


def make_glossary(template_dir: StrOrPath = ".",
                  glossary_name: str = "dictionary.json"):
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    assert schema_path.is_file()
    
    with open(schema_path, 'r') as f:
        schema = load(f, Loader=Loader)
    
    json_schema = json.dumps(schema)
    glossary = get_glossary(json_schema)
    
    template_path = Path(template_dir) / glossary_name
    
    with open(template_path, 'w') as f:
        json.dump(glossary, f, indent=4)


def get_glossary(json_schema: str) -> list[dict[str, Any]]:
    
    schema_deref = jsonref.loads(json_schema)
    glossary = []
    
    for k, v in schema_deref['properties'].items():
        _add_prop_to_glossary(glossary, k, v)
    
    return glossary


def _add_prop_to_glossary(capture, k, v):

    if 'oneOf' in v:
        _add_multi_to_glossary(capture, k, v, 'oneOf')
    elif 'anyOf' in v:
        _add_multi_to_glossary(capture, k, v, 'anyOf')
    elif 'array' in v['type']:
        if 'enum' in v['items']:
            record = {"title": k,
                      "description": v["description"]}
            terms = []
            for value in v['items']['enum']:
                term = {
                    "name": value,
                }
                if ('meta:enum' in v['items'] and
                    value in v['items']['meta:enum']):
                    term["description"] = v['items']['meta:enum'][value]
                terms.append(term)
            record["terms"] =  terms
            capture.append(record)
        else:
            raise RuntimeError(f"Unrecognised items in {(v['items'])} for {k}")
    elif v['type'] == 'string':
        _add_string_to_glossary(capture, k, v)
    else:
        raise RuntimeError(f"Unrecognised type: in {(v['type'])} for {k}")


def _add_string_to_glossary(capture, k, v):
    
    record = {"title": k,
              "description": v["description"]}
    
    if 'enum' in v:
        terms = []
        for value in v['enum']:
            term = {
                    "name": value,
            }
            if 'meta:enum' in v and value in v['meta:enum']:
                term["description"] = v['meta:enum'][value]
            terms.append(term)
        record["terms"] =  terms

    capture.append(record)


def _add_multi_to_glossary(capture, k, v, pk):

    vpk = v[pk]
    types = {d['type']: i for i, d in enumerate(vpk)}

    if 'array' in types:
        sub = vpk[types['array']]
        if 'anyOf' in sub['items']:
            record = {"title": k,
                      "description": v["description"]}
            terms = []
            term_indices = {}
            term_counter = 0
            for subsub in sub['items']['anyOf']:
                if 'enum' in subsub:
                    sub_terms = []
                    for value in subsub['enum']:
                        term = {
                            "name": value,
                        }
                        if ('meta:enum' in subsub and
                            value in subsub['meta:enum']):
                            term["description"] = subsub['meta:enum'][value]
                        sub_terms.append(term)
                        term_indices[value] = term_counter
                        term_counter += 1
                    terms.extend(sub_terms)
                if 'properties' in subsub:
                    for sk, sv in subsub['properties'].items():
                        sd = []
                        _add_prop_to_glossary(sd, sk, sv)
                        terms[term_indices[sk]]["terms"] = sd[0]["terms"]
            record["terms"] =  terms
            capture.append(record)
        elif 'enum' in sub['items']:
            record = {"title": k,
                      "description": v["description"]}
            terms = []
            for value in sub['items']['enum']:
                term = {
                    "name": value,
                }
                if ('meta:enum' in sub['items'] and
                    value in sub['items']['meta:enum']):
                    term["description"] = sub['items']['meta:enum'][value]
                terms.append(term)
            record["terms"] =  terms
            capture.append(record)
        elif 'type' in sub['items'] and sub['items']['type'] == 'string':
            record = {"title": k,
                      "description": v["description"]}
            capture.append(record)
        else:
            raise RuntimeError(f"Unrecognised items in {(sub['items'])} for {k}")
    elif 'string' in types:
        sub = vpk[types['string']]
        sub["description"] = v["description"]
        _add_string_to_glossary(capture, k, sub)


if __name__ == "__main__":
    main()
