def commit_message(res):
    modified = "\n".join([file for file in res["head_commit"]["modified"]])
    return f"""<b>📏 On <a href="{res["repository"]["html_url"]}">{res["repository"]["full_name"]}</a> new commit!</b>
<i>{res["head_commit"]["message"]}</i>
<a href="{res["compare"]}">#{res["head_commit"]["id"][:7]}</a> by <i>{res["head_commit"]["author"]["name"]} (<a href="{res["sender"]["html_url"]}">@{res["head_commit"]["author"]["username"]}</a>)</i>

<b>🖊 Modified files:</b>
<code>{modified}</code>
    """


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
