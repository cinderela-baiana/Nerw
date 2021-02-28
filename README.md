# BotGamera

## Como configurar o bot
O bot precisa de pelo menos o [Python 3.8](https://www.python.org/downloads/release/python-385/)

1. Clone o repositório (`git clone https://github.com/joao-0213/BotGamera/`);
1. Instale as dependências do bot em si (Windows: `pip install -r requirements.txt`, UNIX: `pip3.8 install -r requirements.txt`);

### Passos específicos para UNIX
1. Instale o pacote do [Cairo](https://www.cairographics.org/).

  * Derivados do Debian (Ubuntu, Linux Mint e etc...)
    ```sh
    sudo apt-get install libcairo2-dev
    ```
    
  * Fedora
    ```sh
    sudo yum install cairo-devel
    ```
    
  * OpenSUSE
    ```sh
    zypper install cairo-devel
    ```
    
  * MacOS
    ```sh
    sudo port install cairo
    ```

  * Outras distribuições
  
    Te vira kkkkk   
  
### Passos específicos para Windows

1. Instale o [UniConvertor](https://www.amazon.com/clouddrive/share/yryx2jwdJg4xJbZeIRbUco8EZR7tSUc8ttHkY62SOUz)

1. Vá na pasta raiz dele (normalmente em `%programfiles%\UniConvertor-2.0rc4`)

1. Copie todos os DLLs da pasta `dlls` até a `%SYSTEMROOT%\System32` (**não** copie a pasta `modules`)

Pronto! Agora só rodar usando `python bot.py` no Windows, e `python3.8 bot.py` no MacOS/Linux!
