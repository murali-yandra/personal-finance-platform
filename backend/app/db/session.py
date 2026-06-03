from collections.abc import Generator

from sqlmodel import Session, create_engine

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=settings.database_echo,
)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLModel database session."""
    with Session(engine) as session:
        yield session
