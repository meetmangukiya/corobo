from errbot import BotPlugin, botcmd

from gensim.summarization import summarize

from answers.final import get_answer, graph


class Answer(BotPlugin):

    @botcmd
    def answer(self, msg, arg):
        answers = list(get_answer(arg, graph, final=True))
        if answers:
            yield summarize(answers[0][0])
            # Ignore InvalidLinkBear
            doc_link = 'https://api.coala.io/en/latest/Developers/' + \
                answers[0][0].splitlines()[-1]
            yield 'You can read more here: {}'.format(doc_link)
        else:
            yield 'Dunno'
