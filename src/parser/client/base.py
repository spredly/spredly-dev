from asyncio import TimeoutError
from dataclasses import dataclass
from typing import Any, Optional

import aiohttp
from aiohttp import TCPConnector

from src.services.proxy_service import ProxyService

max_retries = 10


@dataclass
class Response:
    status: int
    data: Any = None
    headers: Optional[dict] = None


async def get_request(
    url: str,
    headers: dict,
    params: dict = None,
    cookies: dict = None,
    use_proxy: bool = False,
) -> Response:
    connector = TCPConnector(limit=2000)
    async with aiohttp.ClientSession(connector=connector, cookies=cookies) as session:
        for _ in range(max_retries):
            proxy = None
            if use_proxy:
                proxy = ProxyService.get_proxy()
            try:
                async with session.get(
                    url, headers=headers, params=params, proxy=proxy, timeout=5
                ) as resp:
                    ctype = resp.headers.get("Content-Type", "").lower()
                    if resp.status == 200:
                        if "application/json" in ctype:
                            response = await resp.json()
                        else:
                            response = await resp.text()
                        return Response(
                            status=resp.status,
                            data=response,
                            headers=dict(resp.headers),
                        )
                    elif resp.status == 404:
                        return Response(status=resp.status)
            except (aiohttp.ContentTypeError, TimeoutError, aiohttp.ClientError):
                continue
        return Response(status=404)
