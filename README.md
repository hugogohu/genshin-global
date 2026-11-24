# genshin-global

Genshin Impact global community weekly digest.

## Reddit setup

Reddit content is fetched through the official OAuth API. Anonymous RSS is intentionally not used because it is rate-limited on GitHub Actions.

1. While logged in to Reddit, open [app preferences](https://www.reddit.com/prefs/apps) and create a **script** app.
2. In this repository, open **Settings → Secrets and variables → Actions** and add:

   | Secret | Value |
   | --- | --- |
   | `REDDIT_CLIENT_ID` | App ID shown under the script app name |
   | `REDDIT_CLIENT_SECRET` | App secret |
   | `REDDIT_USERNAME` | Reddit account username |
   | `REDDIT_PASSWORD` | Reddit account password |

3. Run **Actions → Weekly Digest → Run workflow** to verify the configuration.

The workflow fails without overwriting `docs/data.json` when Reddit authentication or data retrieval fails. This keeps the last known-good Reddit section published instead of replacing it with an empty result.
