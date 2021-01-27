import threading
import logging
from concurrent.futures import wait

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
    """
    Thread que cuida da parte do Chatter.

    Ver também: comando `chatbot`.
    """
    def __init__(self):
        super().__init__()

        self.daemon = True
        self._chatbot = ChatBot("Chatter")
        self.name = "Chatter"
        self.trained = False
        self._usable = False

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


        logger.info("Começando o treinamento do ChatBot.")

        trainer = ChatterBotCorpusTrainer(self._chatbot, show_training_progress=False)
        try:
            if not self.trained:
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
        """
        Gera uma resposta para a pergunta `question`.
        """
        

        logger.debug("Gerando resposta para a pergunta '" + question + "'")

        awns = self.chat.generate_response(Statement(text=question))
        logging.debug("Resposta gerada: " + awns.text)

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
