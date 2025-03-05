from github import Auth, Github


def commit_message(res, user_token):
    # Аутентификация через PyGithub
    auth = Auth.Token(user_token)
    g = Github(auth=auth)

    # Получаем репозиторий
    repo = g.get_repo(res["repository"]["full_name"])

    # Собираем информацию о всех коммитах
    commits_info = []
    for commit_data in res["commits"]:
        # Получаем объект коммита
        commit = repo.get_commit(commit_data["id"])

        # Получаем diff для коммита
        diff = commit.files  # Список измененных файлов
        modified_files = [file.filename for file in diff if file.status == "modified"]
        created_files = [file.filename for file in diff if file.status == "added"]
        removed_files = [file.filename for file in diff if file.status == "removed"]

        modified = "\n".join(modified_files)
        created = "\n".join(created_files)
        removed = "\n".join(removed_files)

        # Получаем общее количество добавленных и удаленных строк
        added_lines, removed_lines = 0, 0
        for file in diff:
            added_lines += file.additions
            removed_lines += file.deletions

        commit_message = f"""<b>Commit <a href="{commit_data["url"]}">#{commit_data["id"][:7]}</a> by <i>{commit_data["author"]["name"]} (<a href="https://github.com/{commit_data["author"]["username"]}">@{commit_data["author"]["username"]}</a>)</i></b>
<i>{commit_data["message"]}</i>
"""

        if created:
            commit_message += f"""<b>➕ Created files:</b>
<code>{created}</code>
"""
        if removed:
            commit_message += f"""<b>🗑 Removed files:</b>
<code>{removed}</code>
"""
        if modified:
            commit_message += f"""<b>🖊 Modified files:</b>
<code>{modified}</code>
"""

        if added_lines or removed_lines:
            commit_message += f"""<b>⌨️ Diff:</b>
+ {added_lines} lines added
- {removed_lines} lines removed
"""

        commits_info.append(commit_message)

    # Объединяем информацию о всех коммитах
    message = f"""<b>📏 On <a href="{res["repository"]["html_url"]}">{res["repository"]["full_name"]}:{res["ref"].split("/")[-1]}</a> new commits!</b>
{len(res["commits"])} commits pushed.
<a href="{res["compare"]}">Compare changes</a>

"""

    message += "\n".join(commits_info)

    return message


def issue_message(res):
    return f"""<b>📌 On <a href="{res['issue']['url']}">{res["repository"]["full_name"]}</a> {res["action"]} issue!</b>

<i>{res["issue"]["title"]}</i>
<a href="{res["issue"]["html_url"]}">#{res["issue"]["number"]}</a> by <a href="{res["sender"]["html_url"]}"><i>@{res["issue"]["user"]["login"]}</i></a>
    """


def star_message(res):
    return f"""<b>⭐️ On <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> {"added" if res["action"] == "created" else "removed"} star!</b>

Total stars: <i>{res["repository"]["stargazers_count"]}</i>
User: <a href="{res["sender"]["html_url"]}"><i>@{res["sender"]["login"]}</i></a>
    """


def ping_message(res):
    return f"""🏓 Repo {res["repository"]["full_name"]} connected and sending ping!"""


def pull_request_message(res):
    body = res["pull_request"]["body"] if res["pull_request"]["body"] else "No description"

    if len(body) > 200:
        body = body[:200] + "..."

    return f"""<b>📝 On <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> {res["action"]} pull request!</b>

<i>{res["pull_request"]["title"]}</i>
<blockquote expandable="expandable">{body}</blockquote>

User: <a href="{res["sender"]["html_url"]}"><i>@{res["pull_request"]["user"]["login"]}</i></a>

<a href="{res["pull_request"]["html_url"]}">#{res["pull_request"]["number"]}</a>
"""


def create_message(res):
    return f"""<b>🖇 On <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> created a {res["ref_type"]} {res["ref"]}</b>"""


def fork_message(res):
    return f"""<b>🍴 <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> forked</b>

<i>Total forks count is now:</i> <code>{res["repository"]["forks"]}</code>
<i>Fork link:</i> <a href={res["forkee"]["html_url"]}">{res["forkee"]["full_name"]}</a>
"""
