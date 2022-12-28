#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import EX_OK, EX_USAGE
import subprocess

def get_current_submodule_hash():
    result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json', "/repos/erkekin/submodule-project-parent/contents/submodule-project-child", '-q', '.sha'], capture_output=True, check=True)
    if result.returncode == EX_OK:
        return result.stdout.decode('utf-8').strip()
    else:
        print(result.stderr)

print(get_current_submodule_hash())
