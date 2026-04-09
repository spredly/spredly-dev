import datetime
import enum
from typing import Annotated

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db.base import Base, str_64, str_128

intpk = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
created_at = Annotated[
    datetime.datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))
]
updated_at = Annotated[
    datetime.datetime,
    mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=datetime.datetime.utcnow,
    ),
]


class MatchResultEnum(enum.Enum):
    win = "win"
    lose = "lose"


class MatchSideEnum(enum.Enum):
    home = "home"
    away = "away"


class Sport(Base):
    __tablename__ = "sport"

    id: Mapped[intpk] = mapped_column(autoincrement=False)
    name: Mapped[str_64] = mapped_column(unique=True, nullable=False)


class League(Base):
    __tablename__ = "league"

    id: Mapped[intpk] = mapped_column(autoincrement=False)
    sport_id: Mapped[int] = mapped_column(ForeignKey("sport.id"), nullable=False)
    name: Mapped[str_128] = mapped_column(nullable=False)
    _table_args__ = (
        UniqueConstraint("name", "sport_id", name="uq_league_combination"),
    )


class Match(Base):
    __tablename__ = "match"

    id: Mapped[intpk] = mapped_column(autoincrement=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("match.id"), nullable=True, index=True
    )
    league_id: Mapped[int] = mapped_column(ForeignKey("league.id"), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[created_at]

    members: Mapped[list["MatchMember"]] = relationship(
        "MatchMember", back_populates="match", cascade="all, delete-orphan"
    )

    parent: Mapped["Match | None"] = relationship(
        "Match", remote_side=[id], back_populates="children"
    )

    status_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    status_name: Mapped[str] = mapped_column(nullable=False, default="unknown", index=True)

    total_home_score: Mapped[int | None] = mapped_column(nullable=True)
    total_away_score: Mapped[int | None] = mapped_column(nullable=True)

    winning_team: Mapped[str | None] = mapped_column(nullable=True)

    first_goal_team: Mapped[str | None] = mapped_column(nullable=True)
    first_goal_minute: Mapped[int | None] = mapped_column(nullable=True)
    
    results: Mapped[list["MatchResult"]] = relationship(
        back_populates="match",
        cascade="all, delete-orphan",
    )

    children: Mapped[list["Match"]] = relationship("Match", back_populates="parent")


class MatchMember(Base):
    __tablename__ = "match_member"

    id: Mapped[intpk]
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), nullable=False, index=True
    )
    home_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True
    )
    away_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id", "home_id", "away_id", name="uq_match_member_combination"
        ),
    )

    match: Mapped["Match"] = relationship("Match", back_populates="members")

    home_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[home_id], back_populates="home_matches"
    )

    away_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[away_id], back_populates="away_matches"
    )


class Team(Base):
    __tablename__ = "team"

    id: Mapped[intpk]
    name: Mapped[str_64] = mapped_column(nullable=False)
    league_id: Mapped[int] = mapped_column(
        ForeignKey("league.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("name", "league_id", name="uq_team_combination"),
    )

    home_matches: Mapped[list["MatchMember"]] = relationship(
        "MatchMember", foreign_keys=[MatchMember.home_id], back_populates="home_team"
    )

    away_matches: Mapped[list["MatchMember"]] = relationship(
        "MatchMember", foreign_keys=[MatchMember.away_id], back_populates="away_team"
    )


class Bet(Base):
    __tablename__ = "bet"

    id: Mapped[intpk]
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"), nullable=False, index=True
    )
    point: Mapped[float] = mapped_column(nullable=True)
    limit: Mapped[int] = mapped_column(nullable=False, default=0)
    home_cf: Mapped[float] = mapped_column(nullable=False)
    draw_cf: Mapped[float] = mapped_column(nullable=True)
    away_cf: Mapped[float] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    period: Mapped[int] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, index=True)
    __table_args__ = (
        Index(
            "idx_bet_latest_version",
            "match_id",
            "type",
            "period",
            "version",
            postgresql_ops={"version": "desc"},
        ),
    )


class User(Base):
    __tablename__ = "user"
    email: Mapped[str] = mapped_column(primary_key=True, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(nullable=False)
    session_id: Mapped[str] = mapped_column(nullable=True)
    telegram_id: Mapped[str] = mapped_column(nullable=True)
    disabled: Mapped[bool] = mapped_column(nullable=False, default=False)
    superuser: Mapped[bool] = mapped_column(nullable=False, default=False)
    created_at: Mapped[created_at]


class InviteCode(Base):
    __tablename__ = "invite_code"

    id: Mapped[intpk]
    code: Mapped[str] = mapped_column(unique=True, index=True)
    user_email: Mapped[str | None] = mapped_column(
        ForeignKey("user.email", ondelete="CASCADE"), nullable=True, index=True
    )
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]


class MatchResult(Base):
    __tablename__ = "match_result"

    id: Mapped[intpk]

    match_id: Mapped[int] = mapped_column(
        ForeignKey("match.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    period_order: Mapped[int] = mapped_column(nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(nullable=False, index=True)

    team_1_score: Mapped[int] = mapped_column(nullable=False)
    team_2_score: Mapped[int] = mapped_column(nullable=False)

    external_period_id: Mapped[int | None] = mapped_column(nullable=True)

    match: Mapped["Match"] = relationship(back_populates="results")

    __table_args__ = (
        UniqueConstraint("match_id", "period_order", name="uq_match_result_match_period"),
    )


# Архивные таблицы
class MatchArchive(Base):
    __tablename__ = "match_archive"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("match_archive.id"), nullable=True, index=True
    )
    league_id: Mapped[int] = mapped_column(ForeignKey("league.id"), nullable=False)
    start_time: Mapped[datetime.datetime] = mapped_column(nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False)

    status_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    status_name: Mapped[str] = mapped_column(nullable=False, default="unknown", index=True)

    total_home_score: Mapped[int | None] = mapped_column(nullable=True)
    total_away_score: Mapped[int | None] = mapped_column(nullable=True)

    winning_team: Mapped[str | None] = mapped_column(nullable=True)

    first_goal_team: Mapped[str | None] = mapped_column(nullable=True)
    first_goal_minute: Mapped[int | None] = mapped_column(nullable=True)

    archived_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow, nullable=False
    )


class MatchMemberArchive(Base):
    __tablename__ = "match_member_archive"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match_archive.id", ondelete="CASCADE"), nullable=False, index=True
    )
    home_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True
    )
    away_id: Mapped[int] = mapped_column(
        ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True
    )
    archived_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "match_id", "home_id", "away_id", name="uq_match_member_archive_combination"
        ),
    )


class BetArchive(Base):
    __tablename__ = "bet_archive"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match_archive.id", ondelete="CASCADE"), nullable=False, index=True
    )
    point: Mapped[float] = mapped_column(nullable=True)
    limit: Mapped[int] = mapped_column(nullable=False, default=0)
    home_cf: Mapped[float] = mapped_column(nullable=False)
    draw_cf: Mapped[float] = mapped_column(nullable=True)
    away_cf: Mapped[float] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    period: Mapped[int] = mapped_column(nullable=False)
    key: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime.datetime] = mapped_column(nullable=False, index=True)
    archived_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow, nullable=False
    )

    __table_args__ = (
        Index(
            "idx_bet_archive_latest_version",
            "match_id",
            "type",
            "period",
            "version",
            postgresql_ops={"version": "desc"},
        ),
    )


class MatchResultArchive(Base):
    __tablename__ = "match_result_archive"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("match_archive.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_order: Mapped[int] = mapped_column(nullable=False, index=True)
    period_type: Mapped[str] = mapped_column(nullable=False, index=True)

    team_1_score: Mapped[int] = mapped_column(nullable=False)
    team_2_score: Mapped[int] = mapped_column(nullable=False)

    external_period_id: Mapped[int | None] = mapped_column(nullable=True)

    archived_at: Mapped[datetime.datetime] = mapped_column(
        default=datetime.datetime.utcnow, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("match_id", "period_order", name="uq_match_result_match_archive_period"),
    )
