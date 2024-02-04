import webbrowser
import coloredlogs
import colorama
import platform
import inquirer
import asyncio
import aiohttp
import json
import sys
import os


__version__ = "1.1"


os.system('cls')
os.system(f'TITLE ProfileExtractor v{__version__} by Liqutch')
coloredlogs.logging.basicConfig(level=coloredlogs.logging.INFO)
log = coloredlogs.logging.getLogger(__name__)
coloredlogs.install(fmt="[%(asctime)s][%(levelname)s] %(message)s", datefmt="%H:%M:%S", logger=log)


PROFILES = ["athena","campaign","collection_book_people0","collection_book_schematics0","collections","common_core","common_public","creative","metadata","outpost0","proto_juno","recycle_bin","theater0","theater1","theater2"]
SWITCH_TOKEN = "OThmN2U0MmMyZTNhNGY4NmE3NGViNDNmYmI0MWVkMzk6MGEyNDQ5YTItMDAxYS00NTFlLWFmZWMtM2U4MTI5MDFjNGQ3"
IOS_TOKEN = "MzQ0NmNkNzI2OTRjNGE0NDg1ZDgxYjc3YWRiYjIxNDE6OTIwOWQ0YTVlMjVhNDU3ZmI5YjA3NDg5ZDMxM2I0MWE="


class EpicAccount:
    def __init__(self, data: dict = {}) -> None:
        self.raw = data

        self.access_token = data.get("access_token", "")
        self.display_name = data.get("displayName", "")
        self.account_id = data.get("account_id", "")
    
    async def get_profile(self, profile: str) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method="POST",
                url="https://fngw-mcp-gc-livefn.ol.epicgames.com"
                f"/fortnite/api/game/v2/profile/{self.account_id}/client/QueryProfile?profileId={profile}&rvn=-1",
                headers={"Authorization": f"bearer {self.access_token}", "Content-Type": "application/json"},
                data=json.dumps({})
            ) as request:
                if request.status == 200:
                    return await request.json()
                else:
                    data = await request.json()
                    log.info("There was a problem while getting the profile.")
                    log.info("{}/{}/{}\n".format(request.status, data["numericErrorCode"], data["errorCode"]))
                    log.info(f"ProfileExtractor v{__version__} will close in 5 seconds. Try again later.")
                    await asyncio.sleep(5)
                    sys.exit()


class Extractor:
    def __init__(self) -> None:
        self.http: aiohttp.ClientSession

        self.access_token = ""
        self.dir_name = "profiles"
        self.user_agent = f"ProfileExtractor/{__version__} {platform.system()}/{platform.version()}"
        
    async def start(self) -> None:
        self.http = aiohttp.ClientSession(headers={"User-Agent": self.user_agent})

        self.access_token = await self.get_access_token()

        print(f"ProfileExtractor v{__version__} made by Liqutch.")
        await asyncio.sleep(3)

        os.system('cls' if sys.platform.startswith('win') else 'clear')
        log.info("Opening device code link in a new tab...")

        device_code = await self.create_device_code()
        webbrowser.open(device_code[0], new=1)

        account = await self.wait_for_device_code_completion(code=device_code[1])
        os.system('cls' if sys.platform.startswith('win') else 'clear')

        while True:
            log.info(f"Logged in as: {account.display_name}\n")

            questions = [
                inquirer.List('profile',
                    message="What profile do you want to download?",
                    choices=["All"]+PROFILES,
                ),
            ]
            answers = inquirer.prompt(questions)
            os.system('cls' if sys.platform.startswith('win') else 'clear')

            if answers['profile'] == "All":
                for profile in PROFILES:
                    response = await account.get_profile(profile=profile)
                    await self.save_profile_as_file(data=response["profileChanges"][0]["profile"], name=profile)
                    log.info(f"{colorama.Fore.LIGHTBLUE_EX}{profile}{colorama.Style.RESET_ALL} profile has been successfully saved to the /{self.dir_name}/profile_{profile}.json")
            else:
                log.info(f"Requesting for the {answers['profile']} profile...")
                response = await account.get_profile(profile=answers['profile'])
                await self.save_profile_as_file(data=response["profileChanges"][0]["profile"], name=answers['profile'])
                log.info(f"{colorama.Fore.LIGHTBLUE_EX}{answers['profile']}{colorama.Style.RESET_ALL} profile has been successfully saved to the /{self.dir_name}/profile_{answers['profile']}.json")

            choice = [inquirer.Confirm('download_again', message="Do you want to download another profile?",default=True)]

            print("\n")
            answers = inquirer.prompt(choice)

            if answers['download_again']:
                os.system('cls' if sys.platform.startswith('win') else 'clear')
            else:
                os.system('cls' if sys.platform.startswith('win') else 'clear')
                log.info(f'Closing ProfileExtractor v{__version__}...')
                await asyncio.sleep(1)
                break

        await self.http.close()
        sys.exit()

    async def get_access_token(self) -> str:
        async with self.http.request(
            method="POST",
            url="https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"basic {SWITCH_TOKEN}",
            },
            data={
                "grant_type": "client_credentials",
            },
        ) as request:
            data = await request.json()

        return data["access_token"]
    
    async def create_device_code(self) -> tuple:
        async with self.http.request(
            method="POST",
            url="https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/deviceAuthorization",
            headers={
                "Authorization": f"bearer {self.access_token}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        ) as request:
            data = await request.json()

        return data["verification_uri_complete"], data["device_code"]

    async def wait_for_device_code_completion(self, code: str) -> EpicAccount:
        os.system('cls' if sys.platform.startswith('win') else 'clear')
        log.info("Waiting for authentication...")

        while True:
            async with self.http.request(
                method="POST",
                url="https://account-public-service-prod03.ol.epicgames.com/account/api/oauth/token",
                headers={
                    "Authorization": f"basic {SWITCH_TOKEN}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={"grant_type": "device_code", "device_code": code},
            ) as request:
                if request.status == 200:
                    break
                else:
                    pass

                await asyncio.sleep(5)

        auth_data = await request.json()
        return EpicAccount(data=auth_data)

    async def save_profile_as_file(self, data: dict = {}, name: str = "unknown") -> None:
        if not os.path.exists(self.dir_name):
            os.makedirs(self.dir_name)

        json_file_name = os.path.join("profiles", f"profile_{name}.json")
        with open(json_file_name, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, sort_keys=False, indent=2)

    def run(self) -> None:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.start())
        loop.run_forever()


ext = Extractor()
ext.run()