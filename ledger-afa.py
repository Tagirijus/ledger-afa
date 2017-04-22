# coding=utf-8

"""
A program for calculating and displaying tax deprecation on specified items
in a ledger journal. (OLD VERSION)

This script will only work, if there are only TWO accounts in the afa
transaction at the end of a ARGUMENTS.year: the one which will apply to the
tax reduction afa list and the one from which it comes (inventory of the
business). Example:

2016-12-31 * (a99) New NTG3 microphone
  afa-tax-reduction:Microphones  $ 100,00
  inventory:NTG3 microphone
"""

import argparse
import datetime
import ledger
import re
import tabulate

from ledger import Amount

# afa relevant account, month and day, decimal seperator
AFA_ACCOUNT = 'AfA'
MONTH = 12
DAY = 31
DEC_SEP = ','

# color coding
WHITE = '\033[97m'
PURPLE = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
CYAN = '\033[96m'
BOLD = '\033[1m'
DIM = '\033[2m'
GREY = '\033[90m'
UNDERLINE = '\033[4m'
E = '\033[0m'


class LedgerClass(object):
    """Holds the ledger journal and can query it."""

    def __init__(self, journal):
        """First parameter has to be a ledger journal."""
        self.journal = journal

    def query_total(self, query):
        """Compute total of queried posts"""
        return sum(post.amount for post in self.journal.query(query))


class SingleAfaTransaction(object):
    """A single tax reducing afa transaction."""

    def __init__(
        self,
        transaction,
        account_name,
        journal,
        year=datetime.datetime.now().year
    ):
        """Initialize the class object."""
        self.transaction = transaction
        self.account = self.calculate_account(account_name)

        self.buy_date = datetime.datetime.now()
        self.calculate_date(journal)

        self.total_costs = Amount(0)
        self.costs_begin = Amount(0)
        self.costs_end = Amount(0)
        self.calculate_costs(journal, year)

    def calculate_costs(self, journal, year):
        """
        Calculate the costs for the transaction.

        Get the total costs, costs at the end of the last year
        and the costs at the end of the current year.
        """
        # get total costs (buy date amount)
        query = '-l "a>0" -p "{}" "{}" and "#{}" and @"{}"'.format(
            self.buy_date.strftime('%Y-%m-%d'),
            self.account,
            self.transaction.code,
            self.transaction.payee
        )
        self.total_costs = journal.query_total(query)

        # get costs_begin = amount for that account last year
        query = '-p "to {}-{}-{}" "{}" and "#{}" and @"{}"'.format(
            str(year),
            str(MONTH),
            str(DAY),
            self.account,
            self.transaction.code,
            self.transaction.payee
        )
        self.costs_begin = journal.query_total(query)

        # get costs_end = at end of the given year
        query = '-p "to {}" "{}" and "#{}" and @"{}"'.format(
            str(year + 1),
            self.account,
            self.transaction.code,
            self.transaction.payee
        )
        self.costs_end = journal.query_total(query)

    def calculate_date(self, journal):
        """Find buy date."""
        # FIXME: Find the minimum date for the transaction with the same
        #        transaction code. This is probably not very robust.
        transactions = journal.journal.xacts()
        self.buy_date = min(t.date for t in transactions
                            if t.code == self.transaction.code)

    def calculate_account(self, default):
        """Get the account name of the inventory account."""
        # the inventory account is distinguished by negative balance
        for post in self.transaction.posts():
            if post.amount < 0:
                return post.account.fullname()

        return default

    def costs_diff(self):
        """Calculate the difference between costs_beginn and costs_end."""
        return self.costs_begin - self.costs_end

    def __str__(self):
        """Return a string of the object."""
        return '{} ({}={})'.format(
            self.transaction.payee,
            self.date_this_year.strftime('%Y-%m-%d'),
            self.buy_date.strftime('%Y-%m-%d')
        )


class AfaTransactions(object):
    """Holds all AfaTransaction-Objects."""

    def __init__(self, journal, account, year):
        """Initialize the class."""
        self.journal = journal
        self.account = account
        self.year = year
        self.transactions = self.get_afa_accounts()

    def get_afa_accounts(self):
        """Search all transactions, which are afa compliant."""
        # FIXME: Refactor this to make it readable.
        out = []
        transactions = self.journal.journal.xacts()
        for trans in transactions:
            # get transactions done this year (aux date of afa trans!)
            # and those who HAVE a code
            this_year = datetime.date(self.year, MONTH, DAY)
            if trans.date == this_year and trans.code:
                for post in trans.posts():
                    name = post.account.fullname()

                    matches = re.match(self.account, name, re.IGNORECASE)
                    amount_positive = post.amount > 0
                    exists = (trans.code + trans.payee in [t.transaction.code + t.transaction.payee for t in out])

                    if matches and amount_positive and not exists:
                        tx = SingleAfaTransaction(
                            trans,
                            name,
                            self.journal,
                            self.year,
                        )
                        out.append(tx)
        return out

    def add_table_entry(
        self,
        date='',
        code='',
        item='',
        account='',
        costs='',
        costs_begin='',
        costs_diff='',
        costs_end=''
    ):
        """Output two tabulate compliant table lines."""
        line_a = [
            unicode(date, 'utf-8'),
            YELLOW + unicode(code, 'utf-8') + E,
            BOLD + unicode(item, 'utf-8') + E,
            RED + unicode(costs, 'utf-8') + E,
            WHITE + unicode(costs_begin, 'utf-8') + E,
            CYAN + unicode(costs_diff, 'utf-8') + E,
            WHITE + unicode(costs_end, 'utf-8') + E
        ]
        line_b = [
            '',
            '',
            PURPLE + unicode('   ' + account, 'utf-8') + E,
            '',
            '',
            '',
            ''
        ]
        return [line_a, line_b]

    def output(self):
        """Print the afa transactions on the output."""
        # init the header for the table
        header = [
            UNDERLINE + BOLD + BLUE + 'Kaufdatum',
            'Beleg-Nr.',
            unicode('Gerät + Konto', 'utf-8'),
            'Kaufpreis',
            'Buchwert Anfang',
            'Buchwert Diff',
            'Buchwert Ende' + E
        ]

        # init the table
        table = [header]

        # init the variables for the output
        sum_costs = Amount('0,00')
        sum_begin = Amount('0,00')
        sum_diff = Amount('0,00')
        sum_end = Amount('0,00')

        # get variables from transaction list
        for x in sorted(self.transactions, key=lambda y: y.buy_date):
            table.extend(self.add_table_entry(
                str(x.buy_date.strftime('%Y-%m-%d')),
                x.transaction.code,
                x.transaction.payee,
                str(x.account),
                str(x.total_costs),
                str(x.costs_begin),
                str(x.costs_diff()),
                str(x.costs_end))
            )
            sum_costs += x.total_costs
            sum_begin += x.costs_begin
            sum_diff += x.costs_diff()
            sum_end += x.costs_end

        table.extend(self.add_table_entry())
        table.extend(self.add_table_entry(
            item='Summen:',
            costs=str(sum_costs),
            costs_begin=str(sum_begin),
            costs_diff=str(sum_diff),
            costs_end=str(sum_end))
        )

        print(tabulate.tabulate(table, tablefmt='plain'))


def main():
    # set up the arguments
    ap = argparse.ArgumentParser(
        description='Programm for calculating and summing up tax reduction'
        ' inventory purchases.'
    )

    ap.add_argument(
        'file',
        help='a ledger journal'
    )
    ap.add_argument(
        '-y',
        '--year',
        type=int,
        default=datetime.datetime.now().year,
        help='year for calculation'
    )
    ap.add_argument(
        '-a',
        '--account',
        default=AFA_ACCOUNT,
        help='afa account'
    )

    ARGUMENTS = ap.parse_args()

    journal = LedgerClass(ledger.read_journal(ARGUMENTS.file))

    AFA = AfaTransactions(journal, ARGUMENTS.account, ARGUMENTS.year)

    # get spicy output, baby!
    AFA.output()

if __name__ == '__main__':
    main()
