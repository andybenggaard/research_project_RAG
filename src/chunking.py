from typing import List, Dict
from rapidfuzz.distance import LCSseq

def _split_paragraphs(text: str) -> List[str]:
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paras

def chunk_page(record: Dict, chunk_size: int, overlap: int) -> List[Dict]:
    paras = _split_paragraphs(record["text"])
    chunks = []
    buf, tokens = [], 0

    def count_tokens(s: str) -> int:
        # simple heuristic: ~4 chars per token
        return max(1, len(s) // 4)

    for para in paras:
        ptoks = count_tokens(para)
        if tokens + ptoks > chunk_size and buf:
            text = "\n\n".join(buf)
            chunks.append({
                "text": text,
                "page": record["page"],
                "file_name": record["file_name"],
                "source_uri": record["source_uri"],
                "section_path": "",  # could be detected by simple heading heuristics
            })
            # overlap
            ov_text = text[-(overlap*4):]
            buf = [ov_text, para]
            tokens = count_tokens(ov_text) + ptoks
        else:
            buf.append(para)
            tokens += ptoks

    if buf:
        chunks.append({
            "text": "\n\n".join(buf),
            "page": record["page"],
            "file_name": record["file_name"],
            "source_uri": record["source_uri"],
            "section_path": "",
        })
    return chunks