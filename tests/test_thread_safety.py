import concurrent.futures
import textwrap

from trnsystor.deck import Deck

components_string = textwrap.dedent(
    r"""
    UNIT 3 TYPE  11 Tee Piece
    *$UNIT_NAME Tee Piece
    *$MODEL tests\input_files\Type11h.xml
    *$POSITION 50.0 50.0
    *$LAYER Main
    PARAMETERS 1
    1  ! 1 Tee piece mode
    INPUTS 4
    0,0  ! [unconnected] Tee Piece:Temperature at inlet 1
    flowRateDoubled  ! double:flowRateDoubled -> Tee Piece:Flow rate at inlet 1
    0,0  ! [unconnected] Tee Piece:Temperature at inlet 2
    0,0  ! [unconnected] Tee Piece:Flow rate at inlet 2
    *** INITIAL INPUT VALUES
    20   ! Temperature at inlet 1
    100  ! Flow rate at inlet 1
    20   ! Temperature at inlet 2
    100  ! Flow rate at inlet 2

    * EQUATIONS "double"
    *
    EQUATIONS 1
    flowRateDoubled  =  2*[1, 2]
    *$UNIT_NAME double
    *$LAYER Main
    *$POSITION 50.0 50.0
    *$UNIT_NUMBER 2
    """
)

def _parse():
    dck = Deck.loads(components_string, proforma_root="tests/input_files")
    return len(dck.models)

def test_load_is_thread_safe():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda _: _parse(), range(8)))
    assert all(r == 2 for r in results)
