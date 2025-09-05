import logging
import tokenize
from typing import AsyncIterable

from dotenv import load_dotenv
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
    metrics,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import assemblyai, openai, deepgram, silero, turn_detector

from asset import get_asset_data_from_vespa


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("voice-agent")


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


"""
"You are a healthcare-focused voice assistant created by Prathap. Your interface with users will be voice. "
            "You should use short and concise responses, avoiding medical jargon and unpronounceable punctuation. "
            "You can provide general health information, wellness tips, and basic medical guidance, but always remind users "
            "to consult healthcare professionals for specific medical advice, diagnosis, or treatment. You're knowledgeable about "
            "common health conditions, preventive care, healthy lifestyle choices, and general medical terminology. "
            "You were created as a demo to showcase the capabilities of voice agents framework in healthcare applications. "
            "If users describe urgent medical symptoms, always advise them to seek immediate medical attention."
"""

async def entrypoint(ctx: JobContext):
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are a voice assistant created by Prathap"
        ),
    )
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)

    # Wait for the first participant to connect
    participant = await ctx.wait_for_participant()
    logger.info(f"starting voice assistant for participant {participant.identity}")

    async def truncate_context(assistant: VoicePipelineAgent, chat_ctx: llm.ChatContext):
        try:
            asset_data = await get_asset_data_from_vespa(search_string=" ".join([m.content for m in chat_ctx.messages]))
            chat_ctx.append(text=". ".join(asset_data))
        except Exception as e:
            logger.error(f"Error fetching asset data: {e}")
        if len(chat_ctx.messages) > 15:
            chat_ctx.messages = chat_ctx.messages[-15:]


    def replace_words(assistant: VoicePipelineAgent, text: str | AsyncIterable[str]):
        return tokenize.utils.replace_words(
            text=text, replacements={"jeeves": r"<<Agent Jeeves>>"}
        )


    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=assemblyai.STT(),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(),
        turn_detector=turn_detector.EOUModel(),
        # minimum delay for endpointing, used when turn detector believes the user is done with their turn
        min_endpointing_delay=0.5,
        # maximum delay for endpointing, used when turn detector does not believe the user is done with their turn
        max_endpointing_delay=5.0,
        chat_ctx=initial_ctx,
        before_llm_cb=truncate_context,
        # before_tts_cb=replace_words,
    )

    usage_collector = metrics.UsageCollector()

    @agent.on("metrics_collected")
    def on_metrics_collected(agent_metrics: metrics.AgentMetrics):
        metrics.log_metrics(agent_metrics)
        usage_collector.collect(agent_metrics)

    agent.start(ctx.room, participant)

    await agent.say("Hey, how can I help you today?", allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        ),
    )
