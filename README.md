# GPT-Assistance-PR
The code in this repository uses GitHub API to obtain the GPT related projects and Pull Requests to analyse the whether the use of GPT has an impact on the time to merge on PR tasks. For more details, refer to the paper.

## Installation

1. Start by creating a virtual environment with python 3.9 installed
```Shell
python3 -m venv gpt_pr
``` 

2. Activate the environment
```Shell
source gpt_pr/bin/activate
``` 

3. Install the project's dependencies
```Shell
pip install -r requirements.txt
```
## How to use code
### 1. Download data
On the terminal, run sh download_gpt_data.sh that will executes the following Python files:
  - Search gpt:
    * python3 scripts/search_gpt.py
  - Collect project participants: python3 scripts/collect_participants.py  
  - Apply_filters to filter participants and stars criteria: python3 scripts/apply_filters.py 
### 2. Collect data
run sh collect_gpt_data.sh that will locally create all the projects used for the analysis:
  - Collect GPT raw data: python3 scripts/collect_gpt_data.py
  - Convert row data in CSV format timelimes: python3 scripts/preprocess_gpt_data.py
  - Add GPT to timelines:  python3 scripts/get_gpt_events.py
  - Identify GPT related events: python3 scripts/process_gpt_data.py
### 3. Apply heuristics

### 4. Label Events

## Directory structure
```
GPT-Assistance-PR/
│   README.md
│   requirements.txt    
│   download_gpt_data.sh
│   collect_gpt_data.sh 
└───scripts/
│   │   search_gpt.py
│   │   collect_participants.py
│   │   apply_filters.py
│   │   collect_gpt_data.py
│   │   preprocess_gpt_data.py 
│   │   get_gpt_events.py
│   │   process_gpt_data.py
│   │
│   └───data/
│   │   │   gtp_pulls.cvs
│   │   │   gtp_repos.cvs
│   │   │   gpt_filtered_pulls
│   │   

```

