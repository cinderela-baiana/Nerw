import threading
import logging
import queue

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement
from collections import namedtuple

logger = logging.getLogger(__name__)

class Question(namedtuple("Question", ("content"))):
    def __str__(self):
        return self.content

    def __len__(self):
        return len(str(self))

    def __contains__(self, item):
        return self.content in item

class ChatterThread(threading.Thread):
    """
    Thread que cuida da parte do Chatter.
    Ver também: comando `chatbot`.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.daemon = True
        self.name = "Chatter"
        self.trained = False

        self._response = None
        self._chatbot = None
        self._usable = False
        self._count = 0
        self._stop_event = threading.Event()
        self._queue = queue.Queue(10)

    @property
    def chat(self):
        """
        Retorna um objeto `chatterbot.ChatBot`.

        Esta propriedade é apenas para leitura.
        """
        return self._chatbot

    @chat.setter
    def chat_setter(self, _):
        raise AttributeError("A propriedade 'chat' é apenas para leitura.")

    @property
    def available(self):
        """
        Se o chatter está disponível para uso.
        Normalmente isso vai retornar `True`.
        """
        return self._usable

    @available.setter
    def usable_setter(self, _):
        raise AttributeError("A propriedade 'usable' é apenas para leitura.")

    def train(self):
        """
        Treina o bot para receber perguntas. Essa função não tem efeito
        se já estiver treinado.
        """

        trainer = ChatterBotCorpusTrainer(self._chatbot, show_training_progress=False)
        try:
            if not self.trained:
                logger.info("Começando o treinamento do ChatBot.")

                trainer.train("chatterbot.corpus.portuguese")
                self.trained = True
        except Exception:
            logger.critical("Houve um erro durante o treinamento do bot!", exc_info=True)
            self._usable = False
            return
        else:
            self._usable = True
            logger.info("ChatBot pronto!")

    def generate_response(self, question: str):
        self._queue.put(Question(content=question), block=True, timeout=5.0)
        return self._response

    def _generate_response(self, question: Question):
        logger.debug("Gerando resposta para a pergunta '" + str(question) + "'")

        awns = self.chat.generate_response(Statement(text=str(question)))
        logging.debug("Resposta gerada: " + awns.text)

        self._response = awns

    def _keep_alive(self):
        try:
            question = self._queue.get(block=True)
        except (queue.Full):
            return

        return self._generate_response(question.content)

    def run(self):
        super().run()
        self._chatbot = ChatBot("Chatter")

        if not self.trained:
            self.train()

        self._keep_alive()

    def stop(self):
        self.trained = False
        self._chatbot = None
        self._usable = False
        self._stop_event.set()