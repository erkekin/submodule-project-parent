#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import EX_OK, EX_USAGE
import subprocess

class GitHubPR:
    def __init__(self, number, submodule_change):
        self.number = number
        self.submodule_hash_from = submodule_change[0]
        self.submodule_hash_to = submodule_change[1]

def get_current_submodule_hash():
    result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json', "/repos/erkekin/submodule-project-parent/contents/submodule-project-child", '-q', '.sha'], capture_output=True, check=True)
    if result.returncode == EX_OK:
        return result.stdout.decode('utf-8').strip()
    else:
        print(result.stderr)


def submodule_changing_prs():
    result = subprocess.run(['gh', 'pr', 'list', "-L", "100", "-s", "all", "--json", "number,files", '-q', '.[] | select(.files[].path=="submodule-project-child").number'], capture_output=True, check=True)
    if result.returncode == EX_OK:
        output = result.stdout.decode('utf-8')
        if output == "":
            print("Nothing to worry about, there's no PR increasing the hash of 'submodule-project-child'")
        else:
            return output.splitlines()
    else:
        print(result.stderr)

def recent_submodule_commits():
    subprocess.run(['git', 'fetch', 'origin', 'main'], capture_output=True, check=True, cwd='submodule-project-child')
    result = subprocess.run(['git', 'rev-list', 'HEAD'], capture_output=True, check=True, cwd='submodule-project-child')
    if result.returncode == EX_OK:
        return result.stdout.decode('utf-8').splitlines()
    else:
        print(result.stderr)


def get_diff_in_pr(pr_number):
    result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.diff', "repos/erkekin/submodule-project-parent/pulls/" + pr_number], capture_output=True, check=True)
    result = subprocess.run(['grep', 'Subproject'], input=result.stdout, capture_output=True, check=False)
    result = subprocess.run(['awk', '{print $3}'], input=result.stdout, capture_output=True, check=False)

    if result.returncode == EX_OK:
        hashes = result.stdout.decode('utf-8').splitlines()
        return GitHubPR(pr_number, hashes)
    else:
        print("problem occured retriveing the open submodule prs")
    print(result.stderr)

def processPRs(prs, submodule_commit_hash, current_submodule_hash):
    pr_line = []
    if current_submodule_hash == submodule_commit_hash.strip():
        pr_line.append(" ⬅ CURRENT HASH")

    for pr in prs:
        if pr.submodule_hash_to == submodule_commit_hash:
            pr_line.append(pr.number + " ⬅")
        if pr.submodule_hash_from == submodule_commit_hash:
            pr_line.append(pr.number + " ⬆")
    return "\t".join(pr_line)

prs = []
for i in submodule_changing_prs():
    prs.append(get_diff_in_pr(i))

current_submodule_hash = get_current_submodule_hash()

for hash in recent_submodule_commits():
    print(hash, processPRs(prs, hash, current_submodule_hash))
