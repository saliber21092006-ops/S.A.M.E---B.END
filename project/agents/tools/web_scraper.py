import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


def scrape_url(url: str, max_chars: int = 4000) -> str:
    """Fetches a webpage and extracts clean, readable text."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove non-content elements like scripts, styles, and navigation
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()

        # Extract and clean whitespace
        lines = (line.strip() for line in soup.get_text(separator="\n").splitlines())
        clean_text = "\n".join(line for line in lines if line)

        return clean_text[:max_chars]
    except Exception as e:
        return f"Error scraping {url}: {str(e)}"


def search_and_scrape(query: str, num_results: int = 3, max_chars_per_page: int = 3000) -> str:
    """
    Searches the web for a query, scrapes the top results, 
    and returns formatted context for an AI agent.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
    except Exception as e:
        return f"Search failed: {str(e)}"

    if not results:
        return "No search results found."

    compiled_output = []
    for idx, res in enumerate(results, 1):
        title = res.get("title", "No Title")
        url = res.get("href", "")
        snippet = res.get("body", "")

        page_content = scrape_url(url, max_chars=max_chars_per_page)

        compiled_output.append(
            f"--- RESULT {idx} ---\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Snippet: {snippet}\n"
            f"Extracted Content:\n{page_content}\n"
        )

    return "\n".join(compiled_output)


# Example usage
if __name__ == "__main__":
    agent_context = search_and_scrape("latest open source LLM releases", num_results=2)
    print(agent_context)
