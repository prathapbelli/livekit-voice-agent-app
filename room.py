from datetime import timedelta
from livekit.api import CreateRoomRequest
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.local")

from livekit.api import LiveKitAPI
from livekit import api

API_KEY = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")
LIVEKIT_URL = os.getenv("LIVEKIT_URL")

async def get_livekit_access_token(
    identity: str,
    name: str,
    room_name: str,
    can_subscribe: bool = True,
    can_publish: bool = True,
    can_publish_data: bool = True,
    can_publish_sources: list[str] | None = None,
) -> str:
    """
    Get livekit access token
    :param identity:
    :param name:
    :param room_name:
    :param config:
    :param can_subscribe: participant can subscribe/see video or audio of other participants
    :param can_publish: participant can publish/enable video or auido if false they cant enable video or video
    :param can_publish_data: can send messages in chat
    :param can_publish_sources: participant can publish/ enable only the selected source like camera
    :return:
    """
    return (
        api.AccessToken(api_key=API_KEY, api_secret=API_SECRET)
        .with_ttl(timedelta(hours=8))
        .with_identity(identity)
        .with_name(name)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_subscribe=can_subscribe,
                can_publish=can_publish,
                can_publish_data=can_publish_data,
                can_publish_sources=can_publish_sources,
            ),
        )
        .to_jwt()
    )

async def get_livekit_user_access_token() -> dict | None:
    """
    get livekit user access token
    :param agent_data:
    :param request:
    :return:
    """
    room_name: str = f"prathap-room-123"
    tasks: list = [
        get_livekit_access_token(
            identity="enduser-prathap-123",
            name="enduser-prathap-123",
            room_name=room_name,
        ),
        get_livekit_access_token(
            identity="agent-prathap-124",
            name="agent-prathap-124",
            room_name=room_name,
        ),
    ]
    results = await asyncio.gather(*tasks)
    print("generated livekit tokens successfully")
    return {"user_token": results[0], "agent_token": results[1]}


# Will read LIVEKIT_URL, LIVEKIT_API_KEY, and LIVEKIT_API_SECRET from environment variables
async def create_room() -> None:
    lkapi = LiveKitAPI(url=LIVEKIT_URL, api_key=API_KEY, api_secret=API_SECRET)
    try:
        room = await lkapi.room.create_room(CreateRoomRequest(
                name="myroom123",
                empty_timeout=10 * 60,
                max_participants=20,
                ))
        return room
    finally:
        # before your app exits or when the API client is no longer needed, you must close its session
        await lkapi.aclose()


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(get_livekit_user_access_token()))

