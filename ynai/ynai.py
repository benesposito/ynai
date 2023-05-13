from ynab_api import YnabApi
from transactions import VenmoTransaction, Transaction

from abc import ABC, abstractmethod
import argparse
import logging
from typing import Any
import sys


def resolve_source(source: Any, ynab: YnabApi) -> list[Transaction]:
    try:
        return VenmoTransaction.list_from(source)
    except FileNotFoundError:
        pass

    try:
        return ynab.transactions.get(source)
    except:
        pass

    raise RuntimeError("Could not detect source")


class Command(ABC):
    def __init__(self, subparser):
        parser = subparser.add_parser(self.name())
        parser.set_defaults(execute=self.execute)

        self.post_init()
        self.setup_args(parser)

    def post_init(self):
        pass

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def setup_args(self, parser):
        pass

    @abstractmethod
    def execute(self, args):
        pass


class ListCommand(Command):
    def post_init(self):
        self.options = {
            "budgets": self.budgets_cmd,
            "accounts": self.accounts_cmd,
            "transactions": self.transactions_cmd,
        }

    def name(self):
        return "list"

    def setup_args(self, parser):
        subparser = parser.add_subparsers(dest="option", required=True)

        budgets_subparser = subparser.add_parser("budgets")
        accounts_subparser = subparser.add_parser("accounts")

        transactions_subparser = subparser.add_parser("transactions")
        transactions_subparser.add_argument("source")

    def execute(self, args, ynab):
        cmd = self.options[args.option]
        list = cmd(args, ynab)

        for line in list:
            print(line)

    def get_list_from_ynab(self, args, data):
        if not args.verbose:
            return [obj["name"] for obj in data[args.option]]
        else:
            return ["{} {}".format(obj["id"], obj["name"]) for obj in data[args.option]]

    def budgets_cmd(self, args, ynab) -> list[str]:
        return self.get_list_from_ynab(args, ynab.budgets.get())

    def accounts_cmd(self, args, ynab) -> list[str]:
        return self.get_list_from_ynab(args, ynab.accounts.get())

    def transactions_cmd(self, args, ynab) -> list[Transaction]:
        return resolve_source(args.source, ynab)


class UploadCommand(Command):
    def name(self):
        return "upload"

    def setup_args(self, parser):
        parser.add_argument("account", help="YNAB account name")
        parser.add_argument("source", help="Transactions source")
        parser.add_argument(
            "-n", "--dry-run", action="store_true", help="Don't upload to YNAB"
        )

    def execute(self, args, ynab):
        try:
            source_transactions = VenmoTransaction.list_from(args.source)
        except FileNotFoundError as e:
            raise RuntimeError("File '{}' does not exist".format(args.source))

        existing_transactions = ynab.transactions.get(args.account)

        new_transactions = [
            t for t in source_transactions if t not in existing_transactions
        ]

        if not new_transactions:
            print("No transactions to upload")
            return

        if not args.dry_run:
            ynab.transactions.post(args.account, new_transactions)

        print("Transactions uploaded:")
        print("\n".join(map(str, new_transactions)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", action="count", default=0)
    parser.add_argument("-b", "--budget", help="Override default budget")

    subparser = parser.add_subparsers(required=True)
    commands = [cmd_type(subparser) for cmd_type in (ListCommand, UploadCommand)]

    args = parser.parse_args()

    if args.verbose == 0:
        loglevel = logging.WARNING
    elif args.verbose == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel)

    with open("token", "r") as f:
        token = f.read().strip()

    ynab = YnabApi(token)

    if args.budget:
        ynab.budget = args.budget

    return args.execute(args, ynab)


if __name__ == "__main__":
    sys.exit(main())
