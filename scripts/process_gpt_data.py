import joblib
import numpy as np
import pandas as pd
import pathlib
from common import (
    cleanup_files,
    convert_dtypes,
    force_refresh,
    get_logger,
    get_path,
    import_bots,
    import_timelines,
    initialize,
    preprocessed,
    selected,
)

initialize()


@convert_dtypes
def add_status(timelines):
    def find_status(timeline):
        pulled = timeline.query("event == 'pulled'")
        closed = timeline.query("event == 'closed'")
        timeline = timeline.assign(
            is_open=False,
            is_closed=False,
            is_merged=False,
            opened_at=pulled["time"].iat[0],
            closed_at=pd.NaT,
            merged_at=pd.NaT,
            closed_by=np.nan,
            merged_by=np.nan,
        )
        if pulled["state"].iat[0] == "closed":
            if not (merged := timeline.query("event == 'merged'")).empty:
                timeline["is_merged"] = True
                timeline["merged_at"] = merged["time"].iat[0]
                timeline["merged_by"] = merged["actor"].iat[0]
            elif not (commit_id := closed.query("commit_id.notna()")).empty:
                timeline["is_merged"] = True
                timeline["merged_at"] = commit_id["time"].iat[0]
                timeline["merged_by"] = commit_id["actor"].iat[0]
            elif not (referenced := timeline.query("referenced", engine="python")).empty:
                timeline["is_merged"] = True
                timeline["merged_at"] = referenced["time"].iat[0]
                timeline["merged_by"] = referenced["actor"].iat[0]
            else:
                timeline["is_closed"] = True
                if not closed.empty:
                    timeline["closed_at"] = closed["time"].iat[-1]
                    timeline["closed_by"] = closed["actor"].iat[-1]
        else:
            timeline["is_open"] = True
        return timeline

    timelines = timelines.groupby("pull_number", group_keys=False).apply(find_status)
    timelines["resolved_at"] = timelines["merged_at"].fillna(timelines["closed_at"])
    timelines["resolved_by"] = timelines["merged_by"].fillna(timelines["closed_by"])
    return timelines.drop(columns=["state", "commit_id", "referenced"])

@convert_dtypes
def add_contributor(timelines):
    def find_contributor(timeline):
        timeline["is_contributor"] = timeline["actor"] == timeline.query("event == 'pulled'")["actor"].iat[0]
        return timeline

    return timelines.groupby("pull_number", group_keys=False).apply(find_contributor)

@convert_dtypes
def add_reviewer(timelines):
    timelines["is_reviewer"] = ~ (timelines["is_contributor"] | timelines["is_bot"])
    return timelines

@convert_dtypes
def add_next_event(timelines):
    timelines['next_event_number'] = None
    timelines['next_event'] = None
    timelines['next_event_time'] = pd.NaT
    timelines['next_event_actor'] = None
    for idx, row in timelines.iterrows():
        if row["is_first_chatgpt"]:
            current_pull, current_event = idx
            next_event_index = (current_pull, current_event + 1)
            while next_event_index in timelines.index:
                next_event = timelines.loc[next_event_index]
                interested_events = ['committed', 'head_ref_force_pushed', 'commented', 'reviewed', 'line-commented', 'commit-commented', 'closed', 'reopened']
                # DISCUSS WITH HASSAN
                # Can PRs have multiple contributors? if yes, are we interested in next action from other contributors if just like the maintainers/reviewers
                if next_event['actor'] != row['actor'] and next_event['actor'] != 'ghost' and not next_event['is_bot'] and next_event['event'] in interested_events:
                    timelines.at[idx, 'next_event_number'] = next_event_index[1]
                    timelines.at[idx, 'next_event'] = next_event['event']
                    timelines.at[idx, 'next_event_time'] = next_event['time']
                    timelines.at[idx, 'next_event_actor'] = next_event['actor']
                    break
                current_event += 1
                next_event_index = (current_pull, current_event + 1)
    return timelines


@convert_dtypes
def add_maintainer_response(timelines):
    timelines = timelines.assign(is_maintainer_response=False)
    timelines.loc[
        timelines.query(
            "is_reviewer and (event.isin(['commented', 'reviewed',"
            " 'line-commented', 'commit-commented', 'merged', 'closed']) or (event == 'referenced' and time"
            " == merged_at)) and time > opened_at",
            engine="python"
        ).index,
        "is_maintainer_response",
    ] = True
    return timelines


@convert_dtypes
def add_maintainer_latency(timelines):
    def find_maintainer_latency(timeline):
        timeline = timeline.assign(
            maintainer_responded_at=pd.NaT,
            maintainer_responded_by=np.nan,
            maintainer_responded_event=np.nan,
            maintainer_latency=np.nan,
        )
        if not (responses := timeline.query("is_maintainer_response", engine="python")).empty:
            timeline["maintainer_responded_at"] = responses["time"].iat[0]
            timeline["maintainer_responded_by"] = responses["actor"].iat[0]
            timeline["maintainer_responded_event"] = responses["event"].iat[0]
            timeline["maintainer_latency"] = (
                timeline["maintainer_responded_at"] - timeline["opened_at"]
            ) / np.timedelta64(1, "h")
        return timeline

    return timelines.groupby("pull_number", group_keys=False).apply(find_maintainer_latency)


@convert_dtypes
def add_contributor_response(timelines):
    timelines = timelines.assign(is_contributor_response=False)
    timelines.loc[
        timelines.query(
            "is_contributor and event.isin(['committed', 'head_ref_force_pushed', 'commented', 'reviewed',"
            " 'line-commented', 'commit-commented', 'closed', 'reopened']) and time > maintainer_responded_at", 
            engine="python"
        ).index,
        "is_contributor_response",
    ] = True
    return timelines


@convert_dtypes
def add_contributor_latency(timelines):
    def find_contributor_latency(timeline):
        timeline = timeline.assign(
            contributor_responded_at=pd.NaT, contributor_responded_event=np.nan, contributor_latency=np.nan
        )
        if not (responses := timeline.query("is_contributor_response", engine="python")).empty:
            timeline["contributor_responded_at"] = responses["time"].iat[0]
            timeline["contributor_responded_event"] = responses["event"].iat[0]
            timeline["contributor_latency"] = (
                timeline["contributor_responded_at"] - timeline["maintainer_responded_at"]
            ) / np.timedelta64(1, "h")
        return timeline

    return timelines.groupby("pull_number", group_keys=False).apply(find_contributor_latency)

@convert_dtypes
def next_event_latency(timelines):
    timelines['next_event_latency'] = (timelines['next_event_time'] - timelines['time']) / np.timedelta64(1, 'h')
    return timelines

@convert_dtypes
def previous_events_latency(timelines):
    timelines['avg_previous_response_time'] = np.nan
    timelines['median_previous_response_time'] = np.nan
    for idx, row in timelines.iterrows():
        if row["is_first_chatgpt"]:
            current_pull, current_event = idx
            previous_event_index = (current_pull, current_event - 1)
            current_event_timeline = row
            previous_latency = []
            while previous_event_index in timelines.index:
                previous_event = timelines.loc[previous_event_index]
                interested_events = ['committed', 'head_ref_force_pushed', 'commented', 'reviewed', 'line-commented', 'commit-commented', 'closed', 'reopened']
                if previous_event['actor'] != current_event_timeline['actor'] and previous_event['actor'] != 'ghost' and not previous_event['is_bot'] and previous_event['event'] in interested_events:
                    previous_response_latency =  (current_event_timeline['time'] - previous_event['time']) / np.timedelta64(1, 'h')
                    previous_latency.append(previous_response_latency)
                    current_event_timeline = previous_event
                current_event -= 1
                previous_event_index = (current_pull, current_event - 1)
            timelines.at[idx, 'avg_previous_response_time'] = np.mean(previous_latency)
            timelines.at[idx, 'median_previous_response_time'] = np.median(previous_latency)
    return timelines

@convert_dtypes
def merge_latency(timelines):
    if timelines['is_merged']:
        timelines['merged_at'] = timelines['merged_at']
        timelines['merged_latency'] = (timelines['merged_at'] - timelines['time']) / np.timedelta64(1, 'h')
    return timelines

def export_dataset(project, timelines):
    timelines.to_csv(get_path("chatgpt_dataset", project))


def process_chatgpt_data(project):
    logger = get_logger(__file__)
    logger.info(f"{project}: Processing ChatGPT data")
    timelines = import_timelines(project)
    timelines = add_status(timelines)
    timelines = add_contributor(timelines)
    timelines = add_reviewer(timelines)
    timelines = add_maintainer_response(timelines)
    timelines = add_maintainer_latency(timelines)
    timelines = add_contributor_response(timelines)
    timelines = add_contributor_latency(timelines)
    timelines = add_next_event(timelines)
    timelines = previous_events_latency(timelines)
    timelines = timelines[timelines['is_chatgpt']]
    timelines = next_event_latency(timelines)
    # timelines = merge_latency(timelines)
    export_dataset(project, timelines)


def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("gpt_filtered_pulls.csv")#+"/data/repository_with_gpt_pr.csv"
   
    #file_path = get_path('gpt_filtered_pulls')#+"/data/repository_with_gpt_pr.csv"
    prs = pd.read_csv(file_path)
    projects = []

    pr_by_repo = prs.groupby("repo_name")["PR Number"].apply(list).to_dict()
    

    for project, pr_numbers in pr_by_repo.items():
        if cleanup_files("chatgpt_dataset", force_refresh(), project):
            projects.append(project)
        else:
            print(f"Skip processing data for project {project}")
    if projects:
        with joblib.Parallel(n_jobs=-1, verbose=50) as parallel:
            parallel(
                joblib.delayed(process_chatgpt_data)(project)
                for project in projects
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop processing data")
        exit(1)