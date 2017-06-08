import re
from datetime import datetime, timedelta

import requests

SP_IN_IDEAL_DAY = 5
SP_IN_IDEAL_WEEK = 4 * SP_IN_IDEAL_DAY
AVERAGE_DAYS_FOR_RC_TESTING = 3
AVERAGE_SP_IN_RELEASE = 30
REGRESSION_TESTING_FACTOR = AVERAGE_DAYS_FOR_RC_TESTING / AVERAGE_SP_IN_RELEASE
WEEKS_IN_VELOCITY_ESTIMATE = 8
SP_FOR_UNTESTED_TASKS = 1
SP_FOR_TASKS_WITHOUT_ESTIMATE = 2
DEFAULT_PROJECTS = ["MCA", "MCI"]


class Jirabus(object):
    def __init__(self, user, password, projects):
        self.user = user
        self.password = password
        self.projects = projects
        self.remove_non_alpha_regex = re.compile('[^A-Z]')
        self.velocities_dict = {}
        self.current_dates_dict = {}
        self.issues_dict = {}
        self.epics_dict = {}
        self.search_results = []
        self.bugs_ratio_dict = {}
        self.inf_ratio_dict = {}

    def get_issues_estimate(self, issues_json):
        total_sp = 0
        remaining_sp = 0
        bugs_sp = 0
        inf_sp = 0
        issues_without_estimate = []
        for issue in issues_json:
            sp = issue['fields']['customfield_10010']
            status = issue['fields']['status']['name']
            issue_type = issue['fields']['issuetype']['name']
            if sp is None:
                issues_without_estimate.append(issue['key'])
                sp = SP_FOR_TASKS_WITHOUT_ESTIMATE

            if status in ['Ready for testing', 'Testing']:
                remaining_sp += SP_FOR_UNTESTED_TASKS
            elif status not in ['Ready to RC', 'Released', 'Closed']:
                remaining_sp += sp
            total_sp += sp
            if issue_type == 'Bug':
                bugs_sp += sp
            if issue_type == 'Infrastructure task':
                inf_sp += sp
        return {'total_sp': total_sp, 'remaining_sp': remaining_sp, 'issues_without_estimate': issues_without_estimate,
                'bugs_sp': bugs_sp, 'inf_sp': inf_sp}

    def add_working_day(self, date):
        if date.weekday() == 4:
            date = date + timedelta(days=3)
        else:
            date = date + timedelta(days=1)
        return date

    def get_release_date(self, start_date, estimate):
        date = start_date
        weekday = date.weekday()
        if estimate == 0 and weekday >= 5:
            while weekday <= 6:
                date = self.add_working_day(date)
                weekday += 1
        else:
            while estimate > 0:
                estimate -= SP_IN_IDEAL_DAY
                date = self.add_working_day(date)

        return date

    def perform_search(self):
        projects_list = self.projects
        if projects_list is None:
            projects_list = DEFAULT_PROJECTS
        projects_list_str = "%2C%20".join(projects_list)
        response = requests.get(
            'https://truckerpath.atlassian.net/rest/api/2/search?jql=project%20in%20({})%20AND%20((issuetype%20%3D%20Epic%20and%20status%20!%3D%20"Released")%20OR%20("Epic%20Link"%20is%20not%20EMPTY%20and%20resolution%20is%20EMPTY)%20OR%20(status%20changed%20to%20"Ready%20to%20RC"%20during%20(-{}w%2C%20now())))'
            '&fields=customfield_10010,status,customfield_10003,customfield_10005,summary,updated,issuetype'
            '&maxResults=1000'.format(
                projects_list_str, WEEKS_IN_VELOCITY_ESTIMATE),
            auth=(self.user, self.password)
        )
        self.search_results = response.json()['issues']

    def fill_velocity_and_ratios(self):
        projects_list = self.projects
        if projects_list is None:
            projects_list = DEFAULT_PROJECTS
        for project in projects_list:
            issues_for_project = [x for x in self.search_results if
                                  x['key'].startswith(project) and x['fields']['status']['name'] in ['Ready to RC',
                                                                                                     'Released',
                                                                                                     'Closed']]
            bugs_for_project = [x for x in issues_for_project if
                                x['fields']['issuetype']['name'] == 'Bug']
            inf_for_project = [x for x in issues_for_project if
                               x['fields']['issuetype']['name'] == 'Infrastructure task']

            total_done_sp = self.get_issues_estimate(issues_for_project)['total_sp']
            total_done_bugs_sp = self.get_issues_estimate(bugs_for_project)['total_sp']
            total_done_inf_sp = self.get_issues_estimate(inf_for_project)['total_sp']
            self.velocities_dict[project] = float(total_done_sp) / float(
                SP_IN_IDEAL_WEEK * WEEKS_IN_VELOCITY_ESTIMATE)
            self.bugs_ratio_dict[project] = float(total_done_bugs_sp) / float(total_done_sp)
            self.inf_ratio_dict[project] = float(total_done_inf_sp) / float(total_done_sp)

    def fill_unreleased_epics_and_issues(self):
        self.epics_dict = {x['key']: x for x in self.search_results if x['fields']['issuetype']['name'] == 'Epic'}
        for epic in self.epics_dict.keys():
            self.issues_dict[epic] = [x for x in self.search_results if x['fields']['customfield_10003'] == epic]

    def get_testing_estimate_for_epic(self, key, issues_estimate):
        estimate = 0
        epic_status = self.epics_dict[key]['fields']['status']['name']
        if epic_status == 'To Do':
            estimate = self.get_days_for_testing(issues_estimate) * SP_IN_IDEAL_DAY
        elif epic_status == 'Testing':
            updated_date = datetime.strptime(self.epics_dict[key]['fields']['updated'],
                                             "%Y-%m-%dT%H:%M:%S.%f%z").replace(
                tzinfo=None)
            remaining_days = self.get_days_for_testing(issues_estimate) - (datetime.today() - updated_date).days
            if remaining_days > 0:
                estimate = remaining_days * SP_IN_IDEAL_DAY

        return estimate

    def get_days_for_testing(self, issues_estimate):
        return issues_estimate * REGRESSION_TESTING_FACTOR

    def get_report_for_epic(self, epic):
        output = ""
        epic_key = epic['key']
        project = self.remove_non_alpha_regex.sub('', epic_key)
        velocity_factor = self.velocities_dict.get(project)
        estimate = self.get_issues_estimate(self.issues_dict[epic_key])
        current_date = self.current_dates_dict.get(project)
        if current_date is None:
            current_date = datetime.today()

        remaining_estimate = estimate['remaining_sp'] + self.get_testing_estimate_for_epic(epic_key,
                                                                                           estimate['remaining_sp'])
        current_date = self.get_release_date(current_date, float(remaining_estimate) / float(velocity_factor))
        self.current_dates_dict[project] = current_date
        output += '{} {}\n'.format(epic['fields']['customfield_10005'], epic['fields']['summary'])
        output += 'Release date: {}\n'.format(current_date.strftime('%d/%m/%y'))
        output += "Estimate total: {}  remaining: {}\n".format(estimate['total_sp'], estimate['remaining_sp'])

        if float(estimate['total_sp']) > 0:
            bugs_ratio = float(estimate['bugs_sp']) / float(estimate['total_sp']) * 100
            inf_ratio = float(estimate['inf_sp']) / float(estimate['total_sp']) * 100
        else:
            bugs_ratio = 0
            inf_ratio = 0

        output += "Bugs: {:.2f}%   Infrastructure: {:.2f}%\n".format(bugs_ratio, inf_ratio)
        if len(estimate['issues_without_estimate']) > 0:
            output += 'Warning: tasks without estimate {}\n'.format(' '.join(estimate['issues_without_estimate']))
        output += '\n'
        return output

    def main(self):
        output = ""

        self.perform_search()
        self.fill_unreleased_epics_and_issues()
        self.fill_velocity_and_ratios()
        for value in sorted(self.epics_dict.values(), key=lambda x: x['fields']['customfield_10005']):
            output += self.get_report_for_epic(value)

        output += 'For the last 2 months:\n'
        for key in sorted(self.velocities_dict.keys()):
            output += 'Velocity factor {} = {:.2f}'.format(key, self.velocities_dict[key]) + '\n'

        for key in sorted(self.bugs_ratio_dict.keys()):
            output += 'Bugs ratio {} = {:.2f}'.format(key, self.bugs_ratio_dict[key] * 100.0) + '%\n'

        for key in sorted(self.inf_ratio_dict.keys()):
            output += 'Infrastructure ratio {} = {:.2f}'.format(key, self.inf_ratio_dict[key] * 100.0) + '%\n'

        return output
