import ledger
import pytest

from glob import glob


ledger_files = glob('tests/data/*.journal')


@pytest.fixture(params=ledger_files)
def filename(request):
    return request.param


# FIXME: we can only read a journal once per program run (session)
#        try `beancount` and see if that can reset sessions and has a usable API
@pytest.fixture(scope="session")
def journal():
    return ledger.read_journal('tests/data/single_transaction.journal')
