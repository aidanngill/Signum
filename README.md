# Signum

Twitch channel point farmer programmed with async support at the forefront.

# Requirements

* Python <sup>3.10+</sup>

* Twitch account(s)

# Setup

```bash
git clone https://github.com/ramadan8/Signum.git && cd Signum
python3 -m venv venv
source venv/bin/activate
python3 -m pip install requirements.txt
```

Once you've installed the requirements, you can then create your cookie files and configure how the application runs.

## Cookies

Install [`cookies.txt`](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/) for Firefox or [`EditThisCookie`](https://www.editthiscookie.com/) for Chrome. From here, you will be able to export your cookies to the Netscape/Mozilla format. In the future I would like to improve this method somewhat, possibly signing the user in on the application itself and pickling the cookies there.

## Configuration

```bash
python3 -m signum --cookies cookie-*.txt --channels shroud xQcOW
```

This would load all files with the format `cookie-*.txt`, e.g. "cookie-user1.txt", and starts watching [shroud](https://twitch.tv/shroud) and [xQcOW](https://twitch.tv/xQcOW).
