from ynab_defs import Transaction

import dataclasses


def to_ynab(account_id: str, transactions: list[Transaction]) -> list[dict]:
    ret_transactions = []
    for t in transactions:
        dict_transaction = dataclasses.asdict(t)
        dict_transaction["account_id"] = account_id
        dict_transaction["date"] = dict_transaction["date"].strftime("%Y-%m-%d")
        dict_transaction["payee_name"] = dict_transaction.pop("payee")
        dict_transaction["amount"] *= 10
        ret_transactions.append(dict_transaction)

    return ret_transactions
