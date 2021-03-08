# BotGamera

## Como configurar o bot
O bot precisa de pelo menos o [Python 3.8](https://www.python.org/downloads/release/python-385/) (é recomendável usar o Python 3.9)

1. Clone o repositório (`git clone https://github.com/joao-0213/BotGamera/`);
1. Instale as dependências do bot em si (Windows: `pip install -r requirements.txt`, UNIX: `pip3.8 install -r requirements.txt`);
1. Baixe o [Stockfish](https://stockfishchess.org/download/), renomeie o executável para `stockfish` (Usuários de Windows: Lembre-se de deixar o sufixo `.exe`!) e mova até a pasta `config`.

### Passos específicos para UNIX
1. Instale os seguintes pacotes usando o seu gerenciador de pacotes de preferência.

   * `cairo-devel` (`libcairo2-dev` em sistemas Debian; `cairo` em MacOS).

   * `python-dev` (ex: `python3.9-dev` para Python 3.9)

   * `ffmpeg`

   * `libffi-dev` (pode ser `libffi-devel` em alguns sistemas)

### Passos específicos para Windows

1. Instale o [UniConvertor](https://www.amazon.com/clouddrive/share/yryx2jwdJg4xJbZeIRbUco8EZR7tSUc8ttHkY62SOUz)

1. Vá na pasta raiz dele (normalmente em `%programfiles%\UniConvertor-2.0rc4`)

1. Copie todos os DLLs da pasta `dlls` até a `%SYSTEMROOT%\System32` (**não** copie a pasta `modules`)

1. Baixe o ZIP do [FFmpeg](https://ffmpeg.org/download.html) e coloque o executável `ffmpeg.exe` em seu PATH.

Pronto! Agora só rodar usando `python bot.py` no Windows, e `python3.8 bot.py` no MacOS/Linux!
