"""
Parser for site http://www.psu.ru/
"""
import asyncio
from dataclasses import asdict, dataclass
from threading import Thread
from typing import Dict
from os import getenv
import json

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from interactions import Embed, Extension, extension_listener, get, User, Webhook
from interactions.ext.tasks import create_task, IntervalTrigger

load_dotenv()

SNILS = getenv("SNILS")
SITE_URL = getenv("SITE_URL")
WEBHOOK_URL = getenv("WEBHOOK_URL")
DISCORD_USER_ID = getenv("DISCORD_USER_ID")  # Optional
EMOJI_ARROW_DOWN = getenv("EMOJI_ARROW_DOWN")  # Optional
EMOJI_ARROW_UP = getenv("EMOJI_ARROW_UP")  # Optional

if not SNILS:
    raise Exception("SNILS not provided in env")
if not SITE_URL:
    raise Exception("PSU site not provided in env")
if not WEBHOOK_URL:
    raise Exception("Webhook url not provided in env")

if SITE_URL[-1] != "/":
    SITE_URL += "/"

try:
    WEBHOOK_ID = WEBHOOK_URL.split("/")[5]
    if not WEBHOOK_ID.isdigit():
        raise Exception("Invalid webhook url!")
    WEBHOOK_TOKEN = WEBHOOK_URL.split("/")[6]
except IndexError:
    raise Exception("Invalid webhook url!")


@dataclass
class Direction:
    name: str
    position: int
    consents: int = None
    originals: int = None
    total_applications: int = None
    total_originals: int = None
    total_consents: int = None


class PSUParser(Extension):
    def __init__(self, client) -> None:
        self.client = client
        self.session = ClientSession()
        self.current_data = {}
        self.previous_data = None
        self.webhook = None

    @extension_listener
    async def on_start(self):
        self.main.start(self)

    @create_task(IntervalTrigger(3 * 60 * 60))  # 3 hours in seconds
    async def main(self):
        data: Dict[str, Direction] = await self.get_results()
        previous_data: Dict[str, Direction] = await self.get_previous_results()
        if not previous_data:
            return await self.update_database(data)

        embed = Embed(
            description="**Место в конкурсе с учётом того, что люди подали оригинал аттестата и согласие на зачисление**",
            color=0xC62E3E,
        )

        if DISCORD_USER_ID:
            user = await get(self.client, User, object_id=int(DISCORD_USER_ID))
            embed.set_author(name=user.username, icon_url=user.avatar_url)

        for code, direction in data.items():
            current_position = direction.position
            previous_position = previous_data[code].position
            if current_position != previous_position:
                if EMOJI_ARROW_UP and EMOJI_ARROW_DOWN:
                    emoji = (
                        EMOJI_ARROW_DOWN
                        if current_position > previous_position
                        else EMOJI_ARROW_UP
                    )
                else:
                    emoji = ''
                description = (
                    f"**Место в конкурсе:** {emoji} `{current_position} ({previous_position})` **Всего:** `{direction.total_applications}` \n"
                    f"**Подано оригиналов:** `{direction.originals}` **Всего:** `{direction.total_originals}`\n"
                    f"**Подано согласий:** `{direction.consents}` **Всего:** `{direction.total_consents}`"
                )
                embed.add_field(name=direction.name, value=description, inline=False)

        if embed.fields:
            await self.send_message(embed=embed)
            await self.update_database(data)

    async def get_results(self):
        async with self.session.get(SITE_URL) as response:
            text = await response.text()
        return await self.parse(text)

    async def get_previous_results(self):
        if self.previous_data is not None:
            return self.previous_data
        with open("psu_data.json") as psu_data:
            psu: dict = json.load(psu_data)
        data = {}
        for code, direction in psu.items():
            data[code] = Direction(**direction)
        return data

    @staticmethod
    def thread_parse(html: str, result: list):
        result.append(BeautifulSoup(html, "html.parser"))

    async def parse(self, html: str):
        result = []
        thread = Thread(
            target=self.thread_parse, args=(html, result)
        )  # Use threads because scraping takes more 20 seconds
        thread.start()
        while not result:
            await asyncio.sleep(5)

        soup = result[0]
        fonts = soup.find_all("font", string=SNILS)
        data = {}
        for font in fonts:
            raw_position = font.parent.parent.find("td").text
            table = font.parent.parent.parent
            article = table.parent
            direction_name = article.find("h2").find_all("span")[2].text
            position = (
                originals
            ) = consents = total_applications = total_originals = total_consents = 0
            trs = table.find_all("tr")
            for tr in trs:
                tds = tr.find_all("td")
                _pos = tds[0].text
                if not _pos.isdigit():  # Skip word `Общий конкурс`
                    continue

                if _pos == raw_position:
                    position = total_applications
                    originals = total_originals
                    consents = total_consents

                if tds[2].text == "+":
                    total_originals += 1
                if tds[3].text == "+":
                    total_consents += 1
                if tds[2].text == "+" and tds[3].text == "+":
                    total_applications += 1

            code = article.find("a")["name"]
            data[code] = Direction(
                name=direction_name,
                position=position + 1,
                consents=consents,
                originals=originals,
                total_applications=total_applications,
                total_originals=total_originals,
                total_consents=total_consents,
            )

        return data

    async def send_message(self, embed: Embed):
        if not self.webhook:
            self.webhook = await Webhook.get(
                self.client._http,
                int(WEBHOOK_ID),
                WEBHOOK_TOKEN
            )
        await self.webhook.execute(embeds=embed)

    async def update_database(self, data: Dict[str, Direction]):
        to_send = {key: asdict(value) for key, value in data.items()}

        with open("psu_data.json", "w") as psu_data:
            json.dump(to_send, psu_data)

        self.previous_data = data


def setup(client):
    PSUParser(client)
