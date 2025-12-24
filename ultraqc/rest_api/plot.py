"""
Plot generation utilities for the REST API.

NOTE: This module has been updated for FastAPI/SQLAlchemy 2.0 compatibility.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Collection, Iterable, Iterator, Optional, Tuple

import numpy
import numpy.typing as npt
from numpy import absolute, delete, take, zeros
from plotly.colors import DEFAULT_PLOTLY_COLORS
from scipy.stats import f, norm, zscore
from sklearn.covariance import EmpiricalCovariance
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from ultraqc.model import models
from ultraqc.model.models import Report, Sample, SampleData, SampleDataType
from ultraqc.rest_api.filters import build_filter_query


def rgb_to_rgba(rgb, alpha):
    """
    Appends an alpha (transparency) value to an RGB string.
    """
    match = re.match(r"rgb\((\d+), (\d+), (\d+)\)", rgb)
    return "rgba({}, {}, {}, {})".format(
        match.group(1), match.group(2), match.group(3), alpha
    )


def encode_to_numeric(y: Iterable, chunk_size: int) -> Iterable[numpy.ndarray]:
    encoder = OneHotEncoder()
    args = [iter(y)] * chunk_size
    for col in zip(*args):
        # Return numeric columns if possible, otherwise categorical
        try:
            yield numpy.asarray(col, float)
        except:
            yield encoder.fit_transform(
                numpy.asarray(col, dtype=numpy.object_).reshape(-1, 1)
            ).toarray()


def extract_query_data(
    query: Query, ncol: int
) -> Tuple[
    npt.NDArray[numpy.string_],
    npt.NDArray[numpy.string_],
    npt.NDArray[numpy.datetime64],
    npt.NDArray[numpy.float_],
]:
    data = query.all()
    names, data_types, x, y = zip(*data)
    y = numpy.column_stack(list(encode_to_numeric(y, len(y) // ncol)))
    nrow = len(x) // ncol
    return (
        numpy.array(names, dtype=str),
        numpy.array(data_types, dtype=str),
        numpy.array(x, dtype=datetime)[0:nrow],
        y,
    )


def univariate_trend_data(
    query: Any, fields: Sequence[str], plot_prefix: str, statistic_options: dict
) -> Iterator[dict]:
    """
    Returns the plot series for the "raw measurement" statistic.
    """
    center_line = statistic_options["center_line"]
    for field, colour in zip(fields, DEFAULT_PLOTLY_COLORS):
        # Fields can be specified either as type IDs, or as type names
        if field.isdigit():
            field_query = query.filter(
                models.SampleDataType.sample_data_type_id == field
            )
        else:
            field_query = query.filter(models.SampleDataType.data_key == field)

        names, data_types, x, all_y = extract_query_data(field_query, 1)
        for i, y in enumerate(all_y.T):
            # We are only considering 1 field at a time
            data_type = data_types[0]

            yield dict(
                id=f"{plot_prefix}_raw_{i}_{field}",
                type="scatter",
                text=names,
                hoverinfo="text+x+y",
                x=x,
                y=y,
                line=dict(color=colour),
                mode="markers",
                name=f"{data_type} Category {i} Samples",
            )

            # Add the mean
            if center_line == "mean":
                y2 = numpy.repeat(numpy.mean(y), len(x))
                yield dict(
                    id=f"{plot_prefix}_mean_{i}_{field}",
                    type="scatter",
                    x=x,
                    y=y2.tolist(),
                    line=dict(color=colour),
                    mode="lines",
                    name=f"{data_type} Category {i} Mean",
                )
            elif center_line == "median":
                y2 = numpy.repeat(numpy.median(y), len(x))
                yield dict(
                    id=f"{plot_prefix}_median_{i}_{field}",
                    type="scatter",
                    x=x,
                    y=y2.tolist(),
                    line=dict(color=colour),
                    mode="lines",
                    name=f"{data_type} Category {i} Median",
                )
            else:
                # The user could request control limits without a center line. Assume they
                # want a mean in this case
                y2 = numpy.repeat(numpy.mean(y), len(x))


# Parameters correspond to fields in
# `TrendInputSchema`
async def trend_data(
    session: AsyncSession,
    fields: Sequence[str],
    filter: Any,
    statistic: str,
    **kwargs
) -> Iterator[dict]:
    """
    Returns data suitable for a plotly plot.

    Args:
        session: Async database session
        fields: List of field names or IDs to plot
        filter: Filter criteria
        statistic: Type of statistic to compute ('measurement' or 'iforest')
        **kwargs: Additional arguments passed to the statistic function

    Returns:
        Iterator of plot data dictionaries
    """
    subquery = build_filter_query(filter)

    # Build the query using SQLAlchemy 2.0 style
    stmt = (
        select(
            Sample.sample_name,
            SampleDataType.nice_name,
            Report.created_at,
            SampleData.value,
        )
        .select_from(Sample)
        .outerjoin(SampleData, Sample.sample_id == SampleData.sample_id)
        .outerjoin(SampleDataType, SampleData.sample_data_type_id == SampleDataType.sample_data_type_id)
        .outerjoin(Report, Report.report_id == Sample.report_id)
        .where(Sample.sample_id.in_(subquery))
        .order_by(SampleDataType.sample_data_type_id)
        .distinct()
    )

    result = await session.execute(stmt)
    query_data = result.all()

    if statistic == "measurement":
        return univariate_trend_data(fields=fields, query_data=query_data, **kwargs)
    elif statistic == "iforest":
        return isolation_forest_trend(fields=fields, query_data=query_data, **kwargs)
    else:
        raise ValueError("Invalid transform!")


def maha_distance(y, alpha=0.05):
    cov = EmpiricalCovariance()
    # Calculate the distance according to T-square distribution
    cov.fit(y)
    distance = cov.mahalanobis(y)

    # Calculate the critical value according to the F distribution
    n, p = y.shape
    cri = f.isf(alpha, dfn=p, dfd=n - p)
    t = (p * (n - 1) / (n - p)) * cri

    return distance, t


def isolation_forest_trend(
    query: Any, fields: Sequence[str], plot_prefix: str, statistic_options: dict
) -> Iterator[dict]:
    """
    Yields plotly series for the "Isolation Forest" statistic.
    """
    # Fields can be specified either as type IDs, or as type names
    if fields[0].isdigit():
        query = query.filter(models.SampleDataType.sample_data_type_id.in_(fields))
    else:
        query = query.filter(models.SampleDataType.data_key.in_(fields))

    names, data_types, x, y = extract_query_data(query, len(fields))

    clf = IsolationForest(
        n_estimators=100, contamination=statistic_options["contamination"]
    )
    outliers = clf.fit_predict(y) < 0
    scores = -clf.decision_function(y)
    # line = numpy.repeat(0, n)

    yield dict(
        id=plot_prefix + "_inliers",
        type="scatter",
        text=names,
        hoverinfo="text+x+y",
        x=x[~outliers],
        y=scores[~outliers],
        line=dict(color="rgb(0,0,250)"),
        mode="markers",
        name="Inliers",
    )

    yield dict(
        id=plot_prefix + "outliers",
        type="scatter",
        text=names,
        hoverinfo="text+x+y",
        x=x[outliers],
        y=scores[outliers],
        line=dict(color="rgb(250,0,0)"),
        mode="markers",
        name="Outliers",
    )

    # yield dict(
    #     id=plot_prefix +"plot_line",
    #     type="scatter",
    #     hoverinfo="text+x+y",
    #     x=x.tolist(),
    #     y=line,
    #     line=dict(color="rgb(250,0,0)"),
    #     mode="lines",
    #     name="Criticial line",
    # )
