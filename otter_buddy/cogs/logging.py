import asyncio
import logging
import os

from discord.ext import commands

from otter_buddy.utils import discord_common

root_logger = logging.getLogger()
print(__name__)
logger = logging.getLogger(__name__)


class Logging(commands.Cog, logging.Handler):
    def __init__(self, bot, channel_id):
        logging.Handler.__init__(self)
        self.bot = bot
        self.channel_id = channel_id
        self.queue = asyncio.Queue()
        self.task = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @commands.Cog.listener()
    @discord_common.once
    async def on_ready(self):
        self.task = asyncio.create_task(self._log_task())
        width = 59
        msg = f'\n{"*" * width}\n***{"otter-buddy is alive!":^{width - 6}}***\n{"*" * width}'
        self.logger.log(level=100, msg=msg)

    async def _log_task(self):
        while True:
            record = await self.queue.get()
            channel = self.bot.get_channel(self.channel_id)
            if channel is None:
                # Channel no longer exists.
                root_logger.removeHandler(self)
                self.logger.warning('Logging channel not available, disabling Discord log handler.')
                break
            try:
                msg = self.format(record)
                # Not all errors will have message_contents or jump urls.
                try:
                    await channel.send(
                        'Original Command: {}\nJump Url: {}'.format(
                            record.message_content, record.jump_url))
                except AttributeError:
                    pass
                discord_msg_char_limit = 2000
                char_limit = discord_msg_char_limit - 2 * len('```')
                too_long = len(msg) > char_limit
                msg = msg[:char_limit]
                await channel.send('```{}```'.format(msg))
                if too_long:
                    await channel.send('`Check logs for full stack trace`')
            except:
                self.handleError(record)

    # logging.Handler overrides below.

    def emit(self, record):
        self.queue.put_nowait(record)

    def close(self):
        if self.task:
            self.task.cancel()


def setup(bot):
    logging_cog_channel_id = os.environ.get('LOGGING_CHANNEL')
    if logging_cog_channel_id is None:
        logger.info('Skipping installation of logging cog as logging channel is not provided.')
        return

    logging_cog = Logging(bot, int(logging_cog_channel_id))
    logging_cog.setLevel(logging.WARNING)
    logging_cog.setFormatter(logging.Formatter(fmt='{asctime}:{levelname}:{name}:{message}',
                                               style='{', datefmt='%d-%m-%Y %H:%M:%S'))
    root_logger.addHandler(logging_cog)
    bot.add_cog(logging_cog)
