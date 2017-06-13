import json
import os
import re

import github3
from IGitt.GitHub.GitHub import GitHub
from IGitt.GitLab.GitLab import GitLab
from errbot import BotPlugin, re_botcmd

from plugins import constants


class LabHub(BotPlugin):
    """GitHub and GitLab utilities"""  # Ignore QuotesBear

    INVITE_SUCCESS = {
        'newcomers': """
 Welcome @{}! :tada:\n\nTo get started, please follow our
 [newcomers guide](https://coala.io/newcomer). Most issues will be explained
 there and in linked pages - it will save you a lot of time, just read it.
 *Really.*\n\n*Do not take an issue if you don't understand it on your own.*
 Especially if you are new you have to be aware that getting started with an
 open source community is not trivial: you will have to work hard and most
 likely become a better coder than you are now just as we all did.\n\n
 Don't get us wrong: we are *very* glad to have you with us on this journey
 into open source! We will also be there for you at all times to help you
 with actual problems. :)
""",
        'developers': """
 Wow @{}, you are a part of developers team now! :tada: Welcome to our
 community!
""",
        'maintainers': """
 @{} you seem to be awesome! You are now a maintainer! :tada: Please go
 through https://github.com/coala/coala/wiki/Membership
"""
    }

    GH_ORG_NAME = constants.GH_ORG_NAME
    GL_ORG_NAME = constants.GL_ORG_NAME

    def activate(self):
        super().activate()
        try:
            self.IGH = GitHub(os.environ.get('GH_TOKEN'))
            self.IGL = GitLab(os.environ.get('GL_TOKEN'))

            self.gh_repos = {repo.full_name.split('/')[1]: repo for repo in
                             filter(lambda x: (x.full_name.split('/')[0] ==
                                               self.GH_ORG_NAME),
                                    self.IGH.write_repositories)}
            self.gl_repos = {repo.full_name.split('/')[1]: repo for repo in
                             filter(lambda x: (x.full_name.split('/')[0] ==
                                               self.GL_ORG_NAME),
                                    self.IGL.write_repositories)}
            self.REPOS = {**self.gh_repos, **self.gl_repos}
        except RuntimeError:
            self.log.error('Either of GH_TOKEN or GL_TOKEN is not set')

    @staticmethod
    def get_teams(token, org_name):
        """
        Invite user to team.
        :param token:    Personal access token or oauth token.
        :param org_name: Name of the organization.
        """
        gh = github3.login(token=token)
        assert gh is not None
        org = gh.organization(org_name)
        teams = dict()
        for team in org.iter_teams():
            teams[team.name] = team
        return teams

    @re_botcmd(pattern=r'(?:(?:invite)|(?:inv))\s+(\w+)\s*(?:to)\s+(\w+)')
    def invite_cmd(self, msg, match):
        """
        Invite given user to given team. By default it invites to
        "newcomers" team.
        """
        if not hasattr(self, 'TEAMS'):
            self.TEAMS = LabHub.get_teams(os.environ.get('GH_TOKEN'),
                                          self.GH_ORG_NAME)

        invitee = match.group(1)
        inviter = msg.frm.nick

        team = (self.GH_ORG_NAME + ' newcomers' if match.group(2) is None
                else match.group(2))

        self.log.info('{} invited {} to {}'.format(inviter, invitee, team))

        if self.TEAMS[self.GH_ORG_NAME + ' maintainers'].is_member(invitee):
            valid_teams = ['newcomers', 'developers', 'maintainers']
            if team.lower() not in valid_teams:
                return 'Please select from one of the ' + ', '.join(valid_teams)
            team_mapping = {
                'newcomers': self.GH_ORG_NAME + ' newcomers',
                'developers': self.GH_ORG_NAME + ' developers',
                'maintainers': self.GH_ORG_NAME + ' maintainers'
            }

            # send the invite
            self.TEAMS[team_mapping[team.lower()]].invite(invitee)
            return self.INVITE_SUCCESS[team.lower()].format(invitee)
        else:
            return ('@{}, you are not a maintainer, only maintainers can invite'
                    ' other people. Nice try :poop:'.format(inviter))

    def callback_message(self, msg):
        """Invite the user whose message includes the holy 'hello world'"""
        if not hasattr(self, 'TEAMS'):
            self.TEAMS = LabHub.get_teams(os.environ.get('GH_TOKEN'),
                                          self.GH_ORG_NAME)

        if re.search(r'hello\s*,?\s*world', msg.body, flags=re.IGNORECASE):
            user = msg.frm.nick
            if not self.TEAMS[self.GH_ORG_NAME + ' newcomers'].is_member(user):
                # send the invite
                self.send(msg.frm,
                          self.INVITE_SUCCESS['newcomers'].format(user))
                self.TEAMS[self.GH_ORG_NAME + ' newcomers'].invite(user)

    @re_botcmd(pattern=r'(?:new|file) issue ([\w-]+?)(?: |\n)(.+?)(?:$|\n((?:.|\n)*))',  # Ignore LineLengthBear, PyCodeStyleBear
               flags=re.IGNORECASE)
    def create_issut_cmd(self, msg, match):
        repo_name = match.group(1)
        iss_title = match.group(2)
        iss_description = match.group(3) if match.group(3) is not None else ''
        if repo_name in self.REPOS:
            repo = self.REPOS[repo_name]
            iss = repo.create_issue(iss_title, iss_description)
            return 'Here you go: {}'.format(iss.url)
        else:
            return 'Can\'t create an issue for a repository that does not '\
                   'exist. Please ensure that the repository is available '\
                   'and owned by coala.'

    @re_botcmd(pattern=r'unassign\s+https://(github|gitlab)\.com/([^/]+)/([^/]+)/issues/(\d+)')
    def unassign_command(self, msg, match):
        host = match.group(1)
        org = match.group(2)
        repo_name = match.group(3)
        issue_number = match.group(4)

        user = msg.frm.nick

        if host is 'github':
            iss = self.IGH.get_repo('{}/{}'.format(org, repo_name)).get_issue(int(issue_number))
        else:
            iss = self.IGL.get_repo('{}/{}'.format(org, repo_name)).get_issue(int(issue_number))

        if iss.assignee == user:
            iss.assignee = ''
        else:
