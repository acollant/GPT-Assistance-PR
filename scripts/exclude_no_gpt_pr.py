import json
import textwrap
import nltk
import re
import spacy
import csv
import pandas as pd
nlp = spacy.load("en_core_web_lg")#,disable=['parser', 'tagger','ner']) 
nlp.max_length = 1500000
import pathlib
#|((\w)\:|\/|\\|(\w))*((\/|\\)[a-z_\-\s0-9\.]*|chatgpt|gpt|openai)+(\.|(\w))+
#|([\w]|[\s])*(chatgpt|gpt|openAI|openai|azureai)([\s]|[a-zA-Z0-9])*(class|function(s)*|constructor(s)*|call(s)*|formatter|demo(s)*|source(s)*|connector(s)*|plugin|endpoint(s)*|model(s)*|api|API|gateway|service(s)*)([\s]|[a-zA-Z0-9])*
        

#(^[not](ask (to)*|create|pass|consult|sponsor|generate|documente|investigate|advice|suggest|modify|solve|support|update|summary|response|change|power|polish)+[\w]*[\s]+(by|with|from|per|via)+([\s]|[\w])*(gpt|chatgpt|openai))

REGEX_INCL = r"""((chatgpt|gpt|chat gpt|chat-gpt)[\s](say|get|write|suggest|tell|think|explain|offer|to explain|flawless|make some suggestion|walk me))
    |(https\:\/\/chat\.openai\.com(\/share\/)*[?a-zA-Z0-9@:%._\+~#=]*)
    |((some example)([a-z]|[\s]|[\-])+(by)[\s](gpt|chatgpt|openai|chat-gpt|coderabbit|gemini|chat gpt))
    |((gpt)[\-][0-9]+([a-z]|[\s])+(flawless))
    |((gpt)[\-][0-9]+([a-z]|[\s])+(make some suggestion))
    |((gpt walk me))
    |((ask (to)*|create|pass|consult|sponsor|generate|documente|investigate|advice|suggest|modify|solve|support|update|summary|response|change|power|polish|utilize|comment|write|improvement|improve|collaborate|collaboration|get)+[\s](by|one with|with|from|per|via|of)[\s](gpt|chatgpt|openai|chat-gpt|coderabbit|gemini|chat gpt|code review gpt))
    """

    
#code be get well and well gpt-4 its not flawless
#pattern_incl = re.compile(REGEX_INCL, re.VERBOSE | re.IGNORECASE)

REGEX_EXCL = r"""([A-Za-zÀ-ÿ]+[\s][\-|_|.|\s]*)+(chatgpt|gpt|openai)[\-|_]{1}[^(chat|gpt)][a-z0-9_\-]*
    |[(http(s)?):\/\/(www\.)?a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&\/=]*(chatgpt|gpt|openai)+)
    |([a-z]\:|\/|\\)((\/|\\)[a-z_\-\s0-9\.]+|(chatgpt|gpt|openai)+)+\.[a-z]{2,3}
    |([a-z]|[\s]|\/|\-|_)*(chatgpt|gpt|openai)(\-|_|[\s]|(@:%.))*([a-zA-Z0-9@:%._]+[\s]*(\-|_)*)
    |((like in the chatgpt)|(like the one from chatgpt))$
    |((spam)+[\s]*(chatgpt|gpt|openai))$
    |([a-z]|[\s]|[@:%_\+.~#?&\/=])*(chatgpt|gpt|openAI|openai|azureai)([\s]|[a-z0-9])*(label[s]*|class|function[s]*|constructor[s]*|call[s]*|formatter|demo[s]*|source[s]*|connector[s]*|plugin|endpoint[s]*|model[s]*|api|API|gateway|service[s]*)
    |(([a-z]|[\s])*((gpt|chatgpt|openai)(\-|_|[\s])*([0-9.]){1,6})+)
    |(([a-z]|[\s]|\-|_|[a-z0-9.])*(GRUB_GPT|grub_gpt))
    |([a-z]|[\s]|[@:%_\+.~#?&\/=]|\-)+(chatgpt|gpt|openai)$
    |((disk guid|mbr|MBR|qemu|QEMU|kvm|KVM|gpt partition(s)*))
    """
#pattern_excl = re.compile(REGEX_EXCL, re.VERBOSE | re.IGNORECASE)

#pattern_excl = re.compile(REGEX_EXCL, re.VERBOSE | re.IGNORECASE | re.UNICODE)
#pattern_incl = re.compile(REGEX_INCL, re.VERBOSE | re.IGNORECASE | re.UNICODE)
#gpt3.1
#gpt-chat.3.1
#gpt_chat 3.1.1
#gpt_chat 3.1

def lemmatize_word(text):
    text = text.lower().replace('"','').replace("'","").replace("`","").replace(":","").replace("(","").replace(")","").replace(",","").replace(">","").replace("<","").replace("│","").strip()
    text = text.replace('[','').replace(']','').replace(".","")
    doc = nlp(text)
    tokens = []
    #for token in doc:
    #    tokens.append(token)
    lemmatized_sentence = ' '.join([token.lemma_ for token in doc])
    lemmatized_sentence = text_partitions(lemmatized_sentence,' -')
    lemmatized_sentence = text_partitions(lemmatized_sentence,' /')

    return lemmatized_sentence

def search_heuristic_classification(data, url):
    classification = ''
    for data_ in data:
        for pull_ in data_: 
            if pull_["url"]==url:
                classification = pull_['classification']
                return classification
    return classification

def compare_labelled(data):
    file_name_out = 'gpt_pr_mention_all_out.json'
    data_heuristics = get_json(file_name_out)
    for pull_ in data:
        url_ = pull_["url"]
        classification = search_heuristic_classification(data_heuristics, url_)
        pull_['new_class'] = classification
    file_name_out = 'gpt_pr_mention_all_out_labelled_match.json'
    with open(file_name_out, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4) 
       

def x():    
    file_name_out = 'gpt_pr_mention_all_out_labelled_match.json'
    data = get_json(file_name_out)
    total_h1 = 0
    total_match_h1 = 0
    total_no_match_h1 = 0

    total_h2 = 0
    total_match_h2 = 0
    total_no_match_h2 = 0

    total_h3 = 0
    total_match_h3 = 0
    total_no_match_h3 = 0

    total_h4 = 0
    total_match_h4 = 0
    total_no_match_h4 = 0

    total_no_match = 0
    total_all = 0

    for pull_ in data:
        total_all+=1
        if pull_['gpt_projectname'] == 'yes':
            total_h1+=1
            if pull_['new_class'] == pull_['true_class']:
                total_match_h1+=1
            else:
                total_no_match_h1+=1
                print(f"pull different gpt_projectname: {pull_['url']}")

        
        if pull_['gpt_title'] == 'yes':
            total_h2+=1
            if pull_['new_class'] == pull_['true_class']:
                total_match_h2+=1
            else:
                total_no_match_h2+=1
                print(f"pull different gpt_title: {pull_['url']}")
        

        if pull_['gpt_filenames'] == 'yes':
            total_h3+=1
            if pull_['new_class'] == pull_['true_class']:
                total_match_h3+=1
            else:
                total_no_match_h3+=1
                print(f"pull different gpt_filenames: {pull_['url']}")
        

        if pull_['gpt_comments'] == 'yes':
            total_h4+=1
            if pull_['new_class'] == pull_['true_class']:
                total_match_h4+=1
            else:
                total_no_match_h4+=1
                print(f"pull different gpt_comments: {pull_['url']}")
        
        if pull_['new_class'] != pull_['true_class']:
            total_no_match +=1 
            
            #print(f"new class:{ pull_['new_class']} vs true class:{pull_['true_class']}")
   
    print(f'% accuracy h1 : {(total_match_h1/total_h1)*100} ({total_no_match_h1} were incorrectly matched out of the {total_h1})')   
    print(f'% accuracy h2 : {(total_match_h2/total_h2)*100} ({total_no_match_h2} were incorrectly matched out of the {total_h2})')   
    print(f'% accuracy h3 : {(total_match_h3/total_h3)*100} ({total_no_match_h3} were incorrectly matched out of the {total_h3})')   
    print(f'% accuracy h4 : {(total_match_h4/total_h4)*100} ({total_no_match_h4} were incorrectly matched out of the {total_h4})') 

    print(f'% not match : {(total_no_match/total_all)*100} ({total_no_match} were incorrectly matched out of the {total_all})')    


def stats(file_name):
    data = get_json(file_name)
    total_pull_request = 0
    no_assistance_pull_request = 0
    assistance_pull_request = 0
    assistance_pull_request_ = 0
    count_h1 = 0 #gpt_projectname
    count_h2 = 0 #gpt_title
    count_h3 = 0 #gpt_filenames
    count_h4 = 0 #gpt_comments
    count_all = 0
    count_all_no_comments = 0
    count_only_comments = 0
    for all_pr in data:
        for each_pr in all_pr:
            total_pull_request +=1
            if each_pr['classification'] == 'no assistance':
                no_assistance_pull_request+=1
            if each_pr['classification'] == '*assistance':
                assistance_pull_request_+=1
            if each_pr['classification'] == 'assistance':
                assistance_pull_request+=1
            if each_pr['gpt_projectname'] == 'yes':
                count_h1+=1
            if each_pr['gpt_title'] == 'yes':
                count_h2+=1
            if each_pr['gpt_filenames'] == 'yes':
                count_h3+=1
            if each_pr['gpt_comments'] == 'yes':
                count_h4+=1
            if each_pr['gpt_projectname'] == 'yes' and each_pr['gpt_title'] == 'yes' and each_pr['gpt_filenames'] == 'yes' and each_pr['gpt_comments'] == 'yes':
                count_all+=1
            if each_pr['gpt_projectname'] == 'yes' and each_pr['gpt_title'] == 'yes' and each_pr['gpt_filenames'] == 'yes':
                count_all_no_comments+=1
            if each_pr['gpt_projectname'] == 'no' and each_pr['gpt_title'] == 'no' and each_pr['gpt_filenames'] == 'no' and each_pr['gpt_comments'] == 'yes':
                count_only_comments+=1


    print(f'number of pull request: {total_pull_request}')        

    print(f'number of NO assistance pull request: {no_assistance_pull_request}')    
    print(f'number of * assistance pull request: {assistance_pull_request_}')    
    print(f'number of assistance pull request: {assistance_pull_request}')        
    print(f'number of  assistance pull request computed: {total_pull_request-no_assistance_pull_request}') 

    print(f'number of gpt_projectname: {count_h1}') 
    print(f'number of  gpt_title: {count_h2}') 
    print(f'number of  gpt_filenames: {count_h3}') 
    print(f'number of  gpt_comments: {count_h4}')   
    print(f'number of  all together: {count_all}')
    print(f'number of  all no comments: {count_all_no_comments}')    
    print(f'number of  only comments: {count_only_comments}')       

def chatgpt_ngrams(text, n):
    words = text.lower().split()
    ngrams = [' '.join(words[i:i+n]) for i in range(len(words))]
    return [ngram for ngram in ngrams if set(['gpt','chatgpt','openai']).intersection(set(re.split(r'(gpt|chatgpt|openai)',ngram.lower())))]
    #return [ngram for ngram in ngrams if ['gpt','chatgpt','openai'] in ngram.lower().split()]

def ngrams_partitions(ngrams, char_ ):
    ngrams_ = []
    for ngram in ngrams:
        hyphens = len(ngram.split(char_.strip())) - 1
        ngram_ = ngram
        if hyphens > 0:
            for _ in range(0,hyphens):
                partitions = list(ngram_.partition(char_))
                ngram_ = ''.join(s.strip() for s in list(partitions))      
        ngrams_.append(ngram_)
    return ngrams_

def text_partitions(text, char_):
    hyphens = len(text.split(char_.strip())) - 1
    if hyphens > 0:
        for _ in range(0,hyphens):
            partitions = (text.partition(char_))
            text = ''.join(s.strip() for s in list(partitions)) 
    return text

def get_gpt_exclusion_pattern(text):
    pattern_excl = re.compile(REGEX_EXCL, re.VERBOSE | re.IGNORECASE)# re.compile(reg_, re.MULTILINE)
    return pattern_excl.match(text)

def get_gpt_inclusion_pattern(text):
    pattern_incl = re.compile(REGEX_INCL, re.VERBOSE | re.IGNORECASE)# re.compile(reg_, re.MULTILINE)
    return pattern_incl.match(text)

def override_exclussion(text):
    ngrams_ = []
    pattern_matched = None
    text_lema = lemmatize_word(text.lower())
    ngrams_ = [text_lema]
    ngrams = chatgpt_ngrams(text_lema,10)
    
    if len(ngrams_) > 0:
        for ngram in ngrams:
            if 'gpt' in ngram or 'chatgpt' in ngram or 'openai' in ngram:
                pattern_matched = get_gpt_inclusion_pattern(ngram) 
                if pattern_matched != None: break
    return pattern_matched
    
def apply_manual_inspection():
    pass

def import_project_pulls():
    headers = [*pd.read_csv(("projects_gpt.csv"), nrows=1)]
    return  pd.read_csv(("projects_gpt.csv"), header=0, usecols=["owner_login" , "name", "number"] , 
                        low_memory=False,
                        quoting=csv.QUOTE_ALL, escapechar="\\")

def check_events_gpt():
    df_projects_gpt = get_csv('projects_gpt.csv') #import_project_pulls().sort_values(by='owner_login')#
    data = get_json('gpt_pr_mention_all_events.json')
    columns_ = ['owner_login','name','number','event','url','is_gpt_for']
    data_ =[]
    df_events_all = pd.DataFrame(columns=columns_)
    #df_events = pd.DataFrame(columns=columns_)
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
                        
        df_events = pd.DataFrame(data_,columns=columns_)
        #df_events_all = df_events_all._append(df_events,ignore_index = True)                    
    df_events.to_csv('events_gpt.csv')


def apply_all_patterns(data, file_name_out ):
    df_true = get_csv('true_class.csv') #original
    
    for all_pr in data:
        for each_pr in all_pr:
            each_pr['classification'] = 'assistance'
            each_pr['gpt_projectname'] = '' 
            each_pr['gpt_title']  =    ''
            each_pr['gpt_filenames']= ''
            each_pr['gpt_comments']= ''

            project_name = each_pr['project'].lower()  
            title        = str(each_pr['pr_title']).lower()
            file_names   = each_pr['modified_files']
            phases       = each_pr['GPTMention']
            PR_number    = each_pr['pr_number']

            url = each_pr['url'].lower().strip() 

            print(f'project name:{project_name}, PR#: {PR_number}')
            
            matched = apply_pattern_single_repositoryname(project_name) 
            each_pr['gpt_projectname'] = 'yes' if matched != None else 'no'
            #'project name is chatgpt implementation related' if matched != None else 'project name is not chatgpt implementation related' 
            matched =  apply_pattern_single_repositorytitle(title)
            each_pr['gpt_title']  =  'yes' if matched != None else 'no'
            # 'project title is chatgpt implementation related' if matched != None else 'project title is not chatgpt implementation related' 
            matched =  apply_pattern_single_filename(file_names)
            each_pr['gpt_filenames']= 'yes' if matched != None else 'no'
            #'changed file name is chatgpt implementation related' if matched != None else 'changed file name is not chatgpt implementation related' 
            each_pr['gpt_comments']=  'no' #'comment/body is not chatgpt implementation related'    
            to_incluide = False
            for phase in phases:
                comment =phase['body'].lower().replace('"','').replace("'","").replace("`","").replace(":","").replace("(","").replace(")","").replace(",","").replace(">","").replace("<","").replace("│"," ").strip()
                comment = comment.replace("[","").replace("]","")
                phase['gpt_in_event'] = 'no'
                phase['event_type'] = 'gpt not assistance'
                if comment != "":
                    if apply_pattern_single_body(comment.lower())  != None: 
                        phase['gpt_in_event'] = 'yes' 
                        each_pr['gpt_comments'] =  'yes' # yes original #'comment/body is chatgpt implementation related'
                        phase['event_type'] = 'gpt not assistance'
                    
                    if override_exclussion(comment.lower()) != None:
                        phase['event_type'] = 'gpt assistance'
                    
                    if to_incluide == False:
                        if override_exclussion(comment.lower()) != None:
                            to_incluide = True
                   
            if to_incluide == True:
                print(f'project name to incluide:{project_name} and url: {url}')
                each_pr['classification'] = 'assistance' 
                #input("to include") 
            else:
                if each_pr['gpt_projectname'] == 'yes' or each_pr['gpt_title'] == 'yes' or each_pr['gpt_filenames'] == 'yes' or each_pr['gpt_comments'] == 'yes':
                    each_pr['classification'] = 'no assistance'
            
            class_ = df_true.loc[(df_true['url'] == url)] #df_true[['true_class']][(df_true['url'] == url)]
            if not class_.empty:
                print('overrride:', df_true.at[class_.index.values[0],'true_class'])
                each_pr['classification'] = df_true.at[class_.index.values[0],'true_class']
                #input("override")
                
    with open(file_name_out, "w") as jsonFile:
        json.dump(data, jsonFile, indent=7)

def apply_all_pattern(data, file_name_out):
    for all_pr in data:
        for each_pr in all_pr:
            each_pr['classification'] = 'assistance'
            each_pr['classification_type'] = ''
            
            #apply patterns in project name
            project_name = each_pr['project'].lower()  
            
            print(f'project:{project_name}')
            print(project_name,': ',apply_pattern_single_repositoryname(project_name) )
            if apply_pattern_single_repositoryname (project_name) != None:
                each_pr['classification'] = 'no assistance'
                each_pr['classification_type'] = 'gpt pattern in project name'
            else: 
                #apply patterns in project title
                title = str(each_pr['pr_title']).lower()
                #print(title,': ',apply_pattern_single_repositorytitle(title) )
                if apply_pattern_single_repositorytitle(title) != None:
                    each_pr['classification'] = 'no assistance'
                    each_pr['classification_type'] = 'gpt pattern in PR title'
                else:
                    #apply patterns in file names
                    file_names = each_pr['modified_files']
                    if apply_pattern_single_filename(file_names) != None:
                        each_pr['classification'] = 'no assistance'
                        each_pr['classification_type'] = 'gpt pattern in file names'
                    else:
                        #appy patterns in the body/comments
                        phases = each_pr['GPTMention']
                        for phase in phases:
                            comment =phase['body'].strip()
                            if comment != "":
                                if apply_pattern_single_body(comment) != None:
                                    each_pr['classification'] = 'no assistance'
                                    each_pr['classification_type'] = 'gpt pattern in body/comment'
                                    break

    with open(file_name_out, "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)
                                
def apply_pattern_single_body(comment):
    ngrams_ = []
    pattern_matched = None
    text_lema = lemmatize_word(comment.lower())
    ngrams_ = [text_lema]
    ngrams = chatgpt_ngrams(text_lema,10)
    
    if len(ngrams_) > 0:
        for ngram in ngrams:
            if 'gpt' in ngram or 'chatgpt' in ngram or 'openai' in ngram:
                pattern_matched = get_gpt_exclusion_pattern(ngram) 
                if pattern_matched != None: break
                
    return pattern_matched 


def apply_pattern_single_filename(filenames):
    pattern_matched = None
    for filename in filenames:
        text_lema = lemmatize_word(filename.lower())
        if len(text_lema) > 0:
            pattern_matched = get_gpt_exclusion_pattern(text_lema)
            if pattern_matched != None: 
                break
    return  pattern_matched 

def apply_pattern_single_repositoryname(project_name):
    project_name = (project_name.lower().split('/'))[1]
    #print(f'project fun:{project_name}')
    text_lema = lemmatize_word(project_name.lower())
    #print(f'project lema:{text_lema}')
    pattern_matched = ''
    if len(text_lema) > 0: pattern_matched = get_gpt_exclusion_pattern(text_lema) 
    return  pattern_matched  

def apply_pattern_single_repositorytitle(project_title):
    project_title = project_title.lower()   
    text_lema = lemmatize_word(project_title.lower())
    #print(f'title:{text_lema}')
    pattern_matched = None
    if len(text_lema) > 0: pattern_matched = get_gpt_exclusion_pattern(text_lema) 
    return  pattern_matched  

def apply_pattern_all_body(data):
    for p in data:
        gpt_pr = p['GPTMention']
        for e in gpt_pr:#range(0,len(p['GPTMention'])):
            body = e['body']
            ngrams_ =[]
            e['classification'] = 'assistance'
            e['classification_type'] = 'NA'
            if body != "":
                text_lema = lemmatize_word(body.lower())
                ngrams = chatgpt_ngrams(text_lema,10)
                ngrams_ = [text_lema]
                if len(ngrams) > 0:
                    ngrams_ = ngrams_partitions(ngrams,' -')
                    ngrams_ = ngrams_partitions(ngrams_,' /')
               
                for n in ngrams_:
                    if get_gpt_exclusion_pattern(n) != None:
                        e['classification'] = 'implementation'
                        e['classification_type'] = 'gpt in the PR body'
                        break
                    
    #with open("data_all_n.json", "w") as jsonFile:
    with open("GPT_mention_body_api.json", "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)

def apply_pattern_all_filename(data):
    #n_line =0
    for d in data:
        for p in d:
            #n_line+=1
            
            #print(f"line number: {n_line} and project: {p['project'].lower()}")
            p['classification'] = 'assistance'
            p['classification_type'] = 'NA'
            file_names = p['modified_files']
            for file_name in file_names:
                #filename = code_[4:].strip()
                text_lema = lemmatize_word(file_name.lower().replace('"','').replace("'","").replace(",",''))
                text_lema = text_partitions(text_lema,' -')
                text_lema = text_partitions(text_lema,' /')
                        
                if len(text_lema) > 0:
                    if get_gpt_exclusion_pattern(text_lema) != None:
                        p['classification'] = 'implementation'
                        p['classification_type'] = 'gpt in modified file (code)'
                        break
   
    with open("gpt_pull_request_mention_out.json", "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)
    
def apply_pattern_all_repositoryname(data):
    for p in data:
        project_name = p['project'].lower().split('/')[1]
        text_lema = lemmatize_word(project_name.lower())
       
        text_lema = text_partitions(text_lema,' -')
        text_lema = text_partitions(text_lema,' /')
        #print(text_lema)
        #input('stop')
        p['classification'] = 'assistance'
        p['classification_type'] = 'NA'
        if len(text_lema) > 0:
            if get_gpt_exclusion_pattern(text_lema) != None:
                p['classification'] = 'implementation'
                p['classification_type'] = 'gpt in project name'
                
    
    #with open("data_all_n.json", "w") as jsonFile:
    with open("GPT_mention_project_name.json", "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)
    
def apply_pattern_all_repositorytitle(data):
    for p in data:
        title = str(p['pr_title']).lower()
        text_lema = lemmatize_word(title.lower())
        
        text_lema = text_partitions(text_lema,' -')
        text_lema = text_partitions(text_lema,' /')
        #print(text_lema)
        #input('stop')
        p['classification'] = 'assistance'
        p['classification_type'] = 'NA'
        if len(text_lema) > 0:
            if get_gpt_exclusion_pattern(text_lema) != None:
                p['classification'] = 'implementation'
                p['classification_type'] = 'gpt in PR title'
            
    #with open("data_all_n.json", "w") as jsonFile:
    with open("GPT_mention_pr_title.json", "w") as jsonFile:
        json.dump(data, jsonFile, indent=4)

def get_json(file_name):
    # Opening JSON file
    f = open(file_name,'r')
    # returns JSON object as  a dictionary
    data = json.load(f)
    f.close()
    return  data

def get_csv(file_name):
    df = pd.read_csv(file_name)
    return df

def check_body(data):
    for all_pr in data:
        for each_pr in all_pr:
            each_pr['classification'] = 'assistance'
            each_pr['gpt_projectname'] = '' 
            each_pr['gpt_title']  =    ''
            each_pr['gpt_filenames']= ''
            each_pr['gpt_comments']= ''

            project_name = each_pr['project'].lower()  
            title        = str(each_pr['pr_title']).lower()
            file_names   = each_pr['modified_files']
            phases       = each_pr['GPTMention']
            PR_number    = each_pr['pr_number']

            url = each_pr['url'].lower() 

            print(f'project name:{project_name}, PR#: {PR_number}')
            for phase in phases:
                comment =phase['body'].lower().replace('"','').replace("'","").replace("`","").replace(":","").replace("(","").replace(")","").replace(",","").replace(">","").replace("<","").strip()
                phase['gpt_in_event'] = 'no'
                if comment != "":
                    apply_pattern_single_body(comment.lower())
                    
 
def apply_pattern_single_body_wrong(comment):
    ngrams_ = []
    pattern_matched = None
    text_lema = lemmatize_word(comment.lower())
    #if len(comment)>5000:
    #    pattern_matched = get_gpt_exclusion_pattern(text_lema)
    #    return pattern_matched

    print(f'comment: {comment}')
    input('comment')

    print(f'text_lema: {text_lema}')
    input('text_lema')
   
    ngrams_ = [text_lema]
    ngrams = chatgpt_ngrams(text_lema,10)
    print(f'ngrams: {ngrams}')
    input('ngrams')

    if len(ngrams_) > 0:
        for ngram in ngrams:
            print(f'ngram: {ngram}')
            input('ngram')
            if 'gpt' in ngram or 'chatgpt' in ngram or 'openai' in ngram:
                print(f'len ngrams:{len(ngram)}')
                gpt_inside_parag = re.split(r'(gpt|chatgpt|openai)', ngram)
                print(f'gpt_inside_parag:{gpt_inside_parag}')
                for gpt in gpt_inside_parag:
                    print(f'gpt:{get_gpt_exclusion_pattern(gpt) }')
                input('stop')
                if len(ngram)>1000:
                    gpt_inside_parag = re.split(r'(gpt|chatgpt|openai)', ngram)
                    for gpt in gpt_inside_parag:
                    #    text_ = ' '.join(gpt_inside_parag[i:i+1])
                        pattern_matched = get_gpt_exclusion_pattern(gpt) 
                        if pattern_matched != None: break
                else:
                    print('pattern_matched before')
                    pattern_matched = get_gpt_exclusion_pattern(ngram) 
                    print(f'pattern_matched:{pattern_matched}')
                    if pattern_matched != None: break
    return pattern_matched 

def json_to_csv(data):
    csv_data = open('to_inspect_all.csv', 'w', newline='')
    csv_assistance = open('to_inspect_assistance.csv', 'w', newline='')
    csv_no_assistance = open('to_inspect_no_assistance.csv', 'w', newline='')

    header = ['url','project','gpt_in_project_name','gpt_in_title','gpt_in_file_names','gpt_in_comments','heuristic_class']
    csv_writer_all = csv.writer(csv_data)
    csv_writer_all.writerow(header)

    csv_writer_assistance =  csv.writer(csv_assistance)
    csv_writer_assistance.writerow(header)
    
    csv_writer_no_assistance =  csv.writer(csv_no_assistance)
    csv_writer_no_assistance.writerow(header)

    for pr_data in data:
        for d in pr_data:
            project_name = d['project']
            url = d['url']
            gpt_in_project_name = d['gpt_projectname']
            gpt_in_title = d['gpt_title']
            gpt_in_file_names = d['gpt_filenames']
            gpt_in_comments = d['gpt_comments']
            heuristic_class = d['classification']
            values = [url, project_name, gpt_in_project_name, gpt_in_title, gpt_in_file_names, gpt_in_comments, heuristic_class]
            csv_writer_all.writerow(values)
            if heuristic_class == 'assistance': csv_writer_assistance.writerow(values)
            if heuristic_class == 'no assistance': csv_writer_no_assistance.writerow(values)

    csv_data.close()


def main():
    directory = pathlib.Path("data")
    directory = pathlib.Path(__file__).parent / directory 
    #check_events_gpt()
    #exit()
    
    #df_true = get_csv('true_class.csv')
    #class_ = df_true.loc[(df_true['url'] == 'https://github.com/azure/azure-kusto-java/pull/301')] #df_true[['true_class']]
    #print(class_)
    #print(true_class['true_class'])
    #if not class_.empty:
    #    print(class_['true_class'])
    #exit()
    #print(data_true_class['url'])
    #print(data_true_class['true_class'])
    
    
    #===== export json to csv ========================
    #file_name_out = 'gpt_pr_mention_all_out.json'
    #data = get_json(file_name_out)
    #json_to_csv(data)
    #exit()
    #=================================================

    ## === all PRs all attributes ===
    file_name_in  = directory / pathlib.Path('gpt_pull_requests_filenames.json')
    #file_name_out = 'gpt_pr_mention_all_out.json' #ORIGINAL use only when call apply_all_patterns
    file_name_out = directory / pathlib.Path('gpt_pr_mention_all_out.json') #use only when call apply_all_patterns

    # ====================== test ======================
    #file_name_in = 'test.json'
    #file_name_out = 'test_out.json'
    
    #data = get_json(file_name_in)
    ##check_body(data)

    # ================== process for patternS ==================
    data = get_json(file_name_in)
    #apply_all_patterns(data,file_name_out) #add where gpt related pattern is found
    ##exit()
    ## =============================================

    # ================== process for pattern ==================
    ##file_name_out = 'gpt_pr_mention_all_out.json' #use only when call apply_all_pattern
    apply_all_pattern(data, file_name_out) #only pr 
    #stats(file_name_out)
    #========================================================


    #============= stats ==============================
    #file_name = 'gpt_pr_mention_all_out_labelled.json'
    #data_labelled = get_json(file_name)
    #compare_labelled(data_labelled)
    #x()
    #stats(file_name_out)
    #===================================================
    
    
    #apply_pattern_file_name(data)
    #apply_pattern_pr_title(data)
    #apply_pattern_body(data)
    #apply_pattern_repository_name(data)

     #print('class: ', class_)
                #print('index: ', class_.index.values[0])
                #print('pos:', df_true.at[class_.index.values[0],'true_class'])
                #each_pr['classification'] = df_true.at[class_.index.values[0],'true_class']
                #print("each_pr['classification']:", each_pr['classification'])
                #input("")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop collecting data")
        exit(1)
    