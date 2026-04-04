import asyncio
import datetime

from src.core.db.db_helper import db_helper
from src.core.logger import get_module_logger
from src.events.queues import Queues
from src.events.schemas import EventsResultRequest, _EventResult
from src.events.sender import send_event
from src.repositories.match_repository import MatchRepository

logger = get_module_logger(__name__)


class ResultsService:
    @staticmethod
    async def request_results(sport_id: int, date: datetime):
        async with db_helper.session_factory() as session:
            events = await MatchRepository.get_matches_by_date(
                date=date, sport_id=sport_id, session=session
            )
            events_dtos = []
            for event in events:
                event_id = event.id
                home_team_name = ""
                away_team_name = ""
                for member in event.members:
                    home_team_name = member.home_team.name
                    away_team_name = member.away_team.name

                event_dto = _EventResult(
                    event_id=event_id,
                    home_team_name=home_team_name,
                    away_team_name=away_team_name,
                )
                events_dtos.append(event_dto)

            date_dto = date.date().isoformat()
            events_result_request = EventsResultRequest(
                queue=Queues.MATCH_REQUESTS,
                event_type="events_result",
                date=date_dto,
                events=events_dtos,
            )

            await send_event(events_result_request)

    @staticmethod
    async def save_results(events):
        logger.error(events)


async def main():
    target_date = datetime.datetime(2026, 3, 30)
    sport_id = 33
    await ResultsService.request_results(sport_id=sport_id, date=target_date)


if __name__ == "__main__":
    asyncio.run(main())
