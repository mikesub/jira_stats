#!/usr/bin/env python3
import sys
import requests
import config
from work_hours import hours_spent
from copy import deepcopy
import numpy

quota_labels = {'mc', 'tb', 'tp', 'eng', 'in'}
output = ''

try:
    debug_issue = sys.argv[1]
except IndexError:
    debug_issue = False


def log(*args):
    if debug_issue:
        print(*args)


def make_request(url, **kwargs):
    r = requests.post(url, **kwargs)
    r.raise_for_status()
    return r.json()


def includes_status_change(item):
    return any([i['field'] == 'status' for i in item['items']])


def includes_project_change(item):
    return any([(i['field'] == 'project' and i['toString'] == 'API') for i in item['items']])


def extract_status_change(item):
    entry = [i for i in item['items'] if i['field'] == 'status'][0]
    r = {
        'date': item['created'],
        'from': entry['fromString'],
        'to': entry['toString'],
    }
    return r


def extract_transitions(histories):
    histories_ = []
    if any([includes_project_change(i) for i in histories]):
        project_change_encountered = False
        for i in histories:
            if includes_project_change(i):
                project_change_encountered = True
            if project_change_encountered:
                histories_.append(i)

    else:
        histories_ = histories

    return [extract_status_change(i) for i in histories_ if includes_status_change(i)]


def strip_issue(item):
    log(item['key'], item['fields']['summary'])
    return {
        'key': item['key'],
        'labels': item['fields']['labels'],
        'summary': item['fields']['summary'],
        'transitions': extract_transitions(item['changelog']['histories']),
    }


def get_hours(transitions):
    hours = {}
    prev = None
    for transition in transitions:
        log('-----------------------')
        log(format(transition['date']))
        log('{} > {}'.format(transition['from'], transition['to']))
        if not prev:
            prev = transition['date']
            log('initial')
            continue
        hours_spent_ = hours_spent(prev, transition['date'])
        if transition['from'] in hours:
            hours[transition['from']] += hours_spent_
            log('{} +{} = {}'.format(
                transition['from'],
                hours_spent_,
                hours[transition['from']],
            ))
        else:
            hours[transition['from']] = hours_spent_
            log(transition['from'], hours_spent_)
        prev = transition['date']
    return hours


def convert_hours(i):
    r = deepcopy(i)
    hours = get_hours(i['transitions'])
    r['transitions'] = hours
    if debug_issue:
        log('-----------------------')
        for k, v in hours.items():
            print(str(v).rjust(3), k)
    return r


def calculate_totals(i):
    r = deepcopy(i)
    total = sum(r['transitions'].values())
    r['transitions']['_total_wo_todo'] = sum(v for k, v in r['transitions'].items() if k not in config.skipped_statuses)
    r['transitions']['_total'] = total
    log(str(total).rjust(3), 'total')
    log(str(r['transitions']['_total_wo_todo']).rjust(3), 'w/o To Do')
    return r

issues = make_request(
    '{}/rest/api/2/search'.format(config.url),
    auth=(config.login, config.password),
    json={
        "jql": config.jql if not debug_issue else 'key={}'.format(debug_issue),
        "maxResults": 300,
        "fields": ['labels', 'summary'],
        "expand": ['changelog']
    },
)['issues']

issues = [strip_issue(i) for i in issues]
issues = [convert_hours(i) for i in issues]
issues = [calculate_totals(i) for i in issues]

if debug_issue:
    sys.exit()

result = {k: 0 for k in quota_labels}
issues_by_quota = {k: [] for k in quota_labels}

for issue in issues:
    if not len(issue['labels']):
        output += 'skip {} {}\n'.format(issue['key'].ljust(7), issue['summary'])
        continue
    issue_quota_labels = quota_labels.intersection(issue['labels'])
    hours_share = issue['transitions']['_total_wo_todo'] / len(issue_quota_labels)
    for q in issue_quota_labels:
        result[q] += hours_share

total_time = sum(result.values())
percentage = {k: round(v/total_time*100) for k, v in result.items()}

for k, v in percentage.items():
    '\n{} {}%\n'.format(k.upper().ljust(3), v)


for label in quota_labels:
    for issue in issues:
        if label not in issue['labels']:
            continue
        issues_by_quota[label].append(issue)

for quota, issues_ in issues_by_quota.items():
    output += '\n{} {}%\n'.format(quota.upper().ljust(3), percentage[quota])
    for issue in sorted(issues_, key=lambda i: i['transitions']['_total_wo_todo'], reverse=True):
        output += '{} {} {}\n'.format(
                issue['key'].ljust(7),
                str(issue['transitions']['_total_wo_todo']).rjust(3),
                issue['summary']
            )

print(output)
