from abc import ABC, abstractmethod
import csv
import dataclasses
from dataclasses import dataclass
import datetime


@dataclass
class Transaction(ABC):
    date: datetime.datetime
    payee: str
    memo: str
    amount: int

    def __eq__(self, other) -> bool:
        return (
            abs(self.date - other.date) < datetime.timedelta(days=2)
            and self.amount == other.amount
        )


class ParsedTransaction(Transaction):
    def __init__(self, data: list[str]):
        transaction_data = self.TransactionData(*data)
        attrs = [getattr(self, field.name) for field in dataclasses.fields(Transaction)]
        super().__init__(*map(lambda attr: attr(transaction_data), attrs))

    @abstractmethod
    def date(self, data):
        pass

    @abstractmethod
    def payee(self, data):
        pass

    @abstractmethod
    def memo(self, data):
        pass

    @abstractmethod
    def amount(self, data):
        pass

    @staticmethod
    def list_from(source):
        raise NotImplementedError()


class VenmoTransaction(ParsedTransaction):
    @dataclass
    class TransactionData:
        empty: str
        id: str
        datetime: str
        type: str
        status: str
        note: str
        from_: str
        to: str
        amount_total: str
        amount_tip: str
        amount_tax: str
        amount_fee: str
        amount_total: str
        tax_rate: str
        tax_exempt: str
        funding_source: str
        destination: str
        beginning_balance: str
        ending_balance: str
        statement_period_venmo_fees: str
        terminal_location: str
        year_to_date_venmo_fees: str
        disclaimer: str

    def __init__(self, raw):
        super().__init__(raw)

    def date(self, data):
        return datetime.datetime.strptime(
            data.datetime, "%Y-%m-%dT%H:%M:%S"
        ) + datetime.timedelta(hours=-4)

    def payee(self, data):
        if data.amount_total.startswith("+") ^ (data.type == "Charge"):
            return data.from_
        else:
            return data.to

    def memo(self, data):
        return data.note

    # amount_total: "+ $150.00"
    def amount(self, data):
        return int(data.amount_total.translate(str.maketrans("", "", "$ ,.")))

    @staticmethod
    def list_from(path):
        with open(path, "r") as file:
            reader = csv.reader(file)
            return [
                VenmoTransaction(row) for row in reader if row[1] and row[1] != "ID"
            ]


class YnabTransaction(ParsedTransaction):
    @dataclass
    class TransactionData:
        id: str
        date: str
        amount: str
        memo: str
        cleared: str
        approved: str
        flag_color: str
        account_id: str
        account_name: str
        payee_id: str
        payee_name: str
        category_id: str
        category_name: str
        transfer_account_id: str
        transfer_transaction_id: str
        matched_transaction_id: str
        import_id: str
        import_payee_name: str
        import_payee_name_original: str
        debt_transaction_type: str
        deleted: str
        subtransactions: str

    def __init__(self, raw):
        super().__init__(raw.values())

    def date(self, data):
        return datetime.datetime.strptime(data.date, "%Y-%m-%d")

    def payee(self, data):
        return data.payee_name

    def memo(self, data):
        return data.memo

    def amount(self, data):
        return int(data.amount / 10)

    @staticmethod
    def from_list(ynab_transactions):
        return [YnabTransaction(t) for t in ynab_transactions]


if __name__ == "__main__":
    raw = ",3750611336113345566,2023-03-03T20:35:12,Payment,Complete,👁️,Christine Esposito,Ben Esposito,+ $150.00,,0,,0,,,Venmo balance,,,,Venmo,,"
    print(VenmoTransaction(raw))
