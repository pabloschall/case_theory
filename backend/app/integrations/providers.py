from typing import Protocol, TypeVar

SourceCase = TypeVar("SourceCase")
NormalizedCase = TypeVar("NormalizedCase", covariant=True)


class CaseSourceProvider(Protocol[SourceCase, NormalizedCase]):
    async def search(self, query: str, page: int = 1) -> object: ...

    async def get_case(self, external_id: str) -> SourceCase: ...

    def normalize(self, source_case: SourceCase) -> NormalizedCase: ...
