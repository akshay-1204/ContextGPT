"""Stock market time-series API loader using standard LangChain BaseLoader and Document."""

from typing import Dict, Any, Tuple, List
import requests
from langchain_community.document_loaders.base import BaseLoader
from langchain_core.documents import Document

from backend.app.loaders.base import LoaderError


class StockAPILoader(BaseLoader):
    """
    Custom LangChain document loader for Alpha Vantage Daily Stock Time Series.
    Follows clean, standard LangChain patterns without complex decorators.
    """

    def __init__(self, symbol: str, api_key: str):
        self.symbol = symbol.strip().upper()
        self.api_key = api_key.strip()
        self.url = (
            f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
            f"&symbol={self.symbol}&apikey={self.api_key}&outputsize=compact"
        )

    def load(self) -> List[Document]:
        """Fetch stock market time-series and return as a list of LangChain Document objects."""
        try:
            response = requests.get(self.url, timeout=12)
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            raise LoaderError(f"Failed to fetch stock data for {self.symbol}: {str(e)}")

        time_series = data.get("Time Series (Daily)")
        if not time_series:
            # Check for error or note messages from Alpha Vantage
            err_msg = data.get("Error Message") or data.get("Note") or "No daily stock data found in API response."
            raise LoaderError(f"Alpha Vantage API: {err_msg}")

        documents = []
        for date, values in time_series.items():
            content = (
                f"Symbol: {self.symbol}\n"
                f"Date: {date}\n"
                f"Open: {values.get('1. open')}\n"
                f"High: {values.get('2. high')}\n"
                f"Low: {values.get('3. low')}\n"
                f"Close: {values.get('4. close')}\n"
                f"Volume: {values.get('5. volume')}"
            )
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "symbol": self.symbol,
                        "date": date,
                        "source": "Alpha Vantage",
                    },
                )
            )

        return documents

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """Convenience method for ContextGPT integration."""
        docs = self.load()
        full_text = "\n\n".join(d.page_content for d in docs)
        return full_text, {
            "symbol": self.symbol,
            "data_points_count": len(docs),
            "char_count": len(full_text),
            "loader": "StockAPILoader",
        }
