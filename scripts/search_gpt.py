#%%
import queue
import csv
import pathlib
from random import randint
from github import Github
from github.GithubException import RateLimitExceededException, GithubException
import yaml
from requests.exceptions import ConnectionError
import time
import os
from collections import defaultdict
import numpy as np
import requests
from time import sleep

import pandas as pd

#%%
os.environ['PYDEVD_WARN_SLOW_RESOLVE_TIMEOUT'] = '120'

#%%
def chatgpt_ngrams(text, n):
    words = text.split()
    ngrams = [' '.join(words[i:i+n]) for i in range(len(words)-n+1)]
    return [ngram for ngram in ngrams if "ChatGPT" in ngram.split()]

#%%
class GitHubClient:
    def __init__(self, tokens_queue):
        self.tokens_queue = tokens_queue
        self.client = self.get_github_client()

    def get_github_client(self, max_retries=5):
        while not self.tokens_queue.empty():
            token = self.tokens_queue.get()
            retries = 0
            while retries < max_retries:
                try:
                    client = Github(token)
                    client.get_user().get_repos()
                    self.tokens_queue.put(token)
                    print(f"Token {token} is used.")
                    return client
                except RateLimitExceededException:
                    break
                except ConnectionError:
                    retries += 1
                    time.sleep(2 ** retries)
            else:
                print(f"Token {token} skipped after {retries}.")
                pass
        raise Exception("All tokens are invalid or rate limit exceeded.")

    def search_repositories(self, search_string):
        return self.client.search_repositories(query=search_string)
    
    def search_pull_requests(self, search_string, start_date=None, end_date=None):
        return self.client.search_issues(query=f'{search_string} is:pr created:{start_date}..{end_date}' if start_date and end_date else f'{search_string} is:pr')

    def get_pull_requests(self, repo):
        return repo.get_pulls(state='all')

#%%
class CSVWriter:
    @staticmethod
    def write_to_csv(file_name, data, headers):
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)

    @staticmethod
    def update_csv(file_name, new_data, headers, unique_key):
        try:
            with open(file_name, mode='r', newline='', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                existing_data = {row[unique_key]: row for row in reader}
                headers = reader.fieldnames
        except FileNotFoundError:
            existing_data = {}
            if new_data == []:
                return
            headers = new_data[0].keys() 
        
        for row in new_data:
            existing_data[row[unique_key]] = row
        
        with open(file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            for row in existing_data.values():
                writer.writerow(row)


#%%
class GitHubDataCollector:
    def __init__(self, github_client):
        self.github_client = github_client


    def check_url_status(self, url, retries=5):
        for attempt in range(retries):
            try:
                sleep(randint(1, 15))
                response = requests.head(url, allow_redirects=True, timeout=5)
                if response.status_code == 200:
                    return True
                elif response.status_code == 404:
                    return False
            except requests.RequestException as e:
                print(f"Request failed for URL: {url} \nError: {e}")
                pass
        return False
    

    def collect_data(self, search_string, start_date=None, end_date=None):
        chatgpt_prs = self.github_client.search_pull_requests(search_string, start_date, end_date)
        print(f'From {start_date} to {end_date}, Found {chatgpt_prs.totalCount} PRs.')
        chatgpt_pulls_data = []
        for pr in chatgpt_prs:
            print(f'PR:{pr}') 
            chatgpt_pulls_data.append({
                    'repo_name': pr.repository.full_name,
                    'PR Title': pr.title,
                    'PR Number': pr.number,
                    'State': pr.state,
                    'Created At': pr.created_at,
                    'URL': pr.html_url,
                    'URL status': self.check_url_status(pr.html_url)
                })
        return chatgpt_pulls_data

    def get_repositories(self, chatgpt_prs):
        pr_counts = defaultdict(int)
        for pr in chatgpt_prs:
            pr_counts[pr['repo_name']] += 1

        repos = set(pr['repo_name'] for pr in chatgpt_prs)
        repo_data = []
        
        print(f'Collecting Information for {len(repos)} Repositories.')

        for repo in repos:
            try:
                repo = self.github_client.client.get_repo(repo)
                try:
                    contributors_count = repo.get_contributors().totalCount
                except GithubException as e:
                    if e.status == 403:
                        contributors_count = 500
                    else:
                        contributors_count = 0

                chatgpt_pr_count = pr_counts[repo.full_name]

                repo_data.append({
                    'repo_name': repo.full_name,
                    'stars': repo.stargazers_count,
                    'nb_commits': repo.get_commits().totalCount,
                    'nb_pulls': repo.get_pulls(state='all').totalCount,
                    'nb_chatgpt': chatgpt_pr_count,
                    'nb_issues': repo.get_issues(state='all').totalCount,
                    'contributors': contributors_count,
                    'forks': repo.forks_count,
                    'watchers': repo.watchers_count,
                    'size': repo.size,
                    'created_at': repo.created_at,
                    'push_at': repo.pushed_at,
                    'is_forked': repo.fork,
                    'language': repo.language,
                    'topics': repo.get_topics()
                })
            except GithubException as e:
                if e.status == 404:
                    print(f"Repository {repo} not found.")
            except Exception as e:
                print(f"Error in collecting data for {repo}: {e}")
        # print(f'Data collection completed with average time of {np.mean(times)} seconds per repository.')
        print('Data collection completed.')
        return repo_data
    
    
#%%
def read_token_from_yaml(file_path):
    
    with open(pathlib.Path.home() / file_path, 'r') as file:
        tokens = yaml.safe_load(file)
    tokens_queue = queue.Queue()
    for token in tokens:
        tokens_queue.put(token)
    return tokens_queue

# #%%
def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 


    tokens = read_token_from_yaml('tokens.yaml')
    github_client = GitHubClient(tokens)
    data_collector = GitHubDataCollector(github_client)
     
    search_string = 'GPT'
    chatgpt_prs = data_collector.collect_data(search_string,'2025-01-01','2025-01-28')
    CSVWriter.write_to_csv(directory / pathlib.Path("gpt_pulls.csv"), chatgpt_prs, ['repo_name', 'PR Title', 'PR Number', 'State', 'Created At','URL','URL status'])
#   
    repositories = data_collector.get_repositories(chatgpt_prs)
    CSVWriter.write_to_csv(directory / pathlib.Path("gpt_repos.csv"), repositories, ['repo_name','stars', 'nb_commits', 'nb_pulls', 'nb_chatgpt', 'nb_issues', 'contributors', 'forks', 'watchers', 'size', 'created_at', 'push_at', 'is_forked', 'language', 'topics'])


    
# #%%
if __name__ == "__main__":
    main()

