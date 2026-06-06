import os
import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor

from browser_use import Agent, Browser, BrowserProfile
from browser_use.llm import ChatGoogle
from dotenv import load_dotenv

load_dotenv()

_executor = ThreadPoolExecutor(max_workers=1)


def get_llm() -> ChatGoogle:
    return ChatGoogle(model="gemini-2.5-flash")


def get_browser(stealth: bool = False) -> Browser:
    # HEADLESS=true  → headless Playwright Chromium (server/cloud deployment)
    # HEADLESS=false → local Chrome via CHROME_PATH (default for local dev)
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    chrome_path = os.getenv("CHROME_PATH") if not headless else None

    profile = BrowserProfile(
        keep_alive=False,
        stealth=stealth,
        headless=headless,
        executable_path=chrome_path,
    )
    return Browser(browser_profile=profile)


async def _run_agent_inner(task: str) -> str:
    llm = get_llm()
    browser = get_browser()
    agent_instance = Agent(task=task, llm=llm, browser=browser)
    response = await agent_instance.run()
    if response.final_result():
        return response.final_result()
    return str(response)


def _run_in_thread(task: str) -> str:
    # Uvicorn on Windows uses SelectorEventLoop, which does not support
    # subprocess creation (needed by browser_use to launch the browser).
    # Running the agent in a dedicated thread with ProactorEventLoop fixes this.
    loop = asyncio.ProactorEventLoop() if sys.platform == "win32" else asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_agent_inner(task))
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def run_agent(task: str) -> str:
    return await asyncio.get_event_loop().run_in_executor(_executor, _run_in_thread, task)


if __name__ == "__main__":
    from task import get_task
    asyncio.run(_run_agent_inner(get_task()))