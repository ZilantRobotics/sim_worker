from __future__ import annotations

import asyncio
import sys
from argparse import ArgumentParser

from decouple import AutoConfig

from config_options import Commands, ConfigVars
from src.api.core import Command
from src.api.websocket_connection.websocket_client import Client

from src.communicators.cli_communicator import CliCommunicator
from src.communicators.wss_communicator import WssCommunicator
from src.core.sim_core import SimCore
from src.logger import logger

config = AutoConfig('./config')

ORDERED_ARGS = 'ordered_args'


argparser = ArgumentParser()
argparser.add_argument(
    '--verbose', '-v', action='count', default=0,
    help='set to -vvv for maximum verbosity')
subparsers = argparser.add_subparsers(dest='command')
subparsers.required = True

wss_parser = subparsers.add_parser(
    Commands.WSS,
    help='create a new sim with wss server')

wss_parser.add_argument(
    '--host',
    default=config(ConfigVars.SIM_WSS_REMOTE_HOST.name, None) or 'localhost',
    type=str, dest=ConfigVars.SIM_WSS_REMOTE_HOST.name,
    help='specify a host for the remote connection')
wss_parser.add_argument(
    '--port',
    default=config(ConfigVars.SIM_WSS_REMOTE_PORT.name, None) or 9090,
    type=int, dest=ConfigVars.SIM_WSS_REMOTE_PORT.name,
    help='specify a port for the remote connection')
wss_parser.add_argument(
    '--ca_cert', type=str, dest=ConfigVars.SIM_CA_CERT.name,
    default=config(ConfigVars.SIM_CA_CERT.name, None),
    help='specify ca cert of the WSS server'
)
wss_parser.add_argument(
    '--ca_key', type=str, dest=ConfigVars.SIM_CA_KEY.name,
    default=config(ConfigVars.SIM_CA_KEY.name, None),
    help='specify ca key of the WSS server'
)
wss_parser.add_argument(
    '--local-port', type=int, dest=ConfigVars.SIM_WSS_LOCAL_PORT.name,
    default=config(ConfigVars.SIM_WSS_LOCAL_PORT.name, None),
    help='specify a port for local cli connections. '
         'If left empty, no local connection will be allowed'
)
wss_parser.add_argument(
    '--local-host', type=str, dest=ConfigVars.SIM_WSS_LOCAL_HOST.name,
    default=config(ConfigVars.SIM_WSS_LOCAL_HOST.name, None),
    help='specify a host for local cli connections. '
         'If left empty, no local connection will be allowed'
)
wss_parser.add_argument(
    '--worker_name', type=str, dest=ConfigVars.SIM_WORKER_NAME,
    default=config(ConfigVars.SIM_WORKER_NAME.name, None),
    help='specify a worker name')

wss_parser.add_argument(
    '--worker_uuid', type=str, dest=ConfigVars.SIM_WORKER_UUID,
    default=config(ConfigVars.SIM_WORKER_UUID.name, None),
    help='specify a worker uuid (you can obtain it from the server)')


cli_parser = subparsers.add_parser(
    Commands.CLI, help='execute opcodes from cli on a (new) sim instance and close it afterwards')

cli_parser.add_argument(
    '--new', action='store_true', dest='new',
    help='if specified, create a new sim instance. Can not be used with --local-port')
cli_parser.add_argument(
    '--local-port', type=int, dest=ConfigVars.SIM_WSS_LOCAL_PORT.name,
    default=config(ConfigVars.SIM_WSS_LOCAL_PORT.name, None) or 9999,
    help='connect to a local sim instance on this port. Can not be used with --new')
cli_parser.add_argument(
    '--local-host', type=str, dest=ConfigVars.SIM_WSS_LOCAL_HOST.name,
    default=config(ConfigVars.SIM_WSS_LOCAL_HOST.name, None) or 'localhost',
    help='connect to a local sim instance on this host. Can not be used with --new')

cli_parser.add_argument(
    '--opcodes', action='append', dest='opcodes', nargs='+',
    help='provide a JSON-formatted opcode. Escape JSON quotes with \\')

LOCAL_NAME = 'local'
LOCAL_UUID = '42bcc394-10a6-4b5c-a4c5-9fefde697a08'

arguments = vars(argparser.parse_args())

if arguments['command'] == Commands.CLI and (arguments.get('opcodes') is None):
    logger.critical('Nothing to do! Please specify --opcodes')
    sys.exit(1)

logger.info("Booting up")

if arguments['command'] == Commands.WSS:
    sim = SimCore(
        communicator=WssCommunicator,
        remote_host=arguments[ConfigVars.SIM_WSS_REMOTE_HOST],
        remote_port=arguments[ConfigVars.SIM_WSS_REMOTE_PORT],
        cert=arguments[ConfigVars.SIM_CA_CERT],
        key=arguments[ConfigVars.SIM_CA_KEY],
        is_local_wss_enabled=all([
            arguments[ConfigVars.SIM_WSS_LOCAL_PORT],
            arguments[ConfigVars.SIM_WSS_LOCAL_HOST]]),
        local_host=arguments[ConfigVars.SIM_WSS_LOCAL_HOST],
        local_port=arguments[ConfigVars.SIM_WSS_LOCAL_PORT],
        name=arguments[ConfigVars.SIM_WORKER_NAME],
        uuid=arguments[ConfigVars.SIM_WORKER_UUID])
    sim.run()
elif arguments['command'] == Commands.CLI and arguments['new']:
    sim = SimCore(
        communicator=CliCommunicator,
        opcode_list=arguments['opcodes'],
        local_port=arguments[ConfigVars.SIM_WSS_LOCAL_PORT])
    sim.run()
elif arguments['command'] == Commands.CLI and not arguments['new']:
    wss_client = Client(
        host=arguments[ConfigVars.SIM_WSS_LOCAL_HOST],
        port=arguments[ConfigVars.SIM_WSS_LOCAL_PORT],
        name=LOCAL_NAME,
        uuid=LOCAL_UUID
    )

    async def cb(cmd: Command):
        return await wss_client.send(cmd)

    com = CliCommunicator(
        opcode_list=arguments['opcodes'],
        dest=cb
    )

    async def run():
        await wss_client.connect()
        await com.setup()
        await wss_client.close()
    asyncio.run(run())

else:
    raise ValueError(f'Unknown command {arguments["command"]}')
