# coding=utf-8

import argparse
import colorama
import ledger
import tabulate

from datetime import date
from termcolor import colored


def get_sub_accounts(account):
    top = [a for a in account.accounts()]
    sub = [a for acc in account.accounts() for a in get_sub_accounts(acc)]
    return top + sub


def get_afa_posts(journal, account, year):
    """
    get all postings that went to afa accounts this year.

    this way we can trace back inventory items which are being deprecated.
    """
    top = journal.find_account_re(account)

    if top is None:
        raise ValueError("Konto nicht gefunden: {}".format(account))

    accounts = [top] + get_sub_accounts(top)
    return [p for a in accounts for p in a.posts()
            if p.date.year == year]


def get_inventory(posts):
    """
    get accounts for inventory items which are being deprecated.

    this is done looking at each deprecation post and taking all
    other accounts in the transaction of that post.
    """

    # monkey patch so we can use `Account` in `set`
    ledger.Account.__hash__ = lambda self: hash(self.fullname())
    ledger.Account.__eq__ = lambda self, other: self.fullname() == other.fullname()

    inventory = set()
    for post in posts:
        # other accounts from the parent transaction of this posting
        inventory |= set((p.account, p.xact) for p in post.xact.posts()
                         if p.account.fullname() != post.account.fullname())

    return inventory


def table_entry(
    date='',
    code='',
    item='',
    total_value='',
    last_year_value='',
    deprecation_amount='',
    next_year_value=''
):
    return [
        date,
        colored(code, 'yellow'),
        item,
        colored(str(total_value), 'red'),
        str(last_year_value),
        colored(str(deprecation_amount), 'cyan'),
        str(next_year_value),
    ]


def create_table(items, year):
    colorama.init()  # needed only for windows terminal color support

    def color_header(s):
        return colored(s, attrs=['bold'])

    def color_footer(s):
        return colored(s, attrs=['bold'])

    header = [
        'Kaufdatum',
        'Beleg',
        'Gerät',
        'Kaufpreis',
        'Buchwert {}'.format(year - 1),
        'Abschreibung',
        'Buchwert {}'.format(year),
    ]

    table = [map(color_header, header)]

    sum_total_value = sum(i.total_value for i in items)
    sum_last_year_value = sum(i.last_year_value for i in items)
    sum_deprecation_amount = sum(i.deprecation_amount for i in items)
    sum_next_year_value = sum(i.next_year_value for i in items)

    for x in sorted(items, key=lambda y: y.buy_date):
        line = table_entry(
            x.buy_date.isoformat(),
            x.code,
            x.item,
            x.total_value,
            x.last_year_value,
            x.deprecation_amount,
            x.next_year_value,
        )
        table.append(line)

    footer = table_entry(
        item='Gesamt',
        total_value=sum_total_value,
        last_year_value=sum_last_year_value,
        deprecation_amount=sum_deprecation_amount,
        next_year_value=sum_next_year_value,
    )

    table.append(map(color_footer, footer))

    table = [map(lambda s: s.decode('utf-8'), row) for row in table]

    return table


class InventoryItem(object):
    def __init__(self, account, xact, year):
        self.code = xact.code

        self.item = account.name
        self.account = account.fullname()
        self.year = year

        self.buy_date = min(p.date for p in account.posts()
                            if p.xact.code == self.code)

        # get first_post to match code and lowest date
        first_post = [post for post in account.posts()
                      if post.xact.code == self.code and
                      post.date == self.buy_date and post.amount > 0]

        # get the only entry in first_post
        try:
            first_post, = first_post
        except ValueError as e:
            print(e.message)

        # for the total_value get account which paid the inventory item
        #  -> its transaction has to be on buy_date
        #  -> its code has to be self.code
        #  -> its amount has to be < 0
        #  -> its not the inventory account itself
        self.total_value = sum(abs(p.amount) for p in account.posts()
                               for pn in p.xact.posts()
                               if p.date == self.buy_date
                               and p.xact.code == self.code
                               and pn.amount < 0
                               and p.id != pn.id)

        self.last_year_value = sum(p.amount for p in account.posts()
                                   if (p.date.year < year and
                                       p.xact.code == self.code)
                                   # consider additional purchases in current year
                                   or (p.date.year == year and p.amount > 0
                                       and p.xact.code == self.code)
                                   )

        self.next_year_value = sum(p.amount for p in account.posts()
                                   if p.date.year <= year and
                                   p.xact.code == self.code
                                   )

        self.deprecation_amount = sum(p.amount for p in account.posts()
                                      if p.date.year == year
                                      and p.id != first_post.id
                                      # only consider deprecation
                                      and p.amount < 0 and
                                      p.xact.code == self.code
                                      )


def main():
    args = argparse.ArgumentParser(
        description=('Ein Programm zur Berechnung und Anzeige der Abschreibung '
                     'für Abnutzung (AfA) auf Grundlage eines ledger Journals.')
    )
    args.add_argument(
        'file',
        help='ledger Journal'
    )
    args.add_argument(
        '-j',
        '--jahr',
        type=int,
        default=date.today().year,
        help='Jahr der Berechnung'
    )
    args.add_argument(
        '-k',
        '--konto',
        default='AfA',
        help='Konto für AfA'
    )

    args = args.parse_args()

    try:
        journal = ledger.read_journal(args.file)
        posts = get_afa_posts(journal, args.konto, args.jahr)
        inventory = [InventoryItem(a, x, args.jahr) for a, x in get_inventory(posts)]
        table = create_table(inventory, args.jahr)
        print(tabulate.tabulate(table, tablefmt='plain'))
    except ValueError as e:
        print(e.message)

if __name__ == '__main__':
    main()
