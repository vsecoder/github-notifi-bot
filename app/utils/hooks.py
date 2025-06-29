from github import Auth, Github
from github import GithubException


def create_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
):
    """
    Creates a webhook for the specified repository.
    This is a programmatic approach to creating webhooks with PyGithub's API. If you wish, this can be done
    manually at your repository's page on Github in the "Settings" section. There is a option there to work with
    and configure Webhooks.
    """

    config = {
        "url": f"{host}webhook/{endpoint}",
        "content_type": "json",
    }
    try:
        auth = Auth.Token(gh_token)
        g = Github(auth=auth)
    except GithubException as e:
        return {"message": "Error authenticating with Github, is your token expired? (rewrite the token)", "error": e.data}

    events = ["push", "pull_request", "issues", "fork", "star"]

    try:
        repo = g.get_repo(integration)
        repo.create_hook("web", config, events, active=True)
    except GithubException as e:
        return {"message": "Error creating webhook, please check your token rights.", "error": e.data}


def validate(token: str):
    """
    Validates the specified Github token.
    This is a programmatic approach to validating tokens with PyGithub's API. If you wish, this can be done
    manually at your profile's page on Github in the "Settings" section. There is a option there to work with
    and configure Personal Access Tokens.
    """

    if not token.startswith("ghp_"):
        return False

    try:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    except GithubException:
        return False

    try:
        g.get_repo("vsecoder/github-notifi-bot")
    except GithubException:
        return False

    # try:
    #    g.add_to_subscriptions("vsecoder/github-notifi-bot")
    # except GithubException:
    #    pass

    return True


def get_repos(token: str):
    """
    Returns a list of repositories for the specified user.
    This is a programmatic approach to getting a list of repositories with PyGithub's API. If you wish, this can be done
    manually at your repository's page on Github in the "Settings" section. There is a option there to work with
    and configure Webhooks.
    """

    try:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    except GithubException as e:
        return {"message": "Error authenticating with Github.", "error": e.data}

    try:
        repos = g.get_user().get_repos()
    except GithubException as e:
        return {"message": "Error getting repositories.", "error": e.data}

    return repos


def check_repo(token: str, repo: str):
    """
    Returns a list of repositories for the specified user.
    This is a programmatic approach to getting a list of repositories with PyGithub's API. If you wish, this can be done
    manually at your repository's page on Github in the "Settings" section. There is a option there to work with
    and configure Webhooks.
    """

    try:
        auth = Auth.Token(token)
        g = Github(auth=auth)
    except GithubException as e:
        return {"message": "Error authenticating with Github.", "error": e.data}

    try:
        repos = g.get_repo(repo)
    except GithubException as e:
        return {"message": "Error getting repositories.", "error": e.data}

    return repos
