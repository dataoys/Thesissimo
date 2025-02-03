from .Whoosh import search_documents, create_or_get_index
from .Postgres import search


__all__ = ['search_documents', 'create_or_get_index', search]