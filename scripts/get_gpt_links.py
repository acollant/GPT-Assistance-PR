#%%
from github import Github
import json
import pandas as pd
from datetime import datetime
import pathlib
import queue
import yaml
from time import sleep
import time
from github.GithubException import RateLimitExceededException, GithubException
from requests.exceptions import ConnectionError
#%%
class GitHubPRCollector:
    def __init__(self, github_token):
        self.github = Github(github_token)

    def extract_chatgpt_links(self, text, source_url, author, property, date):
        """
        Extract ChatGPT sharing links from text with detailed information.
        """
        links = []
        if text:
            for link in text.split():
                if "https://chat.openai.com/share/" in link:
                    mention_details = {
                        "URL": link,
                        "Mention": {
                            "MentionedURL": source_url,
                            "MentionedProperty": property,
                            "MentionedAuthor": author,
                            "MentionedText": text,
                            "Status": 200,
                            "DateOfConversation": date.strftime("%Y-%m-%d %H:%M:%S"),
                            "DateOfAccess": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    }
                    links.append(mention_details)
        return links

    def collect_pr_data(self, repo_name, pr_number):
        """
        Collect data from a GitHub Pull Request, including detailed ChatGPT sharing links.
        """
        try:
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            chatgpt_links = []

            chatgpt_links = self.extract_chatgpt_links(pr.title, pr.html_url, pr.user.login, 'title', pr.created_at) + self.extract_chatgpt_links(pr.body, pr.html_url, pr.user.login, 'body', pr.created_at)

            comments = pr.get_issue_comments()
            for comment in comments:
                chatgpt_links += self.extract_chatgpt_links(
                    comment.body,
                    comment.html_url,
                    comment.user.login,
                    'comment.body',
                    comment.created_at
                )

            reviews = pr.get_reviews()
            for review in reviews:
                chatgpt_links += self.extract_chatgpt_links(
                    review.body,
                    review.html_url,
                    review.user.login,
                    'review.body',
                    review.submitted_at
                )

            discussions = pr.get_review_comments()
            for discussion in discussions:
                chatgpt_links += self.extract_chatgpt_links(
                    discussion.body,
                    discussion.html_url,
                    discussion.user.login,
                    'review.discussion',
                    discussion.created_at
                )

            
            return {
                "URL": pr.html_url,
                "Author": pr.user.login,
                "RepoName": repo.full_name,
                "Number": pr.number,
                "ChatgptSharing": chatgpt_links
            }
        except Exception as e:
            print(f"Error collecting PR data from {repo_name} pull request: {pr_number}: {e}")
            return None


#%%
class DataWriter:
    @staticmethod
    def write_to_json(file_path, data):
        """
        Write data to a JSON file.
        """
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)

#%%
class PRDataProcessor:
    def __init__(self, github_token, csv_file_path):
        self.collector = GitHubPRCollector(github_token)
        self.csv_file_path = csv_file_path

    def process_prs(self):
        repos = pd.read_csv(self.csv_file_path)
        pr_details_list = []
        for _, row in repos.iterrows():
            repo_name = row['repo_name']
            pr_number = int(row['PR Number'])
            print(repo_name)
            print(pr_number)
            pr_details = self.collector.collect_pr_data(repo_name, pr_number)
            print(pr_details)
            if pr_details:
                pr_details_list.append(pr_details)
        return pr_details_list

def read_token_from_yaml(file_path):
    
    with open(pathlib.Path.home() / file_path, 'r') as file:
        tokens = yaml.safe_load(file)
    tokens_queue = queue.Queue()
    for token in tokens:
        tokens_queue.put(token)
    return tokens_queue


#%%
if __name__ == "__main__":
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    
    
    csv_file_path = directory / pathlib.Path("gpt_filtered_pulls.csv")
    json_output_path = directory / pathlib.Path("chatgpt_pull_requests.json")

    max_retries=5
    tokens = read_token_from_yaml('tokens.yaml')
    while not tokens.empty():
        token = tokens.get()
        retries = 0
        while retries < max_retries:
            try:
                client = Github(token)
                client.get_user().get_repos()
                tokens.put(token)
                print(f"Token {token} is used.")
                processor = PRDataProcessor(token, csv_file_path)
                print(processor.csv_file_path)
                pr_details_list = processor.process_prs()
                print(pr_details_list)
                DataWriter.write_to_json(json_output_path, pr_details_list)
                tokens = queue.Queue()
                break
            except RateLimitExceededException:
                break
            except ConnectionError:
                retries += 1
                time.sleep(2 ** retries)
        else:
            print(f"Token {token} skipped after {retries}.")
            pass
    #processor = PRDataProcessor(github_token, csv_file_path)
    #pr_details_list = processor.process_prs()
    #DataWriter.write_to_json(json_output_path, pr_details_list)

    print(f"Data collected and written to {json_output_path}")

#%%
