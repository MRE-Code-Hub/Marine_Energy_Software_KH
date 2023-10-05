
from pathlib import Path

import yaml
from yaml import CLoader as Loader
from jsonschema import validate, ValidationError


def main():
    
    db_repo_path = Path(".")
    schema_path = db_repo_path / "schema.yaml"
    records_path = db_repo_path / "records"
    
    assert schema_path.is_file()
    assert records_path.is_dir()
    
    with open(schema_path, "r") as f:
        schema = yaml.load(f, Loader)
    
    count = 0
    
    for p in records_path.iterdir():
        count += 1
        with open(p, "r") as f:
            instance = yaml.load(f, Loader)
        try:
            validate(instance=instance, schema=schema)
        except ValidationError as e:
            print(f"File '{str(p.name)}' failed validation")
            raise ValidationError(e.message)
    
    print(f"Validated {count} records")


if __name__ == "__main__":
    main()
