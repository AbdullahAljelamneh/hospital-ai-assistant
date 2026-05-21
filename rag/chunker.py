"""Chunk documents into overlapping segments for embedding."""

import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    section: str
    chunk_id: str


def chunk_markdown(
    text: str, source: str, chunk_size: int = 500, overlap: int = 50
) -> list[Chunk]:
    """Split a markdown document into chunks, respecting section boundaries."""

    sections = re.split(r"\n(?=#{1,3}\s)", text)

    chunks = []
    chunk_idx = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        heading_match = re.match(r"^(#{1,3})\s+(.+)", section)
        heading = heading_match.group(2) if heading_match else "General"

        words = section.split()
        if len(words) <= chunk_size:
            chunks.append(
                Chunk(
                    text=section,
                    source=source,
                    section=heading,
                    chunk_id=f"{source}_{chunk_idx}",
                )
            )
            chunk_idx += 1
        else:
            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_text = " ".join(words[start:end])

                if start > 0:
                    chunk_text = f"## {heading}\n{chunk_text}"

                chunks.append(
                    Chunk(
                        text=chunk_text,
                        source=source,
                        section=heading,
                        chunk_id=f"{source}_{chunk_idx}",
                    )
                )
                chunk_idx += 1
                start += chunk_size - overlap

    return chunks
