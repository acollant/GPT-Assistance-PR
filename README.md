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
On the terminal, run **sh download_gpt_data.sh** that will executes the following Python files:
  - search_gpt.py:
    * This code seaches for gpt related repositories and PRs
  - scripts/collect_participants.py
    * This code collects the participants of the PRs
  - apply_filters.py
    * To filter the repositories having the number of participants (>2) and stars (>=10) criteria
### 2. Collect data
On the terminal, run **sh collect_gpt_data.sh** that will locally create the folders for all the projects needed for the analysis:
  - collect_gpt_data.py
    * Collect GPT raw data (ProstgreSQL) for every GPT related project. 
  - preprocess_gpt_data.py
    * Convert raw data in CSV format 
  - get_gpt_events.py
    * Create a csv file for each project having the events that are GPT related.
  - process_gpt_data.py
    * Create a GPT related  dataset
### 3. Apply heuristics
On the terminal, run **inspect_gpt_data.sh** that will create a json needed for the inspection:
  - get_chatgpt_filename.py
    * This code will collect the filename for each project that have GPT within the filename.
  - generate_gpt_json.py
    * This generate a csv file having the attributes that we considered for the analysis.
  - get_gpt_inspection_data.py
    * This code will merge the results from the two previous steps.
  - exclude_no_gpt_pr.py
    * This applies our defined heuristics to classify PRS as potentially as assistance (using GPT) and non assistance (no using GPT).
    * This applies our defined heuristincs to the events (from the projec timelines) to classify events as potentially as assistance (using GPT) and non assistance (no using GPT).
    * Add attributes specifying the gpt was found. Example: on the project name or title, or file names or comments.
### 4. Label Pull Request
- A manual inspection is performed using the file generated (**gpt_pr_mention_all_out.json**) by exclude_no_gpt_pr.py:  
- A true_class.csv is manually created whose structure is:
  * url: PR URL
  * project: project name
  * gpt_in_project_name: if the gpt is found in the project name assessed by the heuristics
  * gpt_in_title: if the gpt is found in the title assessed by the heuristics
  * gpt_in_file_names: if the gpt is found in the file names assessed by the heuristics
  * gpt_in_comments: if the gpt is found in the body of the PRs assessed by the heuristics
  * heuristic_class: assistance if gpt is found either in one of the 4 previous attributes assessed by the heuristics
  * is_correct: marked as no (heuristics are incorrect) or yes (heuristics are correct)
  * true_class: assistance or no assistance
- Re-run exclude_no_gpt_pr.py
  * This will override the wrong heuristics by adding the true-possitive obtained by the manual assessments.
- Run create_gpt_timeline.py
  * This will create a events_gpt.csv file that contains the classification for each event related to the PRs as assistance
  * This will create a new timeline (**timeline_projectname_gpt.csv**) having the GTP events for each identified PR as assistance.
- Run process_gpt_pr_phases.py
  * This will create the phases [*at_submission, at_review, at_waiting_before_change, at_at_change, at_resolution*] for the identified GPT PR and Events (assistance) and for Non-GPT PR (as non-assitance) used to answer RQs.
  * Output file: **project_phases.json**
### 5. RQ Data and stats
On the terminal, run **collect_gpt_stats.sh** that will generate the dataset used to ansewer the RQs:
- collect_gpt_pr_at_resolution.py
  * This will collect the data required for answering RQ1. This data is used in a R code that is found in this repository (https://github.com/acollant/GPT-Assistance-PR/tree/main/R)
  * Columns in the file: project,pull_number,actor,project_age_month,no_commits,PR_size(SLOC),no_changed_files,time_to_merge_h,is_gpt
  * Output file: **at_resolution.csv***
- get_gpt_pr_distance.py
  * This will find the closest Non GPT PR (non assistance) to a GPT PR (Assistance) based on the Euclidean distance by phases.
  * The output file is used in a R program that is found in this repository (https://github.com/acollant/GPT-Assistance-PR/tree/main/R) to check whether the PRs are similar or not.
  * Output file: **distance.csv***
- collect_gpt_pr_stats.py
- collect_gpt_pr_used.py
  
## Directory structure
```
GPT-Assistance-PR/
│   README.md
│   requirements.txt    
│   download_gpt_data.sh
│   collect_gpt_data.sh
│   inspect_gpt_data.sh
└───scripts/
│   │   search_gpt.py
│   │   collect_participants.py
│   │   apply_filters.py
│   │   collect_gpt_data.py
│   │   preprocess_gpt_data.py 
│   │   get_gpt_events.py
│   │   process_gpt_data.py
│   │   get_chatgpt_filename.py
│   │   generate_gpt_json.py
│   │   get_gpt_inspection_data.py
│   │   exclude_no_gpt_pr.py
│   │
│   └───data/
│   │   │   {project_name}_timelines.cvs
│   │   │   {project_name}_timelines.db
│   │   │   {project_name}_dataset.cvs
│   │   │   {project_name}_events.cvs
│   │   │   {project_name}_commits.db
│   │   │   {project_name}_comments.cvs
│   │   │   {project_name}_pulls.cvs
│   │   │   {project_name}_pulls.db
│   │   │   {project_name}_patches.cvs
│   │   │   {project_name}_patches.cvs
│   │   │   gpt_pulls.csv
│   │   │   gpt_repos.cvs


```

