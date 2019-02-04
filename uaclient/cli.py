#!/usr/bin/env python

"""\
Client to manage Ubuntu Advantage support entitlements on a machine.

Available entitlements:
 - Extended Support and Maintenance (https://ubuntu.com/esm)
 - Federal Information Processing Standards
 - Federal Information Processing Standards Updates
 - Canonical Livepatch (https://www.ubuntu.com/server/livepatch)

"""

import argparse
from datetime import datetime
import logging
import os
import sys
import textwrap

from uaclient import config
from uaclient import contract
from uaclient import entitlements
from uaclient import sso
from uaclient import status as ua_status
from uaclient import util

NAME = 'ubuntu-advantage-client'

USAGE_TMPL = '{name} {command} [flags]'
EPILOG_TMPL = (
    'Use {name} {command} --help for more information about a command.')

STATUS_HEADER_TMPL = """\
Account: {account}
Subscription: {subscription}
Valid until: {contract_expiry}
Technical support: {support_level}
"""

# List of PRS needed for full MVP support
MISSING_PR22 = 'Missing PR#22'


def attach_parser(parser=None):
    """Build or extend an arg parser for attach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='attach [token]')
    if not parser:
        parser = argparse.ArgumentParser(
            prog='attach',
            description=('Attach this machine to an existing Ubuntu Advantage'
                         ' support subscription'),
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'attach'
    parser._optionals.title = 'Flags'
    parser.add_argument(
        'token', nargs='?',
        help='Optional token obtained from Ubuntu Advantage dashboard')
    parser.add_argument(
        '--email', action='store',
        help='Optional email address for Ubuntu SSO login')
    parser.add_argument(
        '--password', action='store',
        help='Optional password for Ubuntu SSO login')
    parser.add_argument(
        '--otp', action='store',
        help=('Optional one-time password for login to Ubuntu Advantage'
              ' Dashboard'))
    return parser


def detach_parser(parser=None):
    """Build or extend an arg parser for detach subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='detach')
    if not parser:
        parser = argparse.ArgumentParser(
            prog='detach',
            description=(
                'Detach this machine from an existing Ubuntu Advantage'
                ' support subscription'),
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'detach'
    parser._optionals.title = 'Flags'
    return parser


def enable_parser(parser=None):
    """Build or extend an arg parser for enable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='enable') + ' <entitlement>'
    if not parser:
        parser = argparse.ArgumentParser(
            prog='enable',
            description='Enable a support entitlement on this machine',
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'enable'
    parser._positionals.title = 'Entitlements'
    parser._optionals.title = 'Flags'
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support entitlement to enable')
    return parser


def disable_parser(parser=None):
    """Build or extend an arg parser for disable subcommand."""
    usage = USAGE_TMPL.format(name=NAME, command='disable') + ' <entitlement>'
    if not parser:
        parser = argparse.ArgumentParser(
            prog='disable',
            description='Disable a support entitlement on this machine',
            usage=usage)
    else:
        parser.usage = usage
        parser.prog = 'disable'
    parser._positionals.title = 'Entitlements'
    parser._optionals.title = 'Flags'
    entitlement_names = list(
        cls.name for cls in entitlements.ENTITLEMENT_CLASSES)
    parser.add_argument(
        'name', action='store', choices=entitlement_names,
        help='The name of the support entitlement to disable')
    return parser


def action_disable(args, cfg):
    """Perform the disable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    return 0 if entitlement.disable() else 1


def action_enable(args, cfg):
    """Perform the enable action on a named entitlement.

    @return: 0 on success, 1 otherwise
    """
    ent_cls = entitlements.ENTITLEMENT_CLASS_BY_NAME[args.name]
    entitlement = ent_cls(cfg)
    return 0 if entitlement.enable() else 1


def action_detach(args, cfg):
    """Perform the detach action for this machine.

    @return: 0 on success, 1 otherwise
    """
    if not cfg.is_attached:
        print(textwrap.dedent("""\
            This machine is not attached to a UA Subscription, sign up here:
                  https://ubuntu.com/advantage
        """))
        return 1
    if os.getuid() != 0:
        print(ua_status.MESSAGE_NONROOT_USER)
        return 1
    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg)
        if ent.can_disable(silent=True):
            ent.disable(silent=True)
    cfg.delete_cache('machine-token')
    cfg.delete_cache('oauth')
    print('This machine is now detached')
    return 0


def action_attach(args, cfg):
    if cfg.is_attached:
        print("This machine is already attached to '%s'." % MISSING_PR22)
        return 0
    if os.getuid() != 0:
        print(ua_status.MESSAGE_NONROOT_USER)
        return 1
    if not args.token:
        user_token = sso.prompt_oauth_token(cfg)
    else:
        user_token = {
            'date_created': datetime.utcnow().strftime(
                '%Y-%m-%dT%H:%M:%S.%fZ'),
            'token_key': args.token}
        cfg.write_cache('oauth', user_token)
    if not user_token:
        print('Could not attach machine. Unable to obtain authenticated user'
              ' token')
        return 1
    contract_client = contract.UAContractClient(cfg)
    try:
        token_response = contract_client.request_contract_machine_attach(
            user_token=user_token['token_key'])
    except (sso.SSOAuthError, util.UrlError) as e:
        logging.error(str(e))
        return 1
    contractInfo = token_response['machineTokenInfo']['contractInfo']
    for entitlement_name in contractInfo['resourceEntitlements'].keys():
        # Obtain each entitlement's accessContext for this machine
        contract_client.request_resource_machine_access(
            cfg.machine_token, entitlement_name)
    print("This machine is now attached to '%s'.\n" %
          token_response['machineTokenInfo']['contractInfo']['name'])
    print_status(cfg=cfg)
    return 0


def get_parser():
    parser = argparse.ArgumentParser(
        prog=NAME, formatter_class=argparse.RawDescriptionHelpFormatter,
        description=__doc__,
        usage=USAGE_TMPL.format(name=NAME, command='[command]'),
        epilog=EPILOG_TMPL.format(name=NAME, command='[command]'))
    parser.add_argument(
        '--debug', action='store_true', help='Show all debug messages')
    parser._optionals.title = 'Flags'
    subparsers = parser.add_subparsers(
        title='Available Commands', dest='command', metavar='')
    subparsers.required = True
    parser_status = subparsers.add_parser(
        'status', help='current status of all ubuntu advantage entitlements')
    parser_status.set_defaults(action=print_status)
    parser_attach = subparsers.add_parser(
        'attach',
        help='attach this machine to an ubuntu advantage subscription')
    attach_parser(parser_attach)
    parser_attach.set_defaults(action=action_attach)
    parser_detach = subparsers.add_parser(
        'detach',
        help='remove this machine from an ubuntu advantage subscription')
    detach_parser(parser_detach)
    parser_detach.set_defaults(action=action_detach)
    parser_enable = subparsers.add_parser(
        'enable',
        help='enable a specific support entitlement on this machine')
    enable_parser(parser_enable)
    parser_enable.set_defaults(action=action_enable)
    parser_disable = subparsers.add_parser(
        'disable',
        help='disable a specific support entitlement on this machine')
    disable_parser(parser_disable)
    parser_disable.set_defaults(action=action_disable)
    parser_version = subparsers.add_parser(
        'version', help='Show version of ua-client')
    parser_version.set_defaults(action=print_version)
    return parser


def print_status(args=None, cfg=None):
    if not cfg:
        cfg = config.UAConfig()
    if not cfg.is_attached:
        print(ua_status.MESSAGE_UNATTACHED)
        return
    contractInfo = cfg.machine_token['machineTokenInfo']['contractInfo']
    expiry = datetime.strptime(
        contractInfo['effectiveTo'], '%Y-%m-%dT%H:%M:%S.%fZ')

    status_content = []
    # TODO(parse-from-TBD contract-api-resourceEntitlement-response)
    status_level = ua_status.STATUS_COLOR.get(
            ua_status.STANDARD, ua_status.STANDARD)
    status_content.append(STATUS_HEADER_TMPL.format(
        account=MISSING_PR22,
        subscription=contractInfo['name'],
        contract_expiry=expiry.date(),
        support_level=status_level))

    for ent_cls in entitlements.ENTITLEMENT_CLASSES:
        ent = ent_cls(cfg)
        status_content.append(ua_status.format_entitlement_status(ent))
    status_content.append('\nEnable entitlements with `ua enable <service>`\n')
    print('\n'.join(status_content))


def print_version(_args=None, _cfg=None):
    print(config.get_version())


def setup_logging(level=logging.ERROR):
    fmt = '[%(levelname)s]: %(message)s'
    formatter = logging.Formatter(fmt)
    root = logging.getLogger()
    stderr_found = False
    for handler in root.handlers:
        if hasattr(handler, 'stream') and hasattr(handler.stream, 'name'):
            if handler.stream.name == '<stderr>':
                handler.setLevel(level)
                handler.setFormatter(formatter)
                stderr_found = True
                break
    if not stderr_found:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        console.setLevel(level)
        root.addHandler(console)
    root.setLevel(level)


def main(sys_argv=None):
    if not sys_argv:
        sys_argv = sys.argv
    parser = get_parser()
    args = parser.parse_args(args=sys_argv[1:])
    cfg = config.UAConfig()
    log_level = logging.DEBUG if args.debug else cfg.log_level
    setup_logging(log_level)
    return args.action(args, cfg)


if __name__ == '__main__':
    sys.exit(main())
