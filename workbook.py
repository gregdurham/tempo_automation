import requests
from ruamel.yaml import YAML
from datetime import date, datetime, timedelta
import logging
import sys, getopt

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

def create_worklog(apiKey, entry):
    headers = {"Authorization": f"Bearer {apiKey}"}
    url = f'https://api.tempo.io/core/3/worklogs'
    r = requests.post(url, headers=headers, json=entry)
    status_code = r.status_code
    resp = r.json()
    if status_code == 200:
        return True, ''
    else:
        return False, resp

def delete_worklog(apiKey, worklogId):
    headers = {"Authorization": f"Bearer {apiKey}"}
    url = f'https://api.tempo.io/core/3/worklogs/{worklogId}'
    r = requests.delete(url, headers=headers)
    status_code = r.status_code
    if status_code == 204:
        return True, ''
    else:
        resp = r.json()
        return False, resp

def find_worklog(apiKey, accountId, currentDay):
    payload = {'from': currentDay, 'to': currentDay}
    headers = {"Authorization": f"Bearer {apiKey}"}
    url = f'https://api.tempo.io/core/3/worklogs/user/{accountId}'
    r = requests.get(url, params=payload, headers=headers)
    resp = r.json()
    resp_results = resp.get('results')
    results = []
    
    
    for res in resp_results:
        model = {
            "issueKey": res['issue']['key'],
            "timeSpentSeconds": res.get('timeSpentSeconds'),
            "startDate": res.get('startDate'),
            "startTime": res.get('startTime'),
            "authorAccountId": res['author']['accountId'],
            "tempoWorklogId": res.get('tempoWorklogId')
        }
        results.append(model)

    return results

def main(argv):
    inputfile = None
    accountId = None
    apiKey = None

    try:
        opts, args = getopt.getopt(argv,"hi:a:k",["ifile=","accountId=", "apiKey="])
    except getopt.GetoptError:
        logging.error('workbook.py -i <inputfile> -a <jiraAccountId> -k <apiKey>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            logging.info('workbook.py -i <inputfile> -a <jiraAccountId> -k <apiKey>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-a", "--accountId"):
            accountId = arg
        elif opt in ("-k", "--apiKey"):
            apiKey = arg
    if (inputfile is None) or (accountId is None) or (apiKey is None):
        logging.error(
            'Missing required parameters, workbook.py -i <inputfile> -a <jiraAccountId> -k <apiKey>'
        )
        sys.exit(1)

    try: 
        with open(inputfile, 'r') as workbook:
            try:
                data = YAML(typ='safe', pure=True).load(workbook)
            except ScannerError as e:
                logging.error(
                    'Error parsing yaml of configuration file '
                    '{}: {}'.format(
                        e.problem_mark,
                        e.problem,
                    )
                )
                sys.exit(1)
    except FileNotFoundError:
        logging.error(
            'Error opening configuration file {}'.format(file_path)
        )
        sys.exit(1)
    
    



    for currentDay, logItems in data.items():
        startTime = datetime(currentDay.year, currentDay.month, currentDay.day)
        timecard = []
        for logItem in logItems:
            ticket = logItem.get('ticket')
            timeSpent = logItem.get('time')
            if (ticket is None) or (timeSpent is None):
                logging.error(
                    'Missing ticket or time in one of the worklog items for ' f'{currentDay}' 
                )
                sys.exit(1)

            timeSpentSeconds = int(timeSpent * 60 * 60)
            
            payload = {
                "issueKey": ticket,
                "timeSpentSeconds": timeSpentSeconds,
                "startDate": currentDay.isoformat(),
                "startTime": startTime.strftime("%H:%M:%S"),
                "authorAccountId": accountId
            }
            offset = timedelta(seconds=timeSpentSeconds)
            startTime = startTime + offset
            timecard.append(payload)
        existing = find_worklog(apiKey, accountId, currentDay)
        existing_clean = [{x:d[x] for x in d if x != 'tempoWorklogId'} for d in existing]
        worklogIds = [d['tempoWorklogId'] for d in existing]
        
        if timecard == existing_clean:
            logging.info(
                'No differences found for ' f'{currentDay}' 
            )
            continue
        else:
            logging.info(
                'Differences found in worklog for date ' f'{currentDay}' 
            )

            for worklogId in worklogIds:
                status, error = delete_worklog(apiKey, worklogId)
                if not status:
                    logging.error(
                        f'Could not delete the worklogId {worklogId} due to {error}' 
                    )
                    sys.exit(1)
        
        for entry in timecard:
            status, error = create_worklog(apiKey, entry)
            if not status:
                logging.error(
                    f'Could not create the worklog entry for {entry} due to {error}' 
                )
                sys.exit(1)

if __name__ == "__main__":
    main(sys.argv[1:])