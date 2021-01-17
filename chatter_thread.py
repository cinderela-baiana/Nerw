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

    @property
    def stopped(self):
        return self._stop_event.is_set()


class ChatterThread(StoppableThread):
    def __init__(self, chatterbot):
        super().__init__()

        self.daemon = True
        self.name = "Chatter"
        self.trained = False
        self._chatbot = chatterbot
        self._usable = False

    @property
    def chat(self):
        return self._chatbot

    @chat.setter
    def chat_setter(self, _):
        raise AttributeError("A propriedade 'chat' é apenas para leitura.")

    @property
    def usable(self):
        return self._usable

    @usable.setter
    def usable_setter(self, _):
        raise AttributeError("A propriedade 'usable' é apenas para leitura.")

    def train(self):
        logger.info("Começando o treinamento do ChatBot.")

        trainer = ChatterBotCorpusTrainer(self._chatbot, show_training_progress=False)
        try:
            if not self.trained:
                trainer.train("chatterbot.corpus.portuguese")
                self.trained = True
        except Exception as e:
            logger.critical("Houve um erro durante o treinamento do bot!", exc_info=True)
            self._usable = False
            return
        else:
            self._usable = True
            logger.info("ChatBot pronto!")

    def generate_response(self, question: str):
        logger.debug("Gerando resposta para a pergunta '" + question + "'")

        awns = self.chat.generate_response(question)
        logging.debug("Resposta gerada: " + awns)

        return awns

    def run(self):
        super().run()
        if not self.trained:
            self.train()

    def stop(self):
        super().stop()

        self.trained = False
        self._chatbot = None
        self._usable = False
