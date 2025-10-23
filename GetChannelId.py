from telethon import TelegramClient
from dotenv import load_dotenv
import os
import asyncio


async def main():
    load_dotenv()
    # Validate required environment variables
    session_name = os.getenv("SESSION_NAME", "signals_session")
    api_id_raw = os.getenv("API_ID")
    api_hash = os.getenv("API_HASH")

    if not api_id_raw or not api_hash:
        print("Error: API_ID and API_HASH environment variables are required.")
        print("Create a .env file or export them in your shell. Example .env:\nAPI_ID=123456\nAPI_HASH=your_api_hash\nSESSION_NAME=signals_session")
        return

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print(f"Error: API_ID must be an integer. Got: {api_id_raw!r}")
        return

    # Create the client and connect
    client = TelegramClient(session_name, api_id, api_hash)
    await client.start()

    header = "Signed in successfully. Fetching dialogs...\n\n"
    print(header)

    # Collect output lines so we can both print and save to a file
    out_lines = [header]

    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        username = getattr(entity, 'username', 'N/A')

        block = []
        block.append(f"Name: {dialog.name or ''}")
        block.append(f"Username: {username}")
        block.append(f"ID: {entity.id}")
        block.append(f"Access Hash: {getattr(entity, 'access_hash', 'N/A')}")
        block.append(f"Type: {type(entity).__name__}")
        block.append("-" * 40)

        text_block = "\n".join(block) + "\n"
        print(text_block)
        out_lines.append(text_block)

    await client.disconnect()

    # Save results to ChannelIds.txt (UTF-8), overwrite each run
    try:
        with open('ChannelIds.txt', 'w', encoding='utf-8') as f:
            f.writelines(out_lines)
        print("Saved dialog list to ChannelIds.txt")
    except Exception as e:
        print(f"Warning: failed to write ChannelIds.txt: {e}")

if __name__ == "__main__":
    asyncio.run(main())