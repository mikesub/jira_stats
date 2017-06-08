import argparse

import jirabus

parser = argparse.ArgumentParser()
parser.add_argument('--user', action='store', required=True)
parser.add_argument('--password', action='store', required=True)
parser.add_argument('--projects', nargs='+')
args = parser.parse_args()

jira = jirabus.Jirabus(args.user, args.password, args.projects)
print(jira.main())
