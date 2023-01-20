#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Analyses both parent repo and submodule, outputs subsequent PR list in Markdown format. """

from os import EX_OK
import subprocess
import argparse
import json

arg_parser = argparse.ArgumentParser()
arg_parser.add_argument('-r', '--repo', help='parent repository')
arg_parser.add_argument('-s', '--submodule', help='submodule repository')
arg_parser.add_argument('-o', '--org', help='organization')
arg_parser.add_argument('-so', '--source', help='source pr')

class MarkdownColumn:
    """ Object to define a Markdown Column in a Markdown table. """
    def __init__(self, rows, title=''):
        self.title = title
        self.rows = rows
        self.number_of_rows = len(rows)

def markdown_put_under_dropdown_menu(title, text):
    """ Markdown dropdown with an arrow and details hidden under it. """
    return f"<details><summary>{title}</summary>\n\n{text}\n\n</details>\n"

def markdown_put_in_a_multiline_code_block(text, language=""):
    """ Put text inside three ticks(```). """
    return f"```{language}\n{text}\n```\n"

def markdown_put_in_a_code_block(text):
    """ Put text inside single tick(`). """
    return f"`{text}`"

def markdown_generate_table(columns):
    """ Create a Markdown table. """
    lines = []
    lines.append(f"| {' | '.join(map(lambda x: x.title, columns))} |")
    sep = (['---:'] * len(columns))
    lines.append(f"| {' | '.join(sep)} |")
    rows_list = map(lambda x: x.rows, columns)
    for row in zip(*rows_list):
        lines.append(f"| {' | '.join(list(row))} |")
    return '\n'.join(lines)

class GitHubPR:
    """ An object used to define a GitHub PR. """
    def __init__(self, number, submodule_change, current_pr_number, order):
        self.order = order
        self.number = f"#{number}"
        self.submodule_hash_from = submodule_change[0]
        self.submodule_hash_to = submodule_change[1]
        self.is_current = number == current_pr_number
        self.title = self.number

class Train:
    """ An object used with both parent repo and submodule to output a PR list in Markdown format. """
    def __init__(self, repo, submodule_name, parent_repo_name, current_pr_number):
        self.repo = repo
        self.submodule_name = submodule_name
        self.parent_repo_name = parent_repo_name
        self.current_pr_number = current_pr_number

    def get_current_submodule_hash(self):
        """ Fetch current hash of the submodule. """
        result = subprocess.run([
                    'gh',
                    'api',
                    '-H', 'Accept: application/vnd.github+json',
                    f"repos/{self.repo}/{self.parent_repo_name}/contents/{self.submodule_name}",
                    '-q', '.sha'
                ],
                capture_output=True,
                check=True
            )
        return result.stdout.decode('utf-8').strip()

    def submodule_changing_prs(self):
        """ Fetch parent PRs that change submodule hash. """
        result = subprocess.run([
                'gh',
                'pr',
                'list',
                '-L', '100',
                '-s', 'open',
                '--json', 'number,files',
                '-q', f".[] | select(.files[].path==\"{self.submodule_name}\").number"
            ],
            capture_output=True,
            check=True
        )
        if result.returncode == EX_OK:
            output = result.stdout.decode('utf-8')
            if output == '':
                print('There is no PR increasing the hash of ' + self.submodule_name)
            else:
                return output.splitlines()
        else:
            print(result.stderr)

    def recent_submodule_commits(self):
        """ Check recent commits of the submodule. """
        result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github+json', f"repos/{self.repo}/{self.submodule_name}/commits", '-q', 'map( {sha, html_url} )'], capture_output=True, check=True)
        return json.loads(result.stdout.decode('utf-8'))

    def get_diff_in_pr(self, pr_number):
        """ Fetch submodule changes made in a specific PR. """
        result = subprocess.run(['gh', 'api', '-H', 'Accept: application/vnd.github.diff', f"repos/{self.repo}/{self.parent_repo_name}/pulls/{pr_number}"], capture_output=True, check=True)
        result = subprocess.run(['grep', 'Subproject'], input=result.stdout, capture_output=True, check=True)
        result = subprocess.run(['awk', '{print $3}'], input=result.stdout, capture_output=True, check=True)

        hashes = result.stdout.decode('utf-8').splitlines()
        return GitHubPR(pr_number, hashes, self.current_pr_number, 0)

    def post_comment(self, prs, body):
        """ Posts a GitHub comment to a PR. """
        for open_submodule_pr in prs:
            print(f"Posting comment to PR {open_submodule_pr.title}")
            if not open_submodule_pr.is_current:
#                subprocess.run(['gh', 'pr', 'comment', open_submodule_pr.number, '-b', body], check=True)
                print(body)

    def process_prs(self, prs, submodule_commit_hash, current_submodule_hash):
        """ Process PRs to print in the details dropdown. """
        prs_metadata = []
        to_prs = []
        if current_submodule_hash == submodule_commit_hash.strip():
            prs_metadata.append(' ◄CURRENT HASH')

        for open_submodule_pr in prs:
            if open_submodule_pr.submodule_hash_to == submodule_commit_hash:
                to_prs.append(open_submodule_pr)
                prs_metadata.append(open_submodule_pr.title + ' ◄')
            if open_submodule_pr.submodule_hash_from == submodule_commit_hash:
                prs_metadata.append(open_submodule_pr.title + ' ▲')
        return ('\t'.join(prs_metadata), to_prs)

    def get_order_or_pr(self, open_pr):
        """ Get order feature of a PR. """
        return open_pr.order

    def get_output_lines(self):
        """ Prepare output lines with submodule hashes and metadata. """
        hash_column = MarkdownColumn([], title=f"Latest {self.submodule_name} commits")
        metadata_column = MarkdownColumn([], title=f"{self.parent_repo_name} PRs")
        prs = []
        sorted_pr_list = []
        for i in self.submodule_changing_prs():
            prs.append(self.get_diff_in_pr(i))

        current_submodule_hash = self.get_current_submodule_hash()

        for index, commit in enumerate(self.recent_submodule_commits()):
            commit_hash = commit['sha']
            commit_url = commit['html_url']
            metadata, to_prs = self.process_prs(prs, commit_hash, current_submodule_hash)

            if metadata:
                hash_column.rows.append(commit_url)
                metadata_column.rows.append(metadata)
            for to_pr in to_prs:
                to_pr.order = index
            for sorted_pr in sorted(to_prs, key=self.get_order_or_pr):
                sorted_pr_list.append(sorted_pr)

        table = markdown_put_under_dropdown_menu("Details", markdown_generate_table([hash_column, metadata_column]))
        message = f"#{self.current_pr_number} has been merged with {markdown_put_in_a_code_block(self.submodule_name)} submodule changes. To resolve conflicts, you may want to merge main."
        output_markdown = f"PR Train: {' → '.join(list(map(lambda x: x.title, sorted_pr_list))[::-1])}\n\n{message}\n{table}"
        self.post_comment(prs, output_markdown)

ARGS = arg_parser.parse_args()
train = Train(ARGS.org, ARGS.submodule, ARGS.repo, ARGS.source)
train.get_output_lines()
