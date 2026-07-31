from enum import Enum


class PaperStatus(str, Enum):
    uploaded = "uploaded"
    parsed = "parsed"
    indexed = "indexed"
    extracted = "extracted"


VALID_STATUS_TRANSITIONS = {
    PaperStatus.uploaded.value: [PaperStatus.parsed.value],
    PaperStatus.parsed.value: [PaperStatus.indexed.value],
    PaperStatus.indexed.value: [PaperStatus.extracted.value],
    PaperStatus.extracted.value: []
}