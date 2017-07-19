import unittest
import logging

from errbot.backends.test import TestBot

import plugins.answer

from tests.helper import plugin_testbot

class TestAnswer(unittest.TestCase):

    def test_answer(self):
        answer, testbot = plugin_testbot(plugins.answer.Answer, logging.ERROR)
        answer.activate()

        plugins.answer.get_answer = lambda *x, **y: []
        testbot.assertCommand('!answer something', 'Dunno')

        mock_response = ("First of all, you have to fork the repository you are "
                         "going to contribute to. This will basically give you a "
                         "clone of the repository "
                         "to your own repository. You can do this by opening this to fork the coala "
                         "repository or this to fork the coala-bears repository and then clicking ‘Fork’ "
                         "in the upper right corner.\nGit_Basics.html#getting-started-with-coala")

        plugins.answer.get_answer = lambda *x, **y: [(mock_response, 1)]

        testbot.push_message('!answer something')
        self.assertIn('You can read more here', testbot.pop_message())
        testbot.assertCommand('!answer something', '')
