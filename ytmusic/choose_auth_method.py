import inquirer
from logger import FileLogger
from pathlib import Path

logger = FileLogger(str(Path("ytmusic") / "ytmusic.log"))


def choose_auth_method() -> str:
    """Let user choose between OAuth and browser cookie authentication"""
    questions = [
        inquirer.List(
            "auth_method",
            message="Choose YouTube Music authentication method",
            choices=[
                ("OAuth (recommended)", "oauth"),
                ("Browser Cookies", "browser"),
            ],
            carousel=True,
        )
    ]
    answers = inquirer.prompt(questions)
    if not answers:  # User pressed Ctrl+C
        raise KeyboardInterrupt("Authentication method selection cancelled")
    return answers["auth_method"]
