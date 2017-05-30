#!/usr/bin/env python3

import sys
from copy import deepcopy
import requests
import config
from work_hours import hours_spent


try:
    ISSUE_TO_DEBUG = sys.argv[1]
except IndexError:
    ISSUE_TO_DEBUG = False


def log(*args):
    if ISSUE_TO_DEBUG:
        print(*args)


def make_request(url, **kwargs):
    req = requests.post(url, **kwargs)
    req.raise_for_status()
    return req.json()


def includes_status_change(item):
    return any([i['field'] == 'status' for i in item['items']])


def includes_project_change(item):
    return any([(i['field'] == 'project' and i['toString'] == 'API') for i in item['items']])


def extract_status_change(item):
    entry = [i for i in item['items'] if i['field'] == 'status'][0]
    result = {
        'date': item['created'],
        'from': entry['fromString'],
        'to': entry['toString'],
    }
    return result


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
    result = deepcopy(i)
    hours = get_hours(i['transitions'])
    result['transitions'] = hours
    if ISSUE_TO_DEBUG:
        log('-----------------------')
        for key, value in hours.items():
            print(str(value).rjust(3), key)
    return result


def calculate_totals(i):
    result = deepcopy(i)
    total = sum(result['transitions'].values())
    total_dev = sum(v for k, v in result['transitions'].items() if k not in config.SKIPPED_STATUSES)
    result['transitions']['_total_dev'] = total_dev
    result['transitions']['_total'] = total
    log('-----------------------')
    log(str(total).rjust(3), 'Time Total')
    log(str(result['transitions']['_total_dev']).rjust(3), 'Time in Development')
    return result


def get_issues_time():
    result = make_request(
        '{}/rest/api/2/search'.format(config.URL),
        auth=(config.LOGIN, config.PASSWORD),
        json={
            "jql": config.JQL if not ISSUE_TO_DEBUG else 'key={}'.format(ISSUE_TO_DEBUG),
            "maxResults": 300,
            "fields": ['labels', 'summary'],
            "expand": ['changelog']
        },
    )['issues']

    result = [strip_issue(i) for i in result]
    result = [convert_hours(i) for i in result]
    result = [calculate_totals(i) for i in result]
    return result

def main():
    output = ''
    issues = get_issues_time()
    result = {key: 0 for key in config.QUOTA_LABELS}
    issues_by_quota = {key: [] for key in config.QUOTA_LABELS}

    for issue in issues:
        if not len(issue['labels']):
            output += 'skip {} {}\n'.format(issue['key'].ljust(7), issue['summary'])
            continue
        issue_quota_labels = config.QUOTA_LABELS.intersection(issue['labels'])
        hours_share = issue['transitions']['_total_dev'] / len(issue_quota_labels)
        for quota in issue_quota_labels:
            result[quota] += hours_share

    total_time = sum(result.values())
    percentage = {key: round(value/total_time*100) for key, value in result.items()}

    for label in config.QUOTA_LABELS:
        for issue in issues:
            if label not in issue['labels']:
                continue
            issues_by_quota[label].append(issue)

    for quota, issues_ in issues_by_quota.items():
        output += '\n{} {}%\n'.format(quota.upper().ljust(3), percentage[quota])
        sorted_issues = sorted(issues_, key=lambda i: i['transitions']['_total_dev'], reverse=True)
        for issue in sorted_issues:
            output += '{} {} {}\n'.format(
                issue['key'].ljust(7),
                str(issue['transitions']['_total_dev']).rjust(3),
                issue['summary']
            )

    for key, value in percentage.items():
        output += '\n{} {}%'.format(key.upper().ljust(3), value)

    return output

if ISSUE_TO_DEBUG:
    get_issues_time()
else:
    print(main())
