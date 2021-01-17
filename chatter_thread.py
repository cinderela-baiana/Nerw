import threading
import logging

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement

logger = logging.getLogger(__name__)

class StoppableThread(threading.Thread):
    """Thread com o método stop().

    Copiado da resposta do StackOverflow https://stackoverflow.com/a/325528/
    """

    def __init__(self,  *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

class ChatterThread(StoppableThread):
    def __init__(self, chatterbot):
        super().__init__()

        self.daemon = True
        self.name = "Chatter"
        self.trained = False
        self._chatbot = chatterbot

    @property
    def chat(self):
        return self._chatbot

    @chat.setter
    def chat_setter(self, _):
        raise AttributeError("A propriedade 'chat' é apenas para leitura.")

    def train(self):
        logger.info("Começando o treinamento do ChatBot.")

        trainer = ChatterBotCorpusTrainer(self._chatbot)
        try:
            if not self.trained:
                trainer.train("chatterbot.corpus.portuguese")
                self.trained = True
        except Exception as e:
            logger.error("Houve um erro durante o treinamento do bot!", exc_info=True)
            return
        else:
            logger.info("ChatBot pronto!")

    def generate_response(self, question: str, then_learn=False):
        logger.debug("Gerando resposta para a pergunta '" + question + "'")

        awns = self.chat.generate_response(question)
        logging.debug("Resposta gerada: " + awns)

        if then_learn:
            correct = Statement(text=awns)
            self.chat.learn_response(correct, Statement(text=question))

        return awns

    def run(self):
        super().run()
        if not self.trained:
            self.train()


