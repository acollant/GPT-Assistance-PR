import csv
import re

import joblib
import pandas as pd
import random
import pathlib
from common import (
    cleanup_files,
    force_refresh,
    get_logger,
    get_path,
    initialize,
    lookup_keys,
    open_commits,
    open_patches_raw,
    open_pulls_raw,
    open_timelines_fixed,
    open_timelines_raw,
    open_comments,
    toanalyze,
)

initialize()


def fix_committed(timeline, commits):
    events = []
    for event in timeline:
        if event["event"] == "committed":
            event["author"]["login"] = lookup_keys("author.login", commits[event["sha"]])
        events.append(event)
    return events

def fix_reviewed_commented(timeline, comments):
    events = timeline
    for comment in comments:
        events.append({"event": "review-commented", **comment})

    # for event in timeline:
    #     if event["event"] == "reviewed":
    #         event["comments"] = comments[event["html_url"]]
    #     events.append(event)
    return events

def fix_referenced(timeline):
    events = []
    for event in timeline:
        if event["event"] == "referenced":
            event["referenced"] = event["url"].split("/")[4:6] == event["commit_url"].split("/")[4:6]
        events.append(event)
    return events


def unpack_line_and_commit_commented(timeline):
    events = []
    for event in timeline:
        if event["event"] in ["line-commented", "commit-commented"]:
            for comment in event["comments"]:
                events.append({"event": event["event"], **comment})
        else:
            events.append(event)
    return events


def insert_pulled(timeline, pull):
    return [{"event": "pulled", **pull}, *timeline]


def identify_actor(timeline):
    events = []
    for event in timeline:
        actor = lookup_keys(["actor.login", "user.login", "author.login"], event)
        event["actor"] = actor.lower() if actor is not None else "ghost"
        events.append(event)
    return events


def identify_time(timeline):
    events = []
    for event in timeline:
        event["time"] = lookup_keys(["created_at", "committer.date", "submitted_at"], event)
        events.append(event)
    return events


def add_pull_and_event_number(timeline):
    events = []
    pull_number = timeline[0]["number"]
    for event_number, event in enumerate(sorted(timeline, key=lambda event: event["time"])):
        event["pull_number"] = pull_number
        event["event_number"] = event_number
        events.append(event)
    return events


def fix_timeline(timeline, pull, commits, comments):
    timeline = fix_committed(timeline, commits)
    timeline = fix_referenced(timeline)
    timeline = unpack_line_and_commit_commented(timeline)
    timeline = fix_reviewed_commented(timeline, comments)
    timeline = insert_pulled(timeline, pull)
    timeline = identify_actor(timeline)
    timeline = identify_time(timeline)
    timeline = add_pull_and_event_number(timeline)
    return timeline


def fix_timelines(project, timelines, pulls, commits, comments):
    fixed = open_timelines_fixed(project)
    for pull in pulls:
        fixed[pull] = fix_timeline(timelines[pull], pulls[pull], commits[pull], comments[pull])
    return fixed


def filter_timelines(timelines, pr_numbers):
    rows = []
    for timeline in timelines.values():
        for event in timeline:
            if event["pull_number"] not in pr_numbers:
                continue
            row = {}
            for column in [
                "pull_number",
                "event_number",
                "event",
                "actor",
                "time",
                "state",
                "commit_id",
                "referenced",
                "sha",
                "title",
                "body",
                "html_url",
            ]:
                row[column] = lookup_keys(column, event)
            rows.append(row)
    return rows


def filter_pulls(pulls, pr_numbers):
    rows = []
    for pull in pulls.values():
        if pull["number"] not in pr_numbers:
                continue
        row = {}
        for column in ["number", "html_url", "title", "body"]:
            row[column] = lookup_keys(column, pull)
        rows.append(row)
    return rows


def filter_patches(patches, pr_numbers):
    changes = []
    for pull_number, patch in patches.items():
        if int(pull_number) not in pr_numbers:
            continue
        for diff in re.findall(
            (
                r"(?ms)^From \S+ Mon Sep 17 00:00:00 2001$.+?^---$.+?(?=^From \S+ Mon Sep 17 00:00:00 2001$.+?^---$)"
                r"|^From \S+ Mon Sep 17 00:00:00 2001$.+?^---$.+"
            ),
            patch,
        ):
            added_lines = re.search(r"(?m)^ .+?(\d+) insertions?\(\+\)", diff)
            deleted_lines = re.search(r"(?m)^ .+?(\d+) deletions?\(\-\)", diff)
            changed_files = re.search(r"(?m)^ (\d+) files? changed,", diff)
            changes.append(
                {
                    "pull_number": int(pull_number),
                    "sha": re.match(r"(?ms)^From (\S+) Mon Sep 17 00:00:00 2001$.+?^---$", diff).group(1),
                    "added_lines": added_lines.group(1) if added_lines else 0,
                    "deleted_lines": deleted_lines.group(1) if deleted_lines else 0,
                    "changed_files": changed_files.group(1) if changed_files else 0,
                }
            )
    return changes


def export_timelines(project, timelines):
    pd.DataFrame(timelines).sort_values(["pull_number", "event_number"]).to_csv(
        get_path("timelines", project), index=False, quoting=csv.QUOTE_ALL, escapechar="\\"
    )


def export_pulls(project, pulls):
    pd.DataFrame(pulls).sort_values("number").to_csv(
        get_path("pulls", project), index=False, quoting=csv.QUOTE_ALL, escapechar="\\"
    )


def export_patches(project, patches):
    if len(patches) != 0:
        pd.DataFrame(patches).sort_values(["pull_number", "sha"]).to_csv(get_path("patches", project), index=False)
    else:
        print(f"Empty patches for project {project}")

def preprocess_data(project, pr_numbers):
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info(f"{project}: Preprocessing data")
    
    timelines = open_timelines_raw(project)
    pulls = open_pulls_raw(project)
    commits = open_commits(project)
    patches = open_patches_raw(project)
    comments = open_comments(project)
    timelines = fix_timelines(project, timelines, pulls, commits, comments)
    export_timelines(project, filter_timelines(timelines, pr_numbers))
    export_pulls(project, filter_pulls(pulls, pr_numbers))
    export_patches(project, filter_patches(patches, pr_numbers))
    timelines.terminate()


def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filtered_pulls.csv")#+"/data/repository_with_gpt_pr.csv"
   
    #file_path = get_path('gpt_filtered_pulls')#+"/data/repository_with_gpt_pr.csv"
    prs = pd.read_csv(file_path)
    projects = []
    pr_by_repo = prs.groupby("repo_name")["PR Number"].apply(list).to_dict()
    
    
    for project, pr_numbers in pr_by_repo.items():
        if cleanup_files(["timelines_fixed", "timelines", "pulls", "patches"], force_refresh(), project):
            projects.append(project)
        else:
            print(f"Skip preprocessing data for project {project}")
    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            parallel(joblib.delayed(preprocess_data)(project, pr_by_repo[project]) for project in projects)

# def main():
#     project = "galaxyproject/galaxy-helm"
#     pr_numbers = [448]
#     preprocess_data(project, pr_numbers)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop preprocessing data")
        exit(1)