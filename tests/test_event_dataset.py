# Test that the event dataset works correctly.
import sys
sys.path += ['.']
from func_adl import EventDataset, EventDatasetURLException

def test_good_file_url_bad_form():
    e = EventDataset('file://test.root')
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///test.root'

def test_good_file_url_good_form():
    e = EventDataset('file:///test.root')
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///test.root'

def test_good_file_url_good_form_with_subdir():
    e = EventDataset('file:///sub/test.root')
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///sub/test.root'

def test_good_file_url_bad_form_with_subdir():
    e = EventDataset('file://sub/test.root')
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///sub/test.root'

def test_good_file_url_good_form_with_host_local():
    e = EventDataset('file://localhost/test.root')
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///test.root'

# TODO:
# These are both illegal for us, but I don't know how to detect them without some weird
# heuristics and also deal with malformed urls like file://path.
# def test_good_file_url_good_form_with_host_dns():
#     try:
#         EventDataset('file://www.nytimes.com/test.root')
#         assert False
#     except EventDatasetURLException:
#         return

# def test_good_file_url_good_form_with_host_ip():
#     try:
#         EventDataset('file://192.168.1.23/test.root')
#         assert False
#     except EventDatasetURLException:
#         return

def test_good_grid_url():
    _ = EventDataset('gridds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795')

def test_good_local_grid_ds_url():
    _ = EventDataset('localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795')

def test_good_url_with_options():
    'Note - these options are not necessarily valid!'
    _ = EventDataset('localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795&nfiles=1')

def test_good_local_file_url():
    e = EventDataset(['file://test.root'])
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///test.root'

def test_good_local_file_urls():
    e = EventDataset(['file://test1.root', 'file://test2.root'])
    assert e.url is not None
    assert len(e.url) == 2
    assert e.url[0] == 'file:///test1.root'
    assert e.url[1] == 'file:///test2.root'

def test_root_good_file_urls():
    e = EventDataset(['file:///data/test.root'])
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'file:///data/test.root'

def test_good_grid_urls():
    e = EventDataset(['gridds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795'])
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'gridds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795'

def test_good_local_grid_ds_urls():
    e = EventDataset(['localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795'])
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795'

def test_good_urls_with_options():
    'Note - these options are not necessarily valid!'
    e = EventDataset(['localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795&nfiles=1'])
    assert e.url is not None
    assert len(e.url) == 1
    assert e.url[0] == 'localds://mc16_13TeV.311309.MadGraphPythia8EvtGen_A14NNPDF31LO_HSS_LLP_mH125_mS5_ltlow.deriv.DAOD_EXOT15.e7270_e5984_s3234_r10201_r10210_p3795&nfiles=1'

def test_bad_url_noscheme():
    try:
        _ = EventDataset('holyforkingshirtballs.root')
    except:
        return
    assert False

def test_bad_url_nofile():
    try:
        _ = EventDataset('localds://')
    except:
        return
    assert False

def test_bad_urls():
    try:
        _ = EventDataset(['file://data.root', 'holyforkingshirtballs.root'])
    except:
        return
    assert False

def test_empty_url():
    try:
        _ = EventDataset('')
    except:
        return
    assert False

def test_empty_urls():
    try:
        _ = EventDataset([])
    except:
        return
    assert False

def test_EDS_pickle():
    import pickle

    b = pickle.dumps(EventDataset("file://root.root"))
    o = pickle.loads(b)

    assert len(o.url) == 1