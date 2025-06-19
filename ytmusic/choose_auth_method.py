import inquirer


def choose_auth_method() -> str:
    """
    Let the user choose between OAuth and browser cookie authentication.

    Returns:
        str: The chosen authentication method ("oauth" or "browser").

    Raises:
        KeyboardInterrupt: If user cancels the selection process.

    Notes:
        - OAuth is recommended for better reliability and security.
        - Browser authentication uses saved cookies from a browser session.
    """
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
