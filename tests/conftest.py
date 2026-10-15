import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('MPLBACKEND','Agg')
import pytest
from micrograno.sinteticos import crear_conjunto

@pytest.fixture
def conjunto():
    return crear_conjunto()
