# Tempo Automation

Automates the population of your Tempo Timesheet

## Getting started

This tool reads a provided yaml file containing the day of the week, tickets worked on, and how much time (in hours) was spent on it. 

Example:
```sh
---
2022-06-01:
    - ticket: ABC-123
      time: 1
    - ticket: ABC-245
      time: 1
    - ticket: ABC-549
      time: 6
```

Provided the above yaml file, this will populate the time in Tempo in order of the provided tickets. Time starts at 00:00:00, for each item worked on, the tool will offset the time by however long the previous ticket was, in the above example: 

ABC-123 was started at 00:00:00 on 2022-06-01, and an hour was spent working on it. 

ABC-245 was started at 00:01:00 on 2022-06-01, and an hour was spent working on it. 

ABC-549 was started at 00:02:00 on 2202-06-01, and 6 hours was spent working on it. 

Multiple days can be provided.


Example:
```sh
---
2022-06-01:
    - ticket: ABC-123
      time: 1
    - ticket: ABC-245
      time: 1
    - ticket: ABC-549
      time: 6

2022-06-02:
    - ticket: ABC-123
      time: 1
    - ticket: ABC-245
      time: 1
    - ticket: ABC-549
      time: 6
...
```

The tool is a "desired" state, which means that the config file is treated as the source of truth which means:
1. It will for each day check for the current state from the API
2. It will for each day compare the file data with what was returned in (1)
3. If differences exist it will delete the items on that day
4. It will populate the timesheet as described in the yaml file

This means, if changes were made via the UI, the tool will remove these. 

How to install:
```sh
pip install -r requirements.txt

```

How to run:
```sh
python workbook.py -i <yaml file> -a <account ID> --apiKey <api key generated in tempo>
```
To get a Tempo API key:
```sh
Go to Tempo>Settings, scroll down to Data Access and select API integration.
```
To get your Account ID (atlassian):
```sh
https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-myself/#api-group-myself
```

I used the developer tools while in JIRA to get the Account ID from one of the requests.


