
from pathlib import Path

import yaml
from yaml import CLoader as Loader
from jsonschema import Draft202012Validator, ValidationError


def main():
    
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
    raise_error = False
    
    for p in records_path.iterdir():
        
        count += 1
        
        with open(p, "r") as f:
            instance = yaml.load(f, Loader)
        
        errors = list(validator.iter_errors(instance))
        if not errors: continue
        
        print(f"Record '{str(p.name)}' failed validation with the following "
              "errors:")
        for error in sorted(errors, key=str):
            print(error.message)
        print("")
        
        error_count += 1
        raise_error = True
    
    if raise_error:
        raise RuntimeError(f"{error_count} validation error(s) detected")
    
    print(f"Validated {count} records")


if __name__ == "__main__":
    main()
