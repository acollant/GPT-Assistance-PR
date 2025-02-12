import numpy
import json
import pandas as pd
import pathlib
import scipy.stats as stats
import numpy as np

from common import (
    initialize,
    import_project_pulls,
)

initialize()

def manhattan(x, y):
    distance = numpy.sum(numpy.abs(x - y))
    #print(f"Manhattan distance: {manhattan_distance}")  
    return distance

def normalize(point, points):
    min_ = numpy.min(points)
    max_ = numpy.max(points)
    return round ( (point - min_) / (max_- min_), 3) 

def normalize_df(df):
    df_min_max_scaled = df.copy()
    for column in df_min_max_scaled[['duration_gpt', 'duration_no_gpt']]:
        df_min_max_scaled[column] =  10000 * ( (df_min_max_scaled[column] - 
                                                df_min_max_scaled[column].min()) / 
                                                (df_min_max_scaled[column].max() - 
                                                 df_min_max_scaled[column].min()) )    
    
    return df_min_max_scaled

def get_json(file_name):
    # Opening JSON file
    f = open(file_name,'r')
    # returns JSON object as  a dictionary
    data = json.load(f)
    f.close()
    return  data

def jaccard_binary(x,y):
    """A function for finding the similarity between two binary vectors"""
    intersection = np.logical_and(x, y)
    union = np.logical_or(x, y)
    similarity = intersection.sum() / float(union.sum())
    distance= 1-similarity
    return similarity, distance


def json_to_factors(is_gpt):
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    file_name_in = directory / pathlib.Path('project_phases.json') 
    data = get_json(file_name_in)
    projects = import_project_pulls().sort_values(['owner_login','name'])
    df = projects[projects['is_gpt'] == is_gpt]
    
    columns_= ['project','pull_number','is_gpt_pr','phase',
                                       'no_commits','no_changed_files',
                                       'PR_size','project_age','duration','event']
    
    phase = ['at_submission', 'at_review', 'at_waiting_before_change',
              'at_changed', 'at_waiting_after_accepted', 'at_resolution']
    
    df_factors = pd.DataFrame(columns=columns_)
    
    for _, row in df.iterrows():
        project = row['owner_login'] + '_' + row['name']
        pull_number = str(row['number'])
        is_gpt = str(row['is_gpt'])
        for projects in data:    
            phase_arr = []
            if project in projects:
                #input(project)
                for f in phase:
                    array_ = [project, pull_number, is_gpt, f, -10000, -10000, -10000, -10000, -10000, -10000]
                    if None ==  projects[project][pull_number][f]: continue
                    factor = projects[project][pull_number][f]['factors']
                    duration =  projects[project][pull_number][f]['duration']
                    duration = -10000 if duration is None else duration
                    is_assistance = 'gpt assistance' if projects[project][pull_number][f]['gpt_assistance'] == 1 else 'not gpt assistance'
                    array_ = [project, 
                              pull_number,
                              is_gpt, 
                              f, 
                              factor['no_commits'],
                              factor['no_changed_files'],
                              factor['PR_size'],
                              factor['project_age'], 
                              duration, 
                              is_assistance
                              ]
                    #if numpy.isnan(array_).any(): continue
                    phase_arr.append(array_)
                df_ = pd.DataFrame(phase_arr,columns=columns_)
                    #df_.dropna(axis=1, how='all', inplace=True)
                df_factors =  df_factors._append(df_,ignore_index=True)
            
    return  df_factors

def cosine(x,y):
    similarity = np.dot(x,y)/(norm(x)*norm(y))
    distance = 1 - similarity
    return similarity, distance

def euclidean(x, y):
    x = np.array(x)
    y = np.array(y)
    sum_sq = np.sum(np.square(x - y))
    return (np.sqrt(sum_sq))

def get_PRS_distance():
    gpt_df = json_to_factors(1)
    no_gpt_df = json_to_factors(0)

    phase = ['at_submission', 
             'at_review', 
             'at_waiting_before_change', 
             'at_changed',
             'at_waiting_after_accepted', 
             'at_resolution']
        
    
        
    df_gpt  =    gpt_df[gpt_df['is_gpt_pr'] == '1']
    df_no_gpt  = no_gpt_df[no_gpt_df['is_gpt_pr'] == '0']
        
    columns_=['phase',
              'project_gpt','pull_number_gpt','is_gpt_pr','event_gpt','factor_gpt','factor_gpt_norm', 'duration_gpt',
              'project_no_gpt','pull_number_no_gpt','is_no_gpt_pr','event_no_gpt','factor_no_gpt','factor_no_gpt_norm','duration_no_gpt',
              'jaccard_distance', 'jaccard_similiarity', 'manhattan_distance', 'cosine_distance','cosine_similarity','euclidean_distance']
        
    df_distance = pd.DataFrame(columns=columns_)
        
    df_distance_all = pd.DataFrame(columns=columns_)
    
    for f in phase:
        df_1 = df_gpt[(df_gpt['phase'] == f) & (df_gpt['event']=='gpt assistance')]
        df_2 = df_no_gpt[df_no_gpt['phase'] == f]
        #print(df_1)
        #input("x")
        for _, row in df_1.iterrows():
            phase_arr = []
            project = row['project']
            pull_number = (row['pull_number'])
            is_gpt_pr = 'GPT PR' if row['is_gpt_pr'] == '1' else 'Not GPT PR'
            
            
            #if row['event'] != 'gpt assistance': continue

            points =  numpy.array([(row['no_commits']), (row['no_changed_files']), (row['PR_size']),  (row['project_age'])])
            x =  numpy.array([(row['no_commits']), (row['no_changed_files']), (row['PR_size']),  (row['project_age'])])
            if numpy.isnan(points).any(): continue
            if numpy.count_nonzero(points) == 0: continue
            point_1 =  numpy.array([ 
                normalize(row['no_commits'],points),
                normalize(row['no_changed_files'],points),
                normalize(row['PR_size'],points),
                normalize(row['project_age'],points)
                ])
          
            #point_1 =  numpy.array([int(row['no_commits']), int(row['no_changed_files']), int(row['PR_size']),  int(row['project_age'])]) 
            project_ = ''
            for _, row_ in df_2.iterrows():
                project_2 = row_['project'] 
                pull_number_2 = (row_['pull_number'])
                is_gpt_pr_2 = 'GPT PR' if row_['is_gpt_pr'] == '1' else 'Not GPT PR'
                
                if project_ == project_2: continue

                points =  numpy.array([(row_['no_commits']), (row_['no_changed_files']), (row_['PR_size']), (row_['project_age'])])
                y =  numpy.array([(row_['no_commits']), (row_['no_changed_files']), (row_['PR_size']), (row_['project_age'])])
                #points =  numpy.array([int(row_['no_commits']), int(row_['no_changed_files']), int(row_['PR_size']),  int(row_['project_age'])])
                if numpy.isnan(points).any(): continue
                if numpy.count_nonzero(points) == 0: continue
                
                #points =  numpy.array([int(row_['no_commits']), int(row_['no_changed_files']), int(row_['PR_size']),  int(row_['project_age'])])
                point_2 =  numpy.array([
                    normalize(row_['no_commits'],points),
                    normalize(row_['no_changed_files'],points),
                    normalize(row_['PR_size'],points),
                    normalize(row_['project_age'],points)
                    ])
                #point_2 =  numpy.array([int(row_['no_commits']), int(row_['no_changed_files']), int(row_['PR_size']),  int(row_['project_age'])])
                
                jaccard_similiarity, jaccard_distance = jaccard_binary(point_1, point_2) #   
                manhattan_distance = manhattan(point_1, point_2)
                cosine_similiarity, cosine_distance = cosine(x,y)
                euclidean_distance = euclidean(point_1, point_2)
                #print(f' similiarity: {round(similiarity,2)} mdistance: {round(m_distance,2)} point 1: {point_1} and point 2: {point_2}')
                #input('points')
                phase_arr.append([f,
                                  project, pull_number, is_gpt_pr, row['event'], 
                                  x, point_1,
                                  abs(round(row['duration'],3)),
                                  project_2, pull_number_2, is_gpt_pr_2,row_['event'],
                                  y, point_2,
                                  abs(round(row_['duration'],3)), 
                                  round(jaccard_distance,3),
                                  round(jaccard_similiarity,3),
                                  round(manhattan_distance,3),
                                  round(cosine_distance,3),
                                  round(cosine_similiarity,3),
                                  round(euclidean_distance,3)
                                  ])
                project_ = project_2
            df_ = pd.DataFrame(phase_arr, columns=columns_)
            df_distance_all  = df_distance_all._append(df_)
            df_ = df_.sort_values(by=['euclidean_distance','duration_no_gpt'], ascending= [True,True]).head(1)
            print('first sorted element:', df_)
            df_distance = df_distance._append(df_,ignore_index=True)
           
    return round(df_distance,3), round(df_distance_all,3)

def phases_summary_stats():
    
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 

    file_path = directory / pathlib.Path("project_phases.json")
    data = get_json(file_path)
    
    
    projects = import_project_pulls().sort_values(['owner_login','name'])
    columns_1 = ['phase','is_GPT_PR','pr_status','is_event_gpt','duration']
    columns_2 =['is_GPT_PR','pr_status']
    df_status = pd.DataFrame(columns=columns_2)
    df_stats  = pd.DataFrame(columns=columns_1)

    
   #'at_submission', 
    phases = [
             'at_submission',
             'at_review', 
             'at_waiting_before_change', 
             'at_changed',
             'at_waiting_after_accepted', 
             'at_resolution']

    
    for _, row in projects.iterrows():#get_project():
        project = row['owner_login'] + '_' + row['name']
        pull_number = str(row['number'])
        status_arr = []
        phase_arr = []
        for projects in data:    
            if project in projects:
                is_gpt_pr = 'gpt assistance' if  projects[project][pull_number]['is_GPT_PR'] == 1 else 'not gpt assistance'
                pr_status = projects[project][pull_number]['status']
                status_arr.append([is_gpt_pr, pr_status]) 
                df_2 = pd.DataFrame(status_arr, columns=columns_2) 
                df_status = df_status._append(df_2,ignore_index=True)
                for phase in phases:

                    if  projects[project][pull_number][phase] == None: continue
                    
                    event_gpt = 'gpt assistance'  if projects[project][pull_number][phase]['gpt_assistance']==1 else 'not gpt assistance'
                    duration  = projects[project][pull_number][phase]['duration'] 
                    phase_arr.append([phase, is_gpt_pr, pr_status, event_gpt, duration]) 
                df_1 = pd.DataFrame(phase_arr, columns=columns_1) 
                print(df_1)
        if len(df_1) == 0: continue
        df_stats = df_stats._append(df_1,ignore_index=True)
            
                
    df_stats= df_stats.sort_values('phase')
    
    df_status = df_status.reset_index()
    df_status = df_status.drop(['index'], axis=1)
    
    df_stats = df_stats.reset_index()
    df_stats = df_stats.drop(['index'], axis=1)

    df_summary_status = df_status.groupby(['is_GPT_PR','pr_status']).agg(
        no_status =('pr_status', 'count'),
    ).reset_index()
    print(df_summary_status)
    df_summary_status.to_csv("summary_status.csv", index=False)

    
    
    summary_phases= df_stats.groupby(['phase','is_GPT_PR','is_event_gpt']).agg(
        count = ('is_event_gpt', 'count'),
        median_duration = ('duration', 'median'),
        mean_duration = ('duration', 'mean'),
        max_duration_in_hrs  = ('duration', 'max'),
        min_duration_in_hrs  = ('duration', 'min'),
    ).reset_index()
    print(summary_phases)
    summary_phases.to_csv("summary_phases.csv", index=False)

def stats_distance():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    path = directory / pathlib.Path('distance_all.csv') 
    df_ = pd.read_csv(path)  
    phase = [
        'at_review', 
        'at_waiting_before_change', 
        'at_changed',
        'at_resolution']
    df_ = df_.reset_index()
    df_ = df_.drop(['index'], axis=1)
    summary= df_.groupby(['phase', 'project_gpt','pull_number_gpt']).agg(
        count = ('event_gpt', 'count'),
        manhattan_median = ('manhattan_distance', 'median'),
        manhattan_mean   = ('manhattan_distance', 'mean'),
        manhattan_max  = ('manhattan_distance', 'max'),
        manhattan_min  = ('manhattan_distance', 'min'),
        cosine_simil_median = ('cosine_similarity', 'median'),
        cosine_simil_meam   = ('cosine_similarity', 'mean'),
        cosine_simil_max  = ('cosine_similarity', 'max'),
        cosine_simil_min  = ('cosine_similarity', 'min'),
        euclidean_mediam = ('euclidean_distance', 'median'),
        euclidea_mean   = ('euclidean_distance', 'mean'),
        euclidea_max  = ('euclidean_distance', 'max'),
        euclidea_min  = ('euclidean_distance', 'min'),
        jaccard_simil_median = ('jaccard_similiarity', 'median'),
        jaccard_simil_meam   = ('jaccard_similiarity', 'mean'),
        jaccard_simil_max  = ('jaccard_similiarity', 'max'),
        jaccard_simil_min  = ('jaccard_similiarity', 'min'),
    ).reset_index()
    summary.to_csv('summary_distance.csv')
    print(summary)

def spearmanr():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    path = directory / pathlib.Path('distance_all.csv') 
    df_ = pd.read_csv(path)  
    phase = [
        'at_review', 
        'at_waiting_before_change', 
        'at_changed',
        'at_resolution']
    df_ = df_.reset_index()
    df_ = df_.drop(['index'], axis=1)
    for p in phase:
        print('phase:', p)
        df_x = df_[(df_['phase']==p)]
        df_x = df_x.reset_index()
        df_x = df_x.drop(['index'], axis=1)
        
        x = df_x['manhattan_distance'].tolist() 
        y = df_x['cosine_distance'].tolist()

        corr, pval = stats.spearmanr(x, y)
        # print the result
        print("Spearman's correlation coefficient:", corr)
        print("p-value:", pval)

def main():
    df_, df_all = get_PRS_distance() 
    df_.to_csv('distance.csv', index=False) 
    df_all.to_csv('distance_all.csv', index=False)
    
    
  

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop collecting data")
        exit(1)