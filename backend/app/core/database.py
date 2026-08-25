from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.models.schema import Base, WalletSession

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency for obtaining a database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema(bind_engine=None):
    """
    Adds columns present on the models but missing from an existing database.

    SQLite cannot ALTER a table to add a NOT NULL column without a default, so only
    nullable additions are supported — which is what every new column here is.
    Idempotent: returns the list of columns it actually added.
    """
    target_engine = bind_engine or engine
    insp = inspect(target_engine)
    added = []
    with target_engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing:
                    continue
                col_type = col.type.compile(target_engine.dialect)
                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"))
                added.append(f"{table.name}.{col.name}")
    return added


def init_db(bind_engine=None):
    """Initialize database tables and create the default forward trading wallet session."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)
    ensure_schema(target_engine)

    Session = sessionmaker(bind=target_engine)
    session = Session()
    try:
        default_wallet = session.query(WalletSession).filter_by(
            session_id=settings.DEFAULT_FORWARD_SESSION_ID
        ).first()
        if not default_wallet:
            default_wallet = WalletSession(
                session_id=settings.DEFAULT_FORWARD_SESSION_ID,
                initial_points=settings.DEFAULT_WALLET_INITIAL_POINTS,
                current_points=settings.DEFAULT_WALLET_INITIAL_POINTS,
                total_invested=0,
                total_returned=0,
                total_bets=0,
                won_bets=0,
                max_drawdown=0.0,
            )
            session.add(default_wallet)
            session.commit()
    finally:
        session.close()
