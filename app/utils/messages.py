def parse_diff(diff_text):
    added_lines = 0
    removed_lines = 0

    diff_lines = diff_text.splitlines()
    for line in diff_lines:
        if line.startswith('+') and not line.startswith('+++'):
            added_lines += 1
        elif line.startswith('-') and not line.startswith('---'):
            removed_lines += 1

    return added_lines, removed_lines


def commit_message(res):
    modified = "\n".join([file for file in res["head_commit"]["modified"]])
    created = "\n".join([file for file in res["head_commit"]["added"]])
    removed = "\n".join([file for file in res["head_commit"]["removed"]])

    #route = f"https://github.com/{res["repository"]["full_name"]}/commit/{res["head_commit"]["id"]}.patch/"
    #diff = requests.get(route).text
    #added_lines, removed_lines = parse_diff(diff)

    message = f"""<b>📏 On <a href="{res["repository"]["html_url"]}">{res["repository"]["full_name"]}:{res["ref"].split("/")[-1]}</a> new commit!</b>
<i>{res["head_commit"]["message"]}</i>
<a href="{res["compare"]}">#{res["head_commit"]["id"][:7]}</a> by <i>{res["head_commit"]["author"]["name"]} (<a href="{res["sender"]["html_url"]}">@{res["head_commit"]["author"]["username"]}</a>)</i>

"""

    if created:
        message += f"""<b>➕ Created files:</b>
<code>{created}</code>
"""
    if removed:
        message += f"""<b>🗑 Removed files:</b>
<code>{removed}</code>
"""

    if modified:
        message += f"""<b>🖊 Modified files:</b>
<code>{modified}</code>
"""

#    if added_lines or removed_lines:
#        message += f"""<a href="https://diff2html.xyz/demo?diff={route}">Diff:</a>
#+ {added_lines}
#- {removed_lines}
#"""

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
    return f"""<b>📝 On <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> {res["action"]} pull request!</b>

<i>{res["pull_request"]["title"]}</i>

"""


def create_message(res):
    return f"""<b>🖇 On <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> created a {res["ref_type"]} {res["ref"]}</b>"""


def fork_message(res):
    return f"""<b>🍴 <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> forked</b>

<i>Total forks count is now:</i> <code>{res["repository"]["forks"]}</code>
<i>Fork link:</i> <a href={res["forkee"]["html_url"]}">{res["forkee"]["full_name"]}</a>
"""
