import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

def fetch_github_repository(owner, repository_name):
    """Fetch public repository information without saving it."""
    owner = owner.strip()
    repository_name = repository_name.strip()

    if not owner or not repository_name:
        raise ValueError("Enter a GitHub owner and repository name.")

    encoded_owner = quote(owner, safe="")
    encoded_name = quote(repository_name, safe="")
    url = f"https://api.github.com/repos/{encoded_owner}/{encoded_name}"

    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Arc",
            "X-GitHub-Api-Version": "2026-03-10",
        },
    )

    try:
        with urlopen(request, timeout=10) as response:
            repository = json.load(response)

    except HTTPError as error:
        if error.code == 404:
            raise ValueError("Repository not found. Check the names and make sure it is public.") from error
        if error.code in (403, 429):
            raise ValueError(
                "GitHub denied the request or temporarily limited requests. "
                "Wait before trying again."
            ) from error
        raise ValueError(f"GitHub returned an error (HTTP {error.code}). Try again later.") from error

    except (TimeoutError, URLError) as error:
        raise ValueError("Could not reach GitHub. Check your connection and try again.") from error

    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("GitHub returned an unexpected response.") from error

    if not isinstance(repository, dict):
        raise ValueError("GitHub returned unexpected repository data.")

    return repository