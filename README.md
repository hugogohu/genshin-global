# genshin-global

Genshin Impact global community weekly digest.

## Reddit collection

Reddit highlights are collected from public subreddit RSS feeds; no Reddit account, API application, or GitHub Actions secret is required.

Reddit can temporarily rate-limit shared GitHub Actions IP addresses. The collector retries failed requests with backoff. If every Reddit request fails, it keeps the Reddit posts from the preceding digest rather than publishing an empty section. If no previous posts exist, the workflow fails before changing the published digest.
