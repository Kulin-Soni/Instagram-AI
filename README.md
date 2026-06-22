# Instagram AI

**(EXPERIMENTAL)** Run ai models and chat with them on Instagram.

## Features

- [x] Chat in groups and dm

- [x] Reply to messages

- [x] Fully local

- [ ] Image support (in future versions)

## Requirements

1. **NVIDIA GPU**: Any modern one should work. Highly recommended. Make sure to install drivers and toolkit.
2. **Git**: Comes pre-installed on most Linux distributions and MacOS, you need to [install on Windows](https://git-scm.com/install/windows).
3. **Docker**: This streamlines the process, instead of you having to manage everything.
4. **Python (3.10+)**: Not needed if running on docker. Download from [python.org website](https://python.org/downloads).
5. **Instagram Account**: Do **NOT** use your main account.

## Setup with Docker

> **🐳 Docker setup is highly recommended on Linux and Windows.**

1. _(Linux only)_ Install and [switch context to rootless](https://docs.docker.com/engine/security/rootless), and allow [nvidia toolkit to be accessed in rootless mode](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html#rootless-mode). This is typically pre-configured on cloud providers.

2. _(Windows only)_ You need to use [Windows Subsystem for Linux](https://learn.microsoft.com/en-us/windows/wsl/install).

3. Use [`.env.example`](./.env.example) file as a template, and fill out all the values in a `.env` file.

4. Run `start.sh` script:

    ```sh
    bash ./start.sh
    ```

## Setup without Docker

1. [Install **MongoDB Community Edition**](https://www.mongodb.com/try/download/community) and create a new cluster, get the URI, and start the cluster.

2. Replace the existing `MONGO_URI` constant in [`src/config.py`](./src/config.py):

    ```py
    MONGO_URI = "your_uri_here"
    ```

3. [Install **Ollama**](https://ollama.com), and run the [`model/download.sh`](./model/download.sh) file, it will setup everything automatically:

    ```sh
    bash ./model/download.sh
    ```

4. Replace the `OLLAMA_HOST` constant in [`src/config.py`](./src/config.py) with `http://127.0.0.1:11434` (default url of Ollama):

    ```py
    OLLAMA_HOST = "http://127.0.0.1:11434"
    ```

5. Download required libraries:

    ```sh
    pip install -r requirements.txt # with pip
    uv sync # with uv
    ```

6. Use [`.env.example`](./.env.example) file as a template, and fill out all the values in a `.env` file.

7. Run the main script:

    ```sh
    python src/main.py
    ```

## Side Notes

1. GPU support is limited on MacOS, so you will need to follow the non-docker setup to use Apple Silicon chip.

2. If you need to change the model, you can do it by going to [`model/download.sh`](./model/download.sh) and modifying the urls and names. If you change the name of the file to be downloaded, also modify it in [`model/Modelfile`](./model/Modelfile).

    [`model/download.sh`](./model/download.sh):

    ```sh
    if [ ! -f /models/model_name.gguf ]; then
    echo "Downloading 'Name here' model..."
    curl -L "https://huggingface.co/model/url.gguf" -o /models/model_name.gguf
    echo "Model 'Name here' download complete."
    fi
    ```

    [`model/Modelfile`](./model/Modelfile):

    ```txt
    FROM "/models/model_name.gguf"
    ```

3. If you need to change the system prompt, [`model/Modelfile`](./model/Modelfile) contains `SYSTEM` keyword followed by the string where you can put your new prompt. The file also contains other parameters you can tune. Here is a reference to [Modelfile guide](https://docs.ollama.com/modelfile).

    ```txt
    SYSTEM "You are an ai model."
    ```

4. I have only tested this script on linux, so if some step is missing, please let me know by creating an issue.

5. If you're getting `ChallengeError` and not able to login, enable 2FA on your account, run [`src/relogin.py`](./src/relogin.py) locally, enter the 2FA code (you will need to be quick here) and wait for `session.json` file to be generated. Now you must use this file to login next time (automatically handled in main file).

6. Claude has been used to refactor the code and make it readable, all logic was written by me.

7. I've tried to make the setup instructions as simple as possible, if you still encounter a problem, just create an issue, or you can ask ai.

## Contributions

Although this project is meant for fun, and educational purposes, if you still wanna contribute, you're always welcome! :-)

## Journey Behind The Project

<details>

<summary>Click to read</summary>

This is an experimental project that I built for fun. My friends and I were tired of Meta AI's censorship in Instagram chats where we wanted to troll each other. I took it as a challenge to build an AI system for us that has almost no censorship and would work similar to Meta AI.

Now obviously, Instagram is strict (very strict) about bots running on their platform and often bans such bot accounts very soon. I looked up the internet, and found out about aiograpi library (async version of instagrapi). It is very well maintained, and is very easy and intuitive to use, so all that was left was to piece everything together.

I experimented with the code, and eventually gained enough experience to use this library. In this process, one of my spare accounts got banned 🥲 and I had to create another one.

Instagram locked me out, and blocked my IP from logging into any accounts without browser. I brainstormed, and found an escape route, that was meant for security, but I used it for quite the opposite purpose. It was 2-Factor Authentication.

Instagram gave me access to my spare account after using 2FA code, and then I learnt that aiograpi could somewhat solve my problem. I could just save a session file and I won't have to login again and again.

Then development went smooth, I finally connected everything together, and me and my friends still use the models to have fun.

</details>

## License

This project is licensed under [MIT License](./LICENSE).
