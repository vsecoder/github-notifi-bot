from github import Auth, Github
from github import GithubException


def create_webhook(
    host: str,
    endpoint: str,
    gh_token: str,
    integration: str,
):
    """Creates a webhook for the specified repository.
    This is a programmatic approach to creating webhooks with PyGithub's API. If you wish, this can be done
    manually at your repository's page on Github in the "Settings" section. There is a option there to work with
    and configure Webhooks.
    """

    config = {
        "url": f"http://{host}/{endpoint}",
        "content_type": "json",
    }
    try:
        auth = Auth.Token(gh_token)
        g = Github(auth=auth)
    except GithubException as e:
        return {"message": "Error authenticating with Github.", "error": e.data}

    events = ["push"]

    try:
        repo = g.get_repo(integration)
        repo.create_hook("GitNotifiBot", config, events, active=True)
    except GithubException as e:
        return {"message": "Error creating webhook.", "error": e.data}


def validate(token: str):
    pass
