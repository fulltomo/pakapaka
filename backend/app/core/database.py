from sqlalchemy import create_engine
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


def init_db(bind_engine=None):
    """Initialize database tables and create the default forward trading wallet session."""
    target_engine = bind_engine or engine
    Base.metadata.create_all(bind=target_engine)

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
