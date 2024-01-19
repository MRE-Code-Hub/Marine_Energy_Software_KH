
import argparse
from pathlib import Path

import yaml
from yaml import CLoader as Loader
from jsonschema import Draft202012Validator


def main():
    
    parser = argparse.ArgumentParser(
        description="Validate database schema and records")
    parser.add_argument('action', choices=['schema', 'records'])
    args = parser.parse_args()
    
    if args.action == 'schema':
        validate_schema()
    elif args.action == 'records':
        validate_records()
    else:
        RuntimeError("I'm sorry, Dave. I'm afraid I can't do that.")


def validate_schema():
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    assert schema_path.is_file()
    
    with open(schema_path, "r") as f:
        schema = yaml.load(f, Loader)
    
    Draft202012Validator.check_schema(schema)


def validate_records():
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    records_path = db_repo_path / "records"
    
    assert schema_path.is_file()
    assert records_path.is_dir()
    
    with open(schema_path, "r") as f:
        schema = yaml.load(f, Loader)
    
    validator = Draft202012Validator(schema)
    count = 0
    error_count = 0
    
    for p in records_path.iterdir():
        
        count += 1
        
        if p.suffix != ".yaml":
            if error_count == 0: print("ERRORS:")
            print(f"+ Record '{str(p.name)}' must have yaml file extension")
            error_count += 1
        
        try:
            with open(p, "r") as f:
                instance = yaml.load(f, Loader)
        except Exception as e:
            if error_count == 0: print("ERRORS:")
            print(f"+ Record '{str(p.name)}' failed to load with the "
                   "following error:")
            print("  " + str(e))
            error_count += 1
            continue
        
        errors = list(validator.iter_errors(instance))
        if not errors: continue
        
        if error_count == 0: print("ERRORS:")
        print(f"+ Record '{str(p.name)}' failed validation with the following "
              "errors:")
        for error in sorted(errors, key=str):
            print("  " + error.message)
        
        error_count += 1
    
    if error_count:
        print("")
        raise RuntimeError(f"{error_count} validation error(s) detected")
    
    print(f"Validated {count} records")


if __name__ == "__main__":
    main()
