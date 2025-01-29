import pandas as pd
import numpy as np
import json
import pathlib

#%%
directory = pathlib.Path("data")
directory = pathlib.Path(__file__).parent / directory 

pulls = pd.read_csv(directory / pathlib.Path("gpt_pulls.csv"))
print(f'Total number of pull requests at beginning: {len(pulls)}')

#%%
pulls_dedup = pulls.drop_duplicates(subset=['repo_name', 'PR Number'])
print(f'Total number of pull requests after deduplication: {len(pulls_dedup)}')


# %%
pulls = pd.read_csv(directory / pathlib.Path("repository_with_gpt_pr.csv"))
pull_2 = pulls[pulls['Participants'] > 1]
print(f'Total number of pull requests with more than 1 participant: {len(pull_2)}')

# only with partipant > 1
removed_projects = pulls[pulls['Participants'] > 1]

# %%
repos = pd.read_csv(directory / pathlib.Path("gpt_repos.csv"))
repos_10_stars = repos[repos['stars'] >= 10]
print(f'Total number of repositories with more than 10 stars: {len(repos_10_stars)}')


# %%
prs_10_stars = pull_2[pull_2['repo_name'].isin(repos_10_stars['repo_name'])]
print(f'Total number of pull requests in repositories with more than 10 stars: {len(prs_10_stars)}')
removed_projects = removed_projects[removed_projects['repo_name'].isin(repos_10_stars['repo_name'])]




#remove pr whose URL is not found
removed_projects = removed_projects[removed_projects['URL status'] == True]
# %%
# %%

print(f'Total number of pull requests in final data: {len(removed_projects)}')
removed_projects.to_csv(directory / pathlib.Path("gpt_filtered_pulls.csv"), index=False)

