from python_graphql_client import GraphqlClient
import feedparser
import httpx
import json
import pathlib
import re
import os
from bs4 import BeautifulSoup  # Import BeautifulSoup for HTML parsing

root = pathlib.Path(__file__).parent.resolve()
client = GraphqlClient(endpoint="https://api.github.com/graphql")

TOKEN = os.environ.get("SIMONW_TOKEN", "")

def replace_chunk(content, marker, chunk):
    r = re.compile(
        r"<!\-\- {} starts \-\->.*<!\-\- {} ends \-\->".format(marker, marker),
        re.DOTALL,
    )
    chunk = "<!-- {} starts -->\n{}\n<!-- {} ends -->".format(marker, chunk, marker)
    return r.sub(chunk, content)

# Add a function to fetch and parse the last update from the thesis website
def fetch_thesis_updates():
    response = httpx.get("https://hslima00.github.io/Tese_md/")
    soup = BeautifulSoup(response.text, 'html.parser')
    last_update = soup.find(text="Last update:").find_next().text
    return last_update

def fetch_releases(token):
    headers = {"Authorization": f"Bearer {token}"}
    query = """
    {
      repository(owner:"OWNER", name:"REPO") {
        releases(last: 5) {
          nodes {
            name
            tagName
            url
            publishedAt
          }
        }
      }
    }
    """
    data = client.execute(query=query, headers=headers)
    releases = [
        {
            "repo": "REPO",
            "release": release["name"],
            "url": release["url"],
            "published_at": release["publishedAt"]
        }
        for release in data["data"]["repository"]["releases"]["nodes"]
    ]
    return releases

if __name__ == "__main__":
    readme = root / "README.md"
    releases = fetch_releases(TOKEN)
    releases.sort(key=lambda r: r["published_at"], reverse=True)
    md = "\n".join(
        [
            "* [{repo} {release}]({url}) - {published_at}".format(**release)
            for release in releases[:5]
        ]
    )
    readme_contents = readme.open().read()
    rewritten = replace_chunk(readme_contents, "recent_releases", md)

    tils = fetch_tils()
    tils_md = "\n".join(
        [
            "* [{title}]({url}) - {created_at}".format(
                title=til["title"],
                url=til["url"],
                created_at=til["created_utc"].split("T")[0],
            )
            for til in tils
        ]
    )
    rewritten = replace_chunk(rewritten, "tils", tils_md)

    entries = fetch_blog_entries()[:5]
    entries_md = "\n".join(
        ["* [{title}]({url}) - {published}".format(**entry) for entry in entries]
    )
    rewritten = replace_chunk(rewritten, "blog", entries_md)

    # Fetch and add thesis updates
    thesis_update = fetch_thesis_updates()
    thesis_update_md = f"Last Thesis Update: {thesis_update}"
    rewritten = replace_chunk(rewritten, "thesis_update", thesis_update_md)

    readme.open("w").write(rewritten)
