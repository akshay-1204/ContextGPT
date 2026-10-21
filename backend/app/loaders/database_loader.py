"""Authorized read-only database query loader for PostgreSQL and SQLite using LangChain Community."""

import re
from typing import Dict, Any, Tuple
from sqlalchemy import create_engine, text

from backend.app.loaders.base import BaseSourceLoader, LoaderError


class DatabaseLoader(BaseSourceLoader):
    """
    Executes an authorized read-only SQL SELECT query against a specified PostgreSQL database
    (or SQLite for local development) using LangChain Community SQL utilities.
    """

    DISALLOWED_KEYWORDS = {
        "insert", "update", "delete", "drop", "alter", "truncate", "create",
        "grant", "revoke", "replace", "vacuum", "exec", "execute", "call"
    }

    def _validate_sql_query(self, query: str) -> None:
        clean_query = query.strip().rstrip(";")
        if not clean_query.lower().startswith("select"):
            raise LoaderError("Security restriction: Only SELECT queries are permitted for database sources.")

        # Check for disallowed mutation keywords using regex word boundary
        tokens = set(re.findall(r"\b[A-Za-z_]+\b", clean_query.lower()))
        matched_disallowed = tokens.intersection(self.DISALLOWED_KEYWORDS)
        if matched_disallowed:
            raise LoaderError(
                f"Security restriction: Disallowed SQL operations detected: {', '.join(sorted(matched_disallowed))}."
            )

    def extract(self, source_reference: str, metadata: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        metadata = dict(metadata or {})
        connection_uri = source_reference.strip()
        query = metadata.get("query", "").strip()

        if not query:
            raise LoaderError("SQL query is required to extract database source content.")

        self._validate_sql_query(query)

        # Restrict dialect strictly to PostgreSQL (and SQLite for local dev/testing). MySQL is explicitly disallowed.
        allowed_dialects = ("postgresql", "postgres", "sqlite")
        if not any(connection_uri.lower().startswith(proto) for proto in allowed_dialects):
            raise LoaderError(
                "Security restriction: Only PostgreSQL (postgresql://) and SQLite (sqlite://) are supported. MySQL is not permitted."
            )

        try:
            # Leverage LangChain Community SQLDatabase utility when available
            try:
                from langchain_community.utilities.sql_database import SQLDatabase
                db_wrapper = SQLDatabase.from_uri(connection_uri)
                # Execute query via SQLDatabase wrapper
                raw_result = db_wrapper.run(query)
                table_info = db_wrapper.get_table_info()
            except Exception:
                db_wrapper = None
                raw_result = None
                table_info = None

            # Fallback / precise structured fetch with SQLAlchemy engine
            engine = create_engine(connection_uri, connect_args={"connect_timeout": 5} if "sqlite" not in connection_uri else {})
            with engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                keys = list(result.keys())

                if not rows:
                    raise LoaderError("Query executed successfully, but returned 0 rows.")

                # Format as structured Markdown table
                header = "| " + " | ".join(keys) + " |"
                separator = "| " + " | ".join(["---"] * len(keys)) + " |"
                formatted_rows = [header, separator]

                max_rows = 500  # Cap maximum rows for LLM context bounds
                for row in rows[:max_rows]:
                    formatted_rows.append("| " + " | ".join(str(val) for val in row) + " |")

                if len(rows) > max_rows:
                    formatted_rows.append(f"\n*(Note: Output truncated to first {max_rows} rows out of {len(rows)})*")

                extracted_text = "\n".join(formatted_rows)
                if table_info:
                    extracted_text = f"### Schema Information (from LangChain Community SQLDatabase):\n{table_info}\n\n### Query Results:\n{extracted_text}"

        except LoaderError:
            raise
        except Exception as e:
            # Mask potential credentials from exception messages
            clean_err = re.sub(r"://[^@]+@", "://***:***@", str(e))
            raise LoaderError(f"PostgreSQL query execution failed: {clean_err}")

        # Mask connection URI for metadata storage
        masked_uri = re.sub(r"://[^@]+@", "://***:***@", connection_uri)
        metadata.update({
            "connection_uri": masked_uri,
            "query": query,
            "dialect": "postgresql" if "postgres" in connection_uri.lower() else "sqlite",
            "row_count": len(rows),
            "column_count": len(keys),
            "columns": keys,
        })

        return extracted_text, metadata
