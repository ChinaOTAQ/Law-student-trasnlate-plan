#!/usr/bin/env python3
"""
fix_dict_quotes.py — escape bare ASCII double-quotes inside Python dict
string values so the file parses without SyntaxError.

Targets any file that defines a dict like:
    SOME_DICT = {
        1: "value with "inner" quotes",
        ...
    }

Usage:
    uv run fix_dict_quotes.py <target_py_file>
    uv run fix_dict_quotes.py <target_py_file> --dict-name MY_DICT

The file is edited in place. A dry-run check is done after writing to
confirm the file imports cleanly.
"""

import re
import sys
import importlib.util
import argparse


def fix_file(path: str, dict_name: str = None):
    text = open(path, encoding='utf-8').read()

    # Locate the dict block: <DICT_NAME> = {  ...  }
    name_pat = re.escape(dict_name) if dict_name else r'\w+'
    m = re.search(
        rf'({name_pat}\s*=\s*\{{)(.*?)(\n\}})',
        text, re.DOTALL
    )
    if not m:
        print(f'No matching dict found in {path}')
        return False

    pre  = text[:m.start(1)]
    head = m.group(1)
    body = m.group(2)
    tail = text[m.end(2):]

    fixed = []
    for line in body.split('\n'):
        pat = re.match(
            r'^(\s*(?:\d+|"[^"]*")\s*:\s*)"(.*)",\s*$',
            line, re.DOTALL
        )
        if pat:
            prefix = pat.group(1)
            value  = pat.group(2)
            value  = value.replace('\\"', '"')   # normalise
            value  = value.replace('"', '\\"')   # re-escape all
            fixed.append(f'{prefix}"{value}",')
        else:
            fixed.append(line)

    new_text = pre + head + '\n'.join(fixed) + tail
    open(path, 'w', encoding='utf-8').write(new_text)
    print(f'Written: {path}')

    # verify
    spec = importlib.util.spec_from_file_location('_check', path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('Syntax OK')
    return True


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('--dict-name', default=None)
    args = ap.parse_args()
    ok = fix_file(args.file, args.dict_name)
    sys.exit(0 if ok else 1)
