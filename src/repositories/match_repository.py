from datetime import datetime, timedelta
from typing import List, Tuple

from sqlalchemy import (asc, case, delete, desc, distinct, func, or_, select,
                        update)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, selectinload

from src.core.models import Bet, League, Match, MatchMember, MatchResult, Team


class MatchRepository:

    @staticmethod
    async def get_matches_by_date(
        date: datetime,
        sport_id: int,
        session: AsyncSession,
    ) -> List[Match]:
        start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)

        stmt = (
            select(Match)
            .join(League, League.id == Match.league_id)
            .options(
                selectinload(Match.members),
                selectinload(Match.members).selectinload(MatchMember.home_team),
                selectinload(Match.members).selectinload(MatchMember.away_team),
            )
            .where(
                League.sport_id == sport_id,
                Match.start_time >= start_date,
                Match.start_time < end_date,
                Match.parent_id.is_(None),
            )
            .order_by(Match.start_time.asc())
        )

        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_upcoming_matches(session: AsyncSession):
        stmt = (
            select(Match, League.sport_id)
            .join(League, League.id == Match.league_id)
            .where(Match.start_time > datetime.utcnow())
            .order_by(Match.start_time.asc())
        )
        result = await session.execute(stmt)
        rows = result.all()

        matches = []

        for match, sport_id in rows:
            match.sport_id = sport_id
            matches.append(match)

        return matches

    @staticmethod
    async def get_match_with_teams(match_id: int, session: AsyncSession) -> dict | None:
        home_team = aliased(Team)
        away_team = aliased(Team)

        stmt = (
            select(
                Match.id.label("match_id"),
                Match.league_id.label("league_id"),
                Match.start_time.label("start_time"),
                League.name.label("league_name"),
                League.sport_id.label("sport_id"),
                home_team.id.label("home_team_id"),
                away_team.id.label("away_team_id"),
                home_team.name.label("home_name"),
                away_team.name.label("away_name"),
            )
            .select_from(Match)
            .outerjoin(League, League.id == Match.league_id)
            .outerjoin(MatchMember, MatchMember.match_id == Match.id)
            .outerjoin(home_team, MatchMember.home_id == home_team.id)
            .outerjoin(away_team, MatchMember.away_id == away_team.id)
            .where(Match.id == match_id)
        )

        result = await session.execute(stmt)
        row = result.mappings().one_or_none()

        if not row:
            return None

        result_stmt = (
            select(
                MatchResult.period.label("period"),
                MatchResult.description.label("description"),
                MatchResult.team_1_score.label("team_1_score"),
                MatchResult.team_2_score.label("team_2_score"),
            )
            .where(MatchResult.match_id == match_id)
            .order_by(MatchResult.period.asc())
        )

        result_rows = await session.execute(result_stmt)

        return {
            "match": dict(row),
            "match_results": [dict(item) for item in result_rows.mappings().all()],
        }

    @staticmethod
    async def get_team_games(
        team_id: int,
        current_match_id: int,
        session: AsyncSession,
    ) -> list[dict]:
        home_team = aliased(Team)
        away_team = aliased(Team)
        child_match = aliased(Match)

        match_result_subq = (
            select(
                MatchResult.match_id,
                MatchResult.description,
                MatchResult.team_1_score,
                MatchResult.team_2_score,
            )
            .where(MatchResult.period == 0)
            .subquery()
        )

        change_count = func.count(case((Bet.version >= 1, Bet.id), else_=None))

        stmt = (
            select(
                Match.id.label("id"),
                Match.start_time.label("start_time"),
                League.name.label("league_name"),
                home_team.name.label("home_name"),
                away_team.name.label("away_name"),
                home_team.id.label("home_team_id"),
                away_team.id.label("away_team_id"),
                child_match.id.label("child_id"),
                match_result_subq.c.description.label("result_title"),
                match_result_subq.c.team_1_score.label("home_score"),
                match_result_subq.c.team_2_score.label("away_score"),
                change_count.label("change_count"),
            )
            .join(MatchMember, Match.id == MatchMember.match_id)
            .join(League, League.id == Match.league_id)
            .join(home_team, home_team.id == MatchMember.home_id)
            .join(away_team, away_team.id == MatchMember.away_id)
            .outerjoin(Bet, Bet.match_id == Match.id)
            .outerjoin(match_result_subq, match_result_subq.c.match_id == Match.id)
            .outerjoin(child_match, child_match.parent_id == Match.id)
            .where(
                or_(
                    MatchMember.home_id == team_id,
                    MatchMember.away_id == team_id,
                ),
                Match.id != current_match_id,
            )
            .group_by(
                Match.id,
                Match.start_time,
                League.name,
                home_team.name,
                away_team.name,
                home_team.id,
                away_team.id,
                child_match.id,
                match_result_subq.c.description,
                match_result_subq.c.team_1_score,
                match_result_subq.c.team_2_score,
            )
            .order_by(Match.start_time.desc())
        )

        result = await session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def get_related_match_counts(session: AsyncSession) -> list[dict]:
        utc_now = datetime.utcnow()
        bet_match = aliased(Match)
        bet = aliased(Bet)

        stmt = (
            select(
                League.sport_id.label("sport_id"),
                func.count(distinct(Match.id)).label("count"),
            )
            .select_from(League)
            .outerjoin(Match, League.id == Match.league_id)
            .outerjoin(
                bet_match,
                or_(bet_match.id == Match.id, bet_match.parent_id == Match.id),
            )
            .outerjoin(bet, bet.match_id == bet_match.id)
            .where(
                Match.start_time > utc_now,
                Match.parent_id.is_(None),
                bet.version >= 1,
            )
            .group_by(League.sport_id)
        )

        result = await session.execute(stmt)
        return [dict(row) for row in result.mappings().all()]

    @staticmethod
    async def get_related_matches(
        session: AsyncSession,
        sport_id: int,
        league_id: int | None = None,
        hours: int | None = None,
        finished: bool = False,
        nulls: bool = False,
        sort_by: str = "team_name",
        sort_order: str = "ASC",
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        utc_now = datetime.utcnow()

        home_team = aliased(Team)
        away_team = aliased(Team)
        child_match = aliased(Match)
        bet_match = aliased(Match)
        bet = aliased(Bet)

        change_count = func.count(case((bet.version >= 1, bet.id), else_=None))
        last_update = func.max(bet.created_at).filter(bet.version >= 1)

        sort_map = {
            "team_name": home_team.name,
            "league_name": League.name,
            "change_count": change_count,
            "last_change": last_update,
            "start_time": Match.start_time,
        }
        sort_col = sort_map.get(sort_by, home_team.name)
        sort_expr = asc(sort_col) if sort_order.upper() == "ASC" else desc(sort_col)

        stmt = (
            select(
                Match.id.label("id"),
                Match.start_time.label("start_time"),
                League.name.label("league_name"),
                change_count.label("change_count"),
                last_update.label("last_update"),
                home_team.name.label("home_name"),
                away_team.name.label("away_name"),
                home_team.id.label("home_team_id"),
                away_team.id.label("away_team_id"),
                Match.created_at.label("created_at"),
                child_match.id.label("child_id"),
            )
            .select_from(Match)
            .outerjoin(League, League.id == Match.league_id)
            .outerjoin(MatchMember, MatchMember.match_id == Match.id)
            .outerjoin(home_team, MatchMember.home_id == home_team.id)
            .outerjoin(away_team, MatchMember.away_id == away_team.id)
            .outerjoin(child_match, child_match.parent_id == Match.id)
            .outerjoin(
                bet_match,
                or_(bet_match.id == Match.id, bet_match.parent_id == Match.id),
            )
            .outerjoin(bet, bet.match_id == bet_match.id)
            .where(
                League.sport_id == sport_id,
                Match.parent_id.is_(None),
            )
            .group_by(
                Match.id,
                Match.start_time,
                League.name,
                home_team.name,
                away_team.name,
                home_team.id,
                away_team.id,
                Match.created_at,
                child_match.id,
            )
        )

        if league_id is not None:
            stmt = stmt.where(League.id == league_id)

        stmt = stmt.where(
            Match.start_time < utc_now if finished else Match.start_time >= utc_now
        )

        if hours is not None:
            stmt = stmt.where(Match.start_time < utc_now + timedelta(hours=hours))

        if not nulls:
            stmt = stmt.having(change_count > 0)

        stmt = stmt.order_by(sort_expr).offset(offset)

        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        rows = result.mappings().all()

        return [
            {
                **dict(row),
                "event": f'{row["home_name"]} - {row["away_name"]}',
            }
            for row in rows
        ]

    @staticmethod
    async def count_related_matches(
        session: AsyncSession,
        sport_id: int,
        league_id: int | None = None,
        hours: int | None = None,
        finished: bool = False,
        nulls: bool = False,
    ) -> int:
        utc_now = datetime.utcnow()

        bet_match = aliased(Match)
        bet = aliased(Bet)

        change_count = func.count(case((bet.version >= 1, bet.id), else_=None))

        stmt = (
            select(Match.id)
            .select_from(Match)
            .outerjoin(League, League.id == Match.league_id)
            .outerjoin(
                bet_match,
                or_(bet_match.id == Match.id, bet_match.parent_id == Match.id),
            )
            .outerjoin(bet, bet.match_id == bet_match.id)
            .where(
                League.sport_id == sport_id,
                Match.parent_id.is_(None),
            )
            .group_by(Match.id)
        )

        if league_id is not None:
            stmt = stmt.where(League.id == league_id)

        stmt = stmt.where(
            Match.start_time < utc_now if finished else Match.start_time >= utc_now
        )

        if hours is not None:
            stmt = stmt.where(Match.start_time < utc_now + timedelta(hours=hours))

        if not nulls:
            stmt = stmt.having(change_count > 0)

        count_stmt = select(func.count()).select_from(stmt.subquery())

        result = await session.execute(count_stmt)
        return result.scalar_one()

    @staticmethod
    async def get_existing_ids(
        match_ids: list[int],
        session: AsyncSession,
    ) -> set[int]:
        if not match_ids:
            return set()

        stmt = select(Match.id).where(Match.id.in_(match_ids))
        result = await session.execute(stmt)
        return set(result.scalars().all())

    @staticmethod
    async def update_start_time(
        match_id: int,
        new_start_time: datetime,
        session: AsyncSession,
    ) -> None:
        stmt = (
            update(Match).where(Match.id == match_id).values(start_time=new_start_time)
        )
        await session.execute(stmt)
        await session.commit()

    @staticmethod
    async def add_match_cascade(
        league: League,
        match: Match,
        team_home: Team,
        team_away: Team,
        session: AsyncSession,
    ) -> Match:
        try:
            await session.execute(
                insert(League)
                .values(id=league.id, sport_id=league.sport_id, name=league.name)
                .on_conflict_do_nothing()
            )
            await session.execute(
                insert(Match)
                .values(
                    id=match.id,
                    parent_id=match.parent_id,
                    league_id=match.league_id,
                    start_time=match.start_time,
                )
                .on_conflict_do_nothing()
            )
            home_id = await session.execute(
                insert(Team)
                .values(name=team_home.name, league_id=league.id)
                .on_conflict_do_update(
                    index_elements=["name", "league_id"],
                    set_={"name": team_home.name},
                )
                .returning(Team.id)
            )
            home_id = home_id.scalar()

            away_id = await session.execute(
                insert(Team)
                .values(name=team_away.name, league_id=league.id)
                .on_conflict_do_update(
                    index_elements=["name", "league_id"],
                    set_={"name": team_away.name},
                )
                .returning(Team.id)
            )
            away_id = away_id.scalar()
            if home_id and away_id:
                await session.execute(
                    insert(MatchMember)
                    .values(
                        match_id=match.id,
                        home_id=home_id,
                        away_id=away_id,
                    )
                    .on_conflict_do_nothing()
                )
        except Exception:
            await session.rollback()
            raise

    @staticmethod
    async def get_matches_older_than(
        threshold_time: datetime,
        session: AsyncSession,
    ) -> list[Match]:
        stmt = select(Match).where(Match.start_time < threshold_time)
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_match_members(
        match_ids: list[int],
        session: AsyncSession,
    ) -> list[MatchMember]:
        if not match_ids:
            return []

        stmt = select(MatchMember).where(MatchMember.match_id.in_(match_ids))
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def get_match_results(
        match_ids: list[int],
        session: AsyncSession,
    ) -> list[MatchResult]:
        if not match_ids:
            return []

        stmt = select(MatchResult).where(MatchResult.match_id.in_(match_ids))
        result = await session.execute(stmt)
        return result.scalars().all()

    @staticmethod
    async def delete_matches(
        match_ids: list[int],
        session: AsyncSession,
    ) -> None:
        if not match_ids:
            return

        stmt = delete(Match).where(Match.id.in_(match_ids))
        await session.execute(stmt)
