import requests
from ruamel.yaml import YAML
from datetime import date, datetime, timedelta
import logging
import sys, getopt
import click

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
    if resp_results is not None:
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

@click.group()
def cli():
    """Tempo Automation"""

@cli.command()
@click.option('--apikey')
@click.option('--accountid')
@click.option('--startdate', type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option('--enddate', type=click.DateTime(formats=["%Y-%m-%d"]))

def dump(apikey, accountid, startdate, enddate):
    if (apikey is None) or (accountid is None) or (startdate is None) or (enddate is None):
        logging.error(
            'Missing required parameters, workbook.py dump --apiKey <apiKey> --accountId <jiraAccountId> --startDate <startDate> --endDate <endDate>'
        )
        sys.exit(1)
    startdate = startdate.date()
    enddate = enddate.date()

    allDates = [startdate+timedelta(days=x) for x in range((enddate-startdate).days)]
    payload = {}
    for d in allDates:
        existing = find_worklog(apikey, accountid, d)
        strDate = d.isoformat()
        payload[strDate] = []
        for e in existing:
            entry = {}
            timeSpentSeconds = e['timeSpentSeconds']
            issueKey = e['issueKey']
            timeSpentHours = timeSpentSeconds / 60 / 60
            entry['ticket'] = issueKey
            entry['time'] = timeSpentHours
            payload[strDate].append(entry)
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.dump(payload, sys.stdout)


@cli.command()
@click.option('--apikey')
@click.option('--accountid')
@click.option('--input')
@click.option('--dryrun', is_flag=True, default=False)

def populate(apikey, accountid, input, dryrun):
    if (apikey is None) or (accountid is None) or (input is None) or (dryrun is None):
        logging.error(
            'Missing required parameters, workbook.py populate --apiKey <apiKey> --accountId <jiraAccountId> --input <yaml file>'
        )
        sys.exit(1)

    try: 
        with open(input, 'r') as workbook:
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
                "authorAccountId": accountid
            }
            offset = timedelta(seconds=timeSpentSeconds)
            startTime = startTime + offset
            timecard.append(payload)
        existing = find_worklog(apikey, accountid, currentDay)
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
            
            if dryrun is False:
                for worklogId in worklogIds:
                    status, error = delete_worklog(apikey, worklogId)
                    if not status:
                        logging.error(
                            f'Could not delete the worklogId {worklogId} due to {error}' 
                        )
                        sys.exit(1)
                    else:
                        logging.info(
                            f'Deleted worklog entry for {currentDay}'
                        )
            else:
                logging.info(
                    f'''The following entries in Tempo would be replaced by the local config for {currentDay}: 
{existing_clean}
                    '''
                )


        if dryrun is False:
            for entry in timecard:
                status, error = create_worklog(apikey, entry)
                if not status:
                    logging.error(
                        f'Could not create the worklog entry for {entry} due to {error}' 
                    )
                    sys.exit(1)
                else:
                    logging.info(
                        f'Successfully created worklog entry for {currentDay}'
                    )
        else:
            logging.info(
                    f'''The following entries in Tempo would be created for {currentDay}: 
{timecard}
                    '''
                )

if __name__ == "__main__":
    #main(sys.argv[1:])
    cli()