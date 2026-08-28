from features.builder import build_feature_frame
from features.feast_store import prepare_feast_repo
from features.registry import FEATURE_LIST


def test_prepare_feast_repo_creates_local_store(fake_candles, tmp_path):
    source = fake_candles.assign(symbol="BTCUSDT")
    features = build_feature_frame(source)

    store = prepare_feast_repo(features, tmp_path)

    assert store is not None
    assert (tmp_path / "feature_store.yaml").exists()
    assert (tmp_path / "data" / "features.parquet").exists()
    assert len(FEATURE_LIST) == 50
