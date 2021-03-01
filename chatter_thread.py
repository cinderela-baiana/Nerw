import threading
import logging
import queue

from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer
from chatterbot.conversation import Statement
from collections import namedtuple
from typing import *

logger = logging.getLogger(__name__)

class Question(namedtuple("Question", ("content"))):
    def __str__(self):
        return self.content

    def __len__(self):
        return len(str(self))

    def __contains__(self, item):
        return self.content in item

LearnResponseRequest = namedtuple("LearnResponseRequest", ("question", "statement"))


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
        self._chatbot: Optional[ChatBot] = None
        self._usable = False
        self._count = 0
        self._queue = queue.Queue(10)
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._train_error = None

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
    def train_exception(self):
        return self._train_error

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
        except Exception as err:
            logger.critical("Houve um erro durante o treinamento do bot!", exc_info=True)
            self.train_exception = err
            self._usable = False
            return
        else:
            self._usable = True
            logger.info("ChatBot pronto!")

    def generate_response(self, question: str):
        self._queue.put(Question(content=question), block=True, timeout=5.0)
        return self._get_request()

    def _generate_response(self, question: Question):
        with self._lock:
            logger.debug("Gerando resposta para a pergunta '" + str(question) + "'")

            awns = self.chat.generate_response(Statement(text=str(question)))
            logging.debug("Resposta gerada: " + awns.text)
            print("_genrsp: " + str(self._response))
        return awns

    def _get_request(self):
        question = self._queue.get(block=True)
        if isinstance(question, Question):
            return self._generate_response(question.content)
        elif isinstance(question, LearnResponseRequest):
            self._learn_response(question)

    def _learn_response(self, learn: LearnResponseRequest) -> None:
        correct_response, question = learn.statement, learn.question
        if isinstance(correct_response, str):
            correct_response = Statement(text=correct_response)
        if isinstance(question, str):
            question = Statement(text=question)

        with self._lock:
            self._chatbot.learn_response(correct_response, question)
        return learn

    def learn_response(self, correct_response: Union[Statement, str], question: Union[Statement, str]) -> None:
        self._queue.put(LearnResponseRequest(question, correct_response), block=True, timeout=5.0)
        self._get_request()

    def run(self):
        super().run()
        self._chatbot = ChatBot("Chatter")

        if not self.trained:
            self.train()

    def close(self):
        self._queue.join()
        self.trained = False
        self._chatbot = None
        self._usable = False
        self._event.set()
