from ynab_defs import Transaction, YnabTransaction
import ynab_conversions

import requests

from abc import ABC, abstractmethod
import dataclasses
import logging
import json


@dataclasses.dataclass
class NameIdPair:
    name: str
    id: str


class Endpoint(ABC):
    def __init__(self, base_url, ynab):
        self.base_url = base_url
        self.ynab = ynab
        self.session = ynab.session

    def url(self, **url_params):
        endpoint = self.endpoint(**url_params).format(**url_params)

        if not endpoint.startswith("/"):
            raise ValueError("Endpoint must begin with /")

        return self.base_url + endpoint

    def _handle_response(self, res, handle_response):
        if handle_response:
            res.raise_for_status()
            return res.json()["data"]
        else:
            return res

    def _get(self, params=None, handle_response=True, **url_params):
        return self._handle_response(
            self.session.get(self.url(**url_params), params=params), handle_response
        )

    def _post(self, data=None, handle_response=True, **url_params):
        return self._handle_response(
            self.session.post(self.url(**url_params), data=data), handle_response
        )

    @abstractmethod
    def endpoint(self):
        pass

    def get(self):
        raise NotImplementedError()

    def put(self):
        raise NotImplementedError()


class UserEndpoint(Endpoint):
    def endpoint(self, **url_params):
        return "/user"

    def get(self, handle_response=True):
        return self._get(handle_response=handle_response)


class BudgetsEndpoint(Endpoint):
    def endpoint(self, **url_params):
        return "/budgets"

    def get(self):
        return self._get()


class AccountsEndpoint(Endpoint):
    def endpoint(self, **url_params):
        return "/budgets/{budget_id}/accounts".format(budget_id=self.ynab._budget.id)

    def get(self):
        return self._get()


class TransactionsEndpoint(Endpoint):
    def endpoint(self, **url_params):
        if url_params.get("account_id", None):
            endpoint_str = "/budgets/{budget_id}/accounts/{account_id}/transactions"
        else:
            endpoint_str = "/budgets/{budget_id}/transactions"

        return endpoint_str.format(**url_params)

    def get(
        self,
        account_name: str | None,
        since_date=None,
        type=None,
        last_knowledge_of_server=None,
    ):
        if account_name:
            account_id = self.ynab.resolve_account(account_name)
        else:
            account_id = None

        params = {}

        if since_date:
            params["since_date"] = since_date

        if type:
            params["type"] = type

        if last_knowledge_of_server:
            params["last_knowledge_of_server"] = last_knowledge_of_server

        return YnabTransaction.from_list(
            self._get(params, budget_id=self.ynab._budget.id, account_id=account_id)[
                "transactions"
            ]
        )

    def post(self, account_name: str, transactions: list[Transaction]):
        if not transactions:
            raise RuntimeError("No transactions to upload")

        account_id = self.ynab.resolve_account(account_name)

        return self._post(
            data=json.dumps(
                {"transactions": ynab_conversions.to_ynab(account_id, transactions)}
            ),
            budget_id=self.ynab._budget.id,
            account_id=None,
        )


class YnabApi:
    BASE_URL = "https://api.ynab.com/v1"

    def __init__(self, token: str):
        self.session = requests.Session()
        self.session.headers = {
            "Authorization": "Bearer {}".format(token),
            "Content-Type": "application/json",
        }

        endpoints = (
            UserEndpoint,
            BudgetsEndpoint,
            AccountsEndpoint,
            TransactionsEndpoint,
        )

        for endpoint in endpoints:
            attr_name = endpoint.__name__.removesuffix("Endpoint").lower()
            setattr(self, attr_name, endpoint(self.BASE_URL, self))

        r = self.user.get(handle_response=False)
        if r.status_code != 200:
            raise ValueError("Invalid token")

        budget = self.budgets.get()["budgets"][0]
        self.budget = NameIdPair(budget["name"], budget["id"])

    @property
    def budget(self):
        return self._budget.name

    @budget.setter
    def budget(self, budget: str | NameIdPair):
        if type(budget) == str:
            budget = NameIdPair(budget, self.resolve_budget(budget))

        self._budget = budget
        logging.info("budget set to {}".format(dataclasses.astuple(self._budget)))

    # Utils

    def resolve_budget(self, budget_name):
        for budget in self.budgets.get()["budgets"]:
            if budget["name"] == budget_name:
                return budget["id"]

        raise ValueError("Invalid budget: {}".format(budget_name))

    def resolve_account(self, account_name):
        for account in self.accounts.get()["accounts"]:
            if account["name"] == account_name:
                return account["id"]

        raise ValueError("Invalid account: {}".format(account_name))
