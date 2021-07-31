#!/bin/bash
time python3 get_parents.py 1>get_parents_stdout.out 2>get_parents_stderr.out
time python3 automate_diffs.py -i github_data.json 1>automate_diffs_stdout.out 2>automate_diffs_stderr.out
