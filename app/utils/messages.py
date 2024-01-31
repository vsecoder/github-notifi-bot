def commit_message(res):
    modified = "\n".join([file for file in res["head_commit"]["modified"]])
    return f"""<b>📏 {res["repository"]["full_name"]} new commit!</b>
<i>{res["head_commit"]["message"]}</i>
<a href="{res["compare"]}">#{res["head_commit"]["id"][:7]}</a> by <i>{res["head_commit"]["author"]["name"]} (@{res["head_commit"]["author"]["username"]})</i>

<b>🖊 Modified files:</b>
<code>{modified}</code>
    """


def issues_message(res):
    return f"""<b>📌 <a href="{res['issue']['url']}">{res["repository"]["full_name"]}</a> {res["action"]} issue!</b>

<i>{res["issue"]["title"]}</i>
<a href="{res["issue"]["html_url"]}">#{res["issue"]["number"]}</a> by <i>@{res["issue"]["user"]["login"]}</i>
    """


def star_message(res):
    return f"""<b>⭐️ <a href="{res['repository']['html_url']}">{res["repository"]["full_name"]}</a> starred!</b>

Total stars: <i>{res["repository"]["stargazers_count"]}</i>
    """
