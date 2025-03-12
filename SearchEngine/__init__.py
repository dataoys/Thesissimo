from .Whoosh import search_documents, create_or_get_index
from .Postgres import search
from .Pylucene import search_documents, create_index


__all__ = ['search_documents', 'create_or_get_index', 'search', 'search_documents', 'create_index']