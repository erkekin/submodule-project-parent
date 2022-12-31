#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import EX_OK, EX_USAGE
import subprocess
import argparse

argParser = argparse.ArgumentParser()
argParser.add_argument("-p", "--pr", help="current pr number")

class GitHubPR:
    def __init__(self, number, submodule_change, current_pr_number):
        self.number = number
        self.submodule_hash_from = submodule_change[0]
        self.submodule_hash_to = submodule_change[1]
        self.isCurrent = number == current_pr_number

class Train:
    def __init__(self, repo, submodule_name, parent_repo_name, pr):
        self.repo = repo
        self.submodule_name = submodule_name
        self.parent_repo_name = parent_repo_name
        self.current_pr_number = pr

    def get_current_submodule_hash(self):
        result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json', "/repos/" + self.repo + "/" + self.parent_repo_name + "/contents/" + self.submodule_name, '-q', '.sha'], capture_output=True, check=True)
        if result.returncode == EX_OK:
            return result.stdout.decode('utf-8').strip()
        else:
            print(result.stderr)

    def submodule_changing_prs(self):
        result = subprocess.run(['gh', 'pr', 'list', "-L", "100", "-s", "open", "--json", "number,files", '-q', '.[] | select(.files[].path=="' + self.submodule_name + '").number'], capture_output=True, check=True)
        if result.returncode == EX_OK:
            output = result.stdout.decode('utf-8')
            if output == "":
                print("Nothing to worry about, there's no PR increasing the hash of 'roughly'")
            else:
                return output.splitlines()
        else:
            print(result.stderr)
          
    def recent_submodule_commits(self):
        result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json', "/repos/" + self.repo + "/" + self.submodule_name + "/commits", '-q', '.[].sha'], capture_output=True, check=True)
        if result.returncode == EX_OK:
            return result.stdout.decode('utf-8').splitlines()
        else:
            print(result.stderr)


    def get_diff_in_pr(self, pr_number):
        result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.diff', "repos/" + self.repo + "/" + self.parent_repo_name + "/pulls/" + pr_number], capture_output=True, check=True)
        result = subprocess.run(['grep', 'Subproject'], input=result.stdout, capture_output=True, check=False)
        result = subprocess.run(['awk', '{print $3}'], input=result.stdout, capture_output=True, check=False)

        if result.returncode == EX_OK:
            hashes = result.stdout.decode('utf-8').splitlines()
            return GitHubPR(pr_number, hashes, self.current_pr_number)
        else:
            print("problem occured retriveing the open submodule prs")
        print(result.stderr)

    def post_comment(self, prs, body):
        for pr in prs:
            print("Posting comment to PR" + " " + pr.number)
            if pr.isCurrent == False:
                subprocess.run(['gh', 'pr', 'comment', pr.number, '-b', body])

    def processPRs(self, prs, submodule_commit_hash, current_submodule_hash):
        pr_line = []
        if current_submodule_hash == submodule_commit_hash.strip():
            pr_line.append(" ◄CURRENT HASH")

        for pr in prs:
            if pr.submodule_hash_to == submodule_commit_hash:
                pr_line.append(("(THIS PR)" if pr.isCurrent else "") + pr.number + "◄")
            if pr.submodule_hash_from == submodule_commit_hash:
                pr_line.append(("(THIS PR)" if pr.isCurrent else "") + pr.number + "▲")

        return "\t".join(pr_line)

    def run(self):
        prs = []
        lines = ["\n```"]
        for i in self.submodule_changing_prs():
            prs.append(self.get_diff_in_pr(i))

        current_submodule_hash = self.get_current_submodule_hash()

        for index, hash in enumerate(self.recent_submodule_commits()):
            metadata = self.processPRs(prs, hash, current_submodule_hash)
            lines.append(hash + "\t" + metadata)
            print(index, hash, metadata)

        lines.append("```")
        output = "\n".join(lines)
        
        self.post_comment(prs, "[Another PR](https://www.google.com) altered the " + self.submodule_name + " submodule is just merged in. Please have a look and update this PR accordingly." + output)

train = Train("erkekin", "roughly", "submodule-project-parent", argParser.parse_args().pr)
train.run()