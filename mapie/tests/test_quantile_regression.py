from __future__ import annotations

from typing import Any, Tuple

import pytest
import numpy as np
from sklearn.datasets import make_regression
from sklearn.linear_model import QuantileRegressor
from sklearn.model_selection import KFold, LeaveOneOut
from sklearn.utils.validation import check_is_fitted
from typing_extensions import TypedDict
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.base import RegressorMixin, clone, BaseEstimator
from inspect import signature

from mapie._typing import NDArray
from mapie.metrics import regression_coverage_score
from mapie.quantile_regression import MapieQuantileRegressor


X_toy = np.array(
    [0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4, 5, 0, 1, 2, 3, 4,
     5, 0, 1, 2, 3, 4, 5]
).reshape(-1, 1)
y_toy = np.array(
    [5, 7, 9, 11, 13, 15, 5, 7, 9, 11, 13, 15, 5, 7, 9,
     11, 13, 15, 5, 7, 9, 11, 13, 15]
)

random_state = 1

X_train_toy, X_calib_toy, y_train_toy, y_calib_toy = train_test_split(
    X_toy,
    y_toy,
    test_size=0.5,
    random_state=random_state
)

qt = QuantileRegressor(solver='highs')
gb = GradientBoostingRegressor(
            loss="quantile",
            random_state=random_state
            )

X, y = make_regression(
    n_samples=500,
    n_features=10,
    noise=1.0,
    random_state=random_state
    )
X_train, X_calib, y_train, y_calib = train_test_split(
    X,
    y,
    test_size=0.5,
    random_state=random_state
)

SYMMETRY = [True, False]
ESTIMATOR = [qt, gb]


Params = TypedDict(
    "Params",
    {
        "method": str,
        "alpha": float,
    },
)

STRATEGIES = {
    "quantile_alpha2": Params(method="quantile", alpha=0.2),
    "quantile_alpha3": Params(method="quantile", alpha=0.3),
    "quantile_alpha4": Params(method="quantile", alpha=0.4),
    }

WIDTHS = {
    "quantile_alpha2": 368.4755759683198,
    "quantile_alpha3": 319.487008615549,
    "quantile_alpha4": 284.56158261736726,
}

COVERAGES = {
    "quantile_alpha2": 0.786,
    "quantile_alpha3": 0.71,
    "quantile_alpha4": 0.628,
}


class NotFitPredictEstimator:

    def __init__(self, alpha):
        self.alpha = alpha


class NoLossPamametroEstimator(BaseEstimator):
    def __init__(self, alpha):
        self.alpha = alpha

    def fit(self, *args: Any) -> None:
        """Dummy fit."""

    def predict(self, *args: Any) -> None:
        """Dummy predict."""


class NoAlphaPamametroEstimator(BaseEstimator):
    def __init__(self, alpha, loss):
        self.alpha = alpha
        self.loss = loss

    def fit(self, *args: Any) -> None:
        """Dummy fit."""

    def predict(self, *args: Any) -> None:
        """Dummy predict."""


def test_default_parameters() -> None:
    """Test default values of input parameters."""
    mapie_reg = MapieQuantileRegressor()
    assert mapie_reg.method == "quantile"
    assert mapie_reg.cv is None
    assert mapie_reg.alpha == 0.1


def test_default_sample_weight() -> None:
    """Test default sample weights."""
    mapie_reg = MapieQuantileRegressor()
    assert (
        signature(mapie_reg.fit).parameters["sample_weight"].default
        is None
    )


def test_default_parameters_estimator() -> None:
    """Test default values of estimator."""
    mapie_reg = MapieQuantileRegressor()
    mapie_reg.fit(X_train, y_train, X_calib, y_calib)
    for estimator in mapie_reg.estimators_:
        assert isinstance(estimator, QuantileRegressor)
        assert estimator.__dict__["solver"] == "highs"


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_valid_estimator(strategy: str) -> None:
    """Test that valid estimators are not corrupted, for all strategies."""
    mapie_reg = MapieQuantileRegressor(
        estimator=qt,
        **STRATEGIES[strategy]
        )
    mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)
    for estimator in mapie_reg.estimators_:
        assert isinstance(estimator, QuantileRegressor)


def test_no_predict_fit_estimator() -> None:
    """Test that valid estimators are not corrupted, for all strategies."""
    with pytest.raises(
        ValueError,
        match=r".*Invalid estimator.*",
    ):
        mapie_reg = MapieQuantileRegressor(
            estimator=NotFitPredictEstimator(alpha=0.2)
            )
        mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


def test_no_para_loss_estimator() -> None:
    """Test to check when it does not have a valid alpha parameter name"""
    Params = TypedDict(
        "Params",
        {
            "loss_name": str,
            "alpha_name": str
        },
    )
    with pytest.raises(
        ValueError,
        match=r".*The matching parameter loss_name*",
    ):
        mapie_reg = MapieQuantileRegressor()
        mapie_reg.quantile_estimator_params[
            "NoLossPamametroEstimator"
        ] = Params(
            loss_name="noloss",
            alpha_name="notalpha"
        )
        mapie_reg.estimator = NoLossPamametroEstimator(
            alpha=0.2
            )
        mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


def test_no_para_alpha_estimator() -> None:
    """Test to check when it does not have a valid alpha parameter name"""
    Params = TypedDict(
        "Params",
        {
            "loss_name": str,
            "alpha_name": str
        },
    )
    with pytest.raises(
        ValueError,
        match=r".*The matching parameter alpha_name*",
    ):
        mapie_reg = MapieQuantileRegressor()
        mapie_reg.quantile_estimator_params[
            "NoAlphaPamametroEstimator"
        ] = Params(
            loss_name="loss",
            alpha_name="notalpha"
        )
        mapie_reg.estimator = NoAlphaPamametroEstimator(
            alpha=0.2,
            loss="quantile"
            )
        mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
@pytest.mark.parametrize("estimator", ESTIMATOR)
def test_valid_method(strategy: str, estimator: RegressorMixin) -> None:
    """Test that valid strategies and estimators raise no error"""
    mapie_reg = MapieQuantileRegressor(
        estimator=estimator,
        **STRATEGIES[strategy]
        )
    mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)
    check_is_fitted(mapie_reg, mapie_reg.fit_attributes)
    assert mapie_reg.__dict__["method"] == "quantile"


@pytest.mark.parametrize("strategy", [*STRATEGIES])
@pytest.mark.parametrize("estimator", ESTIMATOR)
@pytest.mark.parametrize("dataset", [
        (X_train, X_calib, y_train, y_calib),
        (X_train_toy, X_calib_toy, y_train_toy, y_calib_toy)
    ]
)
@pytest.mark.parametrize("symmetry", SYMMETRY)
def test_predict_output_shape(
    strategy: str,
    estimator: RegressorMixin,
    dataset: Tuple[NDArray, NDArray, NDArray, NDArray],
    symmetry: bool
) -> None:
    """Test predict output shape."""
    mapie_reg = MapieQuantileRegressor(
        estimator=estimator,
        **STRATEGIES[strategy]
        )
    (X_t, X_c, y_t, y_c) = dataset
    mapie_reg.fit(X_t, y_t, X_c, y_c)
    y_pred, y_pis = mapie_reg.predict(X_t, symmetry=symmetry)
    assert y_pred.shape == (X_t.shape[0],)
    assert y_pis[:, 0, 0].shape == (X_t.shape[0],)
    assert y_pis[:, 1, 0].shape == (X_t.shape[0],)


@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_results_with_constant_sample_weights(
    strategy: str,
) -> None:
    """
    Test predictions when sample weights are None
    or constant with different values.
    """
    n_samples = len(X_train)
    mapie0 = MapieQuantileRegressor(
        estimator=qt,
        **STRATEGIES[strategy]
        )
    mapie1 = MapieQuantileRegressor(
        estimator=qt,
        **STRATEGIES[strategy]
        )
    mapie2 = MapieQuantileRegressor(
        estimator=qt,
        **STRATEGIES[strategy]
        )
    mapie0.fit(
        X_train, y_train, X_calib, y_calib,
        sample_weight=None
        )
    mapie1.fit(
        X_train, y_train, X_calib, y_calib,
        sample_weight=np.ones(shape=n_samples)
        )
    mapie2.fit(
        X_train, y_train, X_calib, y_calib,
        sample_weight=np.ones(shape=n_samples) * 5
        )

    np.testing.assert_allclose(
        mapie0.conformity_scores_,
        mapie1.conformity_scores_
    )
    np.testing.assert_allclose(
        mapie0.conformity_scores_,
        mapie2.conformity_scores_
    )

    y_pred0, y_pis0 = mapie0.predict(X)
    y_pred1, y_pis1 = mapie1.predict(X)
    y_pred2, y_pis2 = mapie2.predict(X)
    np.testing.assert_allclose(y_pred0, y_pred1)
    np.testing.assert_allclose(y_pred1, y_pred2)
    np.testing.assert_allclose(y_pis0, y_pis1)
    np.testing.assert_allclose(y_pis1, y_pis2)


@pytest.mark.parametrize("estimator", ESTIMATOR)
@pytest.mark.parametrize("symmetry", SYMMETRY)
def test_results_for_same_alpha(
    estimator: RegressorMixin,
    symmetry: bool
) -> None:
    """
    Test that predictions and intervals
    are similar with two equal values of alpha.
    """
    mapie_reg = MapieQuantileRegressor(
        estimator=estimator,
        alpha=0.2
    )
    mapie_red_clone = clone(mapie_reg)
    mapie_reg.fit(X_train, y_train, X_calib, y_calib)
    mapie_red_clone.fit(X_train, y_train, X_calib, y_calib)
    y_pred, y_pis = mapie_reg.predict(X, symmetry=symmetry)
    y_pred_clone, y_pis_clone = mapie_reg.predict(X, symmetry=symmetry)
    np.testing.assert_allclose(y_pred, y_pred_clone)
    np.testing.assert_allclose(y_pis[:, 0, 0], y_pis_clone[:, 0, 0])
    np.testing.assert_allclose(y_pis[:, 1, 0], y_pis_clone[:, 1, 0])


@pytest.mark.parametrize("alphas", ["hello", MapieQuantileRegressor, [2], 1])
def test_wrong_alphas_types(alphas: float) -> None:
    """Checking for wrong type of alphas"""
    with pytest.raises(
        ValueError,
        match=r".*Invalid alpha. Allowed values are float.*",
    ):
        mapie_reg = MapieQuantileRegressor(alpha=alphas)
        mapie_reg.fit(X_train, y_train, X_calib, y_calib)


@pytest.mark.parametrize("alphas", [0.5, 0.6, 0.95, 5.0, -0.1, -0.001, -10.0])
def test_wrong_alphas(alphas: float) -> None:
    """Checking for alphas values that are too big according to all value."""
    with pytest.raises(
        ValueError,
        match=r".*Invalid alpha. Allowed values are between 0 and 0.5.*",
    ):
        mapie_reg = MapieQuantileRegressor(alpha=alphas)
        mapie_reg.fit(X_train, y_train, X_calib, y_calib)


def test_estimators_quantile_function() -> None:
    """Checking for badly set estimator parameters."""
    with pytest.raises(
        ValueError,
        match=r".*You need to set the loss/objective*",
    ):
        mapie_reg = MapieQuantileRegressor(
            estimator=GradientBoostingRegressor()
            )
        mapie_reg.fit(X_train, y_train, X_calib, y_calib)


@pytest.mark.parametrize("cv", [-1, 2, KFold(), LeaveOneOut()])
def test_invalid_cv(cv: Any) -> None:
    """Test that valid cv raise errors."""
    with pytest.raises(
        ValueError,
        match=r".*Invalid cv method.*",
    ):
        mapie = MapieQuantileRegressor(cv=cv)
        mapie.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


@pytest.mark.parametrize("cv", [None, "split"])
def test_valid_cv(cv: Any) -> None:
    """Test that valid cv raise no errors."""
    mapie = MapieQuantileRegressor(cv=cv)
    mapie.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


def test_estimators_not_in_list() -> None:
    """
    Test for estimators that are not in the list, hence not accepted
    estimators
    """
    with pytest.raises(
        ValueError,
        match=r".*The base model does not seem to be accepted by.*",
    ):
        mapie_reg = MapieQuantileRegressor(estimator=RandomForestClassifier())
        mapie_reg.fit(X_train_toy, y_train_toy, X_calib_toy, y_calib_toy)


def test_for_small_dataset() -> None:
    """Test for when we have calibration datasets that are too small."""
    with pytest.raises(
        ValueError,
        match=r".*Number of samples of the score is too low*",
    ):
        mapie_reg = MapieQuantileRegressor(
            estimator=qt,
            alpha=0.1
        )
        mapie_reg.fit(
            np.array([1, 2, 3]),
            np.array([2, 2, 3]),
            np.array([3, 5]),
            np.array([2, 3])
        )


@pytest.mark.parametrize("strategy", [*STRATEGIES])
@pytest.mark.parametrize("estimator", ESTIMATOR)
@pytest.mark.parametrize("dataset", [
    (X_train, X_calib, y_train, y_calib),
    (X_train_toy, X_calib_toy, y_train_toy, y_calib_toy)
])
def test_conformity_len(
    strategy: str,
    estimator: RegressorMixin,
    dataset: Tuple[NDArray, NDArray, NDArray, NDArray],
) -> None:
    """Test conformity scores output shape."""
    (X_t, X_c, y_t, y_c) = dataset
    n_samples = int(len(X_c))
    mapie_regressor = MapieQuantileRegressor(
        estimator=estimator,
        **STRATEGIES[strategy]
        )
    mapie_regressor.fit(X_t, y_t, X_c, y_c)
    assert mapie_regressor.conformity_scores_[0].shape[0] == n_samples


# Working but want to add both symmetry and different estimators
@pytest.mark.parametrize("strategy", [*STRATEGIES])
def test_linear_regression_results(strategy: str) -> None:
    """
    Test expected prediction intervals for
    a different strategies.
    """
    mapie = MapieQuantileRegressor(**STRATEGIES[strategy])
    mapie.fit(X_train, y_train, X_calib, y_calib)
    _, y_pis = mapie.predict(X)
    y_pred_low, y_pred_up = y_pis[:, 0, 0], y_pis[:, 1, 0]
    width_mean = (y_pred_up - y_pred_low).mean()
    coverage = regression_coverage_score(y, y_pred_low, y_pred_up)
    np.testing.assert_allclose(width_mean, WIDTHS[strategy], rtol=1e-2)
    np.testing.assert_allclose(coverage, COVERAGES[strategy], rtol=1e-2)


# # Dosen't work just yet, need to set it as a warning
# @pytest.mark.parametrize("strategy", [*STRATEGIES])
# @pytest.mark.parametrize("estimator", ESTIMATOR)
# @pytest.mark.parametrize("dataset", [(X, y), (X_toy, y_toy)])
# @pytest.mark.parametrize("symmetry", SYMMETRY)
# def test_prediction_between_low_up(
#     strategy: str,
#     estimator: RegressorMixin,
#     dataset: Tuple[NDArray, NDArray],
#     symmetry: bool
# ) -> None:
#     """
#     Test that MapieRegressor applied on a linear regression model
#     fitted on a linear curve results in null uncertainty.
#     """
#     mapie = MapieQuantileRegressor(
#         estimator=estimator,
#         **STRATEGIES[strategy]
#         )
#     (X, y) = dataset
#     mapie.fit(X, y)
#     y_pred, y_pis = mapie.predict(X, symmetry=symmetry)
#     assert (y_pis[:, 1, 0] >= y_pis[:, 0, 0]).all()
#     assert (y_pred >= y_pis[:, 0, 0]).all()
#     assert (y_pred <= y_pis[:, 1, 0]).all()
