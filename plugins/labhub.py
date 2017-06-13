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

    @classmethod
    def get_teams(cls, token, org_name):
        """
        Invite user to team.
        :param token:    Personal access token or oauth token.
        :param org_name: Name of the organization.
        """
        cls.GH = github3.login(token=token)
        assert cls.GH is not None
        cls.GH_ORG = cls.GH.organization(org_name)
        teams = dict()
        for team in cls.GH_ORG.iter_teams():
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

    @re_botcmd(pattern=r'unassign\s+https://(github|gitlab)\.com/([^/]+)/([^/]+)/issues/(\d+)', # Ignore LineLengthBear, PyCodeStyleBear
               flags=re.IGNORECASE)
    def unassign_cmd(self, msg, match):
        org = match.group(2)
        repo_name = match.group(3)
        issue_number = match.group(4)

        user = msg.frm.nick

        try:
            assert org == GH_ORG_NAME or org == GL_ORG_NAME
        except AssertionError:
            return 'Repository not owned by our org.'

        if host is 'github':
            iss = self.IGH.get_repo(
                '{}/{}'.format(org, repo_name)).get_issue(int(issue_number))
        else:
            iss = self.IGL.get_repo(
                '{}/{}'.format(org, repo_name)).get_issue(int(issue_number))

        try:
            iss = self.REPOS[repo_name].get_issue(int(issue_number))
            if user in iss.assignees:
                iss.unassign(user)
                return '@{}, you are unassigned now :+1:'.format(user)
            else:
                return 'You are not an assignee on the issue.'
        except KeyError:
            return 'Repository doesn\'t exist.'

    @re_botcmd(pattern=r'assign\s+https://(github|gitlab)\.com/([^/]+)/([^/]+)/issues/(\d+)',  # Ignore LineLengthBear, PyCodeStyleBear
               flags=re.IGNORECASE)
    def assign_cmd(self, msg, match):
        org = match.group(2)
        repo_name = match.group(3)
        iss_number = match.group(4)

        try:
            assert org == GH_ORG_NAME or org == GL_ORG_NAME
        except AssertionError:
            return 'Repository not owned by our org.'

        checks = [
            # newcomer asking for assigning issues with difficulty level other
            # than low and newcomer
            lambda user, iss: (bool(filter(lambda x: ('low' in x) or
                                                    ('newcomer' in x),
                                          filter(lambda x:
                                                        'difficulty' in x,
                                                     iss.labels)))
                               if self.TEAMS[self.GH_ORG_NAME +
                                             ' newcomers'].is_member(user)
                               else False)
        ]

        def eligible(user, iss):
            for chk in checks:
                if chk(user, iss):
                    return False
            return True

        eligility_conditions = [
            '- A newcomer cannot be assigned to an issue with a difficulty '\
            'level higher then newcomer or low difficulty.',
        ]

        try:
            iss = self.REPOS[repo_name].get_issue(int(iss_number))

            if not iss.assignee:
                if elligible(user, iss):
                    iss.assign(user)
                    return 'Congratulations! You\'ve been assigned to the '\
                           'issue. :tada:'
                else:
                    yield 'You are not eligible to be assigned to this issue.'
                    yield '\n'.join(eligility_conditions)
            else:
                return 'The issue is already assigned to someone. Please '\
                       'check if the assignee is still working on the issue, '\
                       'if not, you should ask for reassignment.'
        except KeyError:
            return 'Repository doesn\'t exist.'
