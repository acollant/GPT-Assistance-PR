import joblib 
from github.GithubException import RateLimitExceededException, GithubException
from joblib import Parallel, delayed
import pandas as pd
import numpy as np
import requests
import time
import itertools
import pathlib
import yaml
import pandas as pd
import csv
import queue

#%%
def read_token_from_yaml(file_path):
    
    with open(pathlib.Path.home() / file_path, 'r') as file:
        tokens = yaml.safe_load(file)
    tokens_queue = queue.Queue()
    for token in tokens:
        tokens_queue.put(token)
    return tokens_queue

#%%

#%%
def query_graphql(token, query):
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github.v3+json"}
    
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': query},
        headers=headers
    )
    if response.status_code != 200:
        raise Exception(f"GraphQL query failed with status code {response.status_code}: {response.text}")
    return response.json()['data']

#%%
def get_pr_details(repository, pr_number):
    MAX_RETRIES = 5
    tokens = read_token_from_yaml('tokens.yaml')
    while not tokens.empty():
        retries = 0
        token = tokens.get()
        while retries < MAX_RETRIES:
            tokens.put(token)
            try:
                repo_owner, repo_name = repository.split('/')
                query = f"""
                {{
                    repository(owner: "{repo_owner}", name: "{repo_name}") {{
                    pullRequest(number: {pr_number}) {{
                        participants(first: 100) {{
                        totalCount
                        }}
                        reviews(first: 100) {{
                        totalCount
                        nodes {{
                                author {{
                                    login
                                }}
                            }}
                        }}
                    }}
                    }}
                }}
                """

                data = query_graphql(token, query)['repository']['pullRequest']
                participants_count = data['participants']['totalCount'] if data['participants'] else 0
                return int(participants_count)
            except Exception as e:
                print(repository, pr_number, e)
                return np.nan

def merge():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    repo_data = pd.DataFrame()
    gpt_file  = directory / pathlib.Path("gpt_pulls.csv") 
    gpt_repos = directory / pathlib.Path("gpt_repos.csv")
    
    with open(gpt_file, newline='') as f:
        reader = csv.reader(f)
        pr_data = pd.DataFrame((reader), columns=['repo_name', 'PR Title', 'PR Number', 'State', 'Created At', 'URL', 'URL status'])

    with open(gpt_repos, newline='') as f:
        reader = csv.reader(f)
        repo_data = pd.DataFrame((reader), columns=['repo_name','stars', 'nb_commits', 'nb_pulls', 'nb_chatgpt', 'nb_issues', 'contributors', 'forks', 'watchers', 'size', 'created_at', 'push_at', 'is_forked', 'language', 'topics'])

    merged_pr_repos = pd.merge(pr_data, repo_data, on= 'repo_name')
    return merged_pr_repos

def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    merged_pr_repos = merge()
    #merged_pr_repos.to_csv('data/repository_with_gpt_pr.csv')
    participants = []
    for index, row in merged_pr_repos.iterrows():
        if index !=0: 
            print(index, row['repo_name'], row['PR Number'])
            participants.append(get_pr_details(row['repo_name'], row['PR Number']))
        
        
    merged_pr_repos[['Participants']] = pd.DataFrame(participants, columns=['Participants'])
    merged_pr_repos = merged_pr_repos.tail(merged_pr_repos.shape[0] - 1)
    merged_pr_repos.to_csv( directory / pathlib.Path("repository_with_gpt_pr.csv"), index = False)
   



if __name__ == "__main__":
    main()