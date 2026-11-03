import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import urlopen

def fetch_codewars_profile(username):
    """Fetch a public Codewars profile without saving it."""
    username = username.strip()

    if not username:
        raise ValueError("Enter a Codewars username.")

    encoded_username = quote(username, safe="")
    url = f"https://www.codewars.com/api/v1/users/{encoded_username}"

    try:
        with urlopen(url, timeout=10) as response:
            profile = json.load(response)
    except HTTPError as error:
        if error.code == 404:
            raise ValueError("Codewars user not found.") from error
        if error.code == 429:
            raise ValueError(
                "Codewars request limit reached. Try again later."
            ) from error
        raise ValueError(
            f"Codewars returned an error (HTTP {error.code}). Try again later."
        ) from error
    except (TimeoutError, URLError) as error:
        raise ValueError(
            "Could not reach Codewars. Check your connection and try again."
        ) from error
    except(json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Codewars returned an upexpected response.")

    if not isinstance(profile, dict):
        raise ValueError("Codewars returned aan unexpected respone.")
    
    return profile