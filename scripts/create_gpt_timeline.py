import pandas as pd
import pathlib



from common import (
    get_logger,
    get_path,
    initialize,
    import_project_timelines,
    import_project_pulls,
    import_events_gpt,
    get_json,
    get_csv,
)

initialize()


def export_timeline_gpt(project,timeline_gpt):
    timeline_gpt.to_csv(get_path("timelines_gpt", project), index=False)

def check_events_gpt():
    df_projects_gpt = get_csv('projects_gpt.csv') #import_project_pulls().sort_values(by='owner_login')#
    data = get_json('gpt_pr_mention_all_out.json')
    columns_ = ['owner_login','name','number','event','html_url','is_gpt_for']
    data_ =[]
    df_events_all = pd.DataFrame(columns=columns_)
    for _, row in df_projects_gpt.iterrows():#get_project():
        project = row['owner_login'] + '/' + row['name']
        pull_number = row['number']
        
        print(f'Evaluation the project: {project}/pull/{pull_number}')
        for all_pr in data:
            for each_pr in all_pr:
                if project ==each_pr['project'] and pull_number == each_pr['pr_number']:
                    phases = each_pr['GPTMention']
                    gpt_assistance = 0
                    for phase in phases:
                        data_.append([row['owner_login'],row['name'],row['number'],phase['event'],phase['url'],phase['event_type']])
                        if phase['event_type'] == "gpt assistance": 
                            gpt_assistance = 1
                    
                    if gpt_assistance == 0:
                        print(f'project: {project}/pull/{pull_number} is not gpt')
                        #input('warning')
        df_events = pd.DataFrame(data_,columns=columns_)
    df_events.to_csv('events_gpt.csv', index=False)


def get_project():
    logger = get_logger(__file__, modules={"sqlitedict": "WARNING"})
    logger.info("Add event gpt to timelines")
    
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    
    file_ =  directory / "projects_gpt.csv"
    projects = []
    n = 0
    with open(file_, newline='') as f:
        f.readline()
        for row in f.readlines():
            project = row.split(",")[0].strip() + '/' + row.split(",")[1].strip()
            #projects.append(line.split(",")[0].strip())
            projects.append(project)
    return projects

def main():
    check_events_gpt()
    events_gpt = import_events_gpt()
    projects = get_project()
    
    
    gpt_pulls = import_project_pulls().sort_values(by='owner_login')
    columns_=["project","pull_number","event_number","event","actor","time","state","commit_id","referenced","sha","title","html_url","is_bot","is_chatgpt","is_first_chatgpt","is_proceeding_chatgpt","chatgpt_event"]
    
    for p in projects:
        project = p.replace('/','_')
        print(project)
        timeline = import_project_timelines(project) 
        merged_df = pd.merge(timeline, events_gpt, on='html_url', how ='left')
        #export_timelines(project)
        export_timeline_gpt(project,merged_df)
        #merged_df.to_csv("timeline_1_"+project+'.csv',sep=',',index=False)
        #print(merged_df)
        #input('stop merged')



if __name__ == "__main__":
    main()