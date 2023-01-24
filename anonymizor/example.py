#!/usr/bin/env python3

from pathlib import Path
from anonymizor import anonymizor
import yaml

example_file = Path("example.yaml")
example_content = yaml.safe_load(example_file.read_text())
print(example_content)
ano = anonymizor.anonymize(example_content)
print(yaml.dump(ano))
