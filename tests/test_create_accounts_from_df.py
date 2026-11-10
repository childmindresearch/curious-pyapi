"""Tests for create_accounts_from_df."""

import logging
from unittest.mock import MagicMock

import httpx
import polars as pl

from curious_pyapi.api.curious import create_accounts_from_df


def _df():
    return pl.DataFrame(
        {
            "email": [
                "bruce.wayne@wayneenterprises.com",
                "clark.kent@dailyplanet.com",
                "diana.prince@themyscira.gov",
            ]
        }
    )


def test_dry_run_does_not_post():
    """Test dry run skips posting."""
    client = MagicMock()
    invite = MagicMock()
    invite.url = "https://forever.people/invitations/new-genesis16/respondent"
    client.invite_user.return_value = invite
    create_accounts_from_df(
        client, _df(), applet_id="new-genesis16", user_type="respondent", dry=True
    )
    invite.post.assert_not_called()
    assert client.invite_user.call_count == 3  # noqa: PLR2004


def test_limit_truncates():
    """Test limit truncates rows."""
    client = MagicMock()
    invite = MagicMock()
    invite.url = "https://forever.people/invitations/new-genesis16/respondent"
    invite.post.return_value.status_code = httpx.codes.OK
    client.invite_user.return_value = invite
    create_accounts_from_df(
        client, _df(), applet_id="new-genesis16", user_type="respondent", limit=2
    )
    assert invite.post.call_count == 2  # noqa: PLR2004


def test_verbose_logs(caplog):
    """Test verbose logging."""
    client = MagicMock()
    invite = MagicMock()
    invite.url = "https://forever.people/invitations/new-genesis16/respondent"
    resp = MagicMock()
    resp.status_code = httpx.codes.CREATED
    invite.post.return_value = resp
    client.invite_user.return_value = invite
    with caplog.at_level(logging.INFO):
        create_accounts_from_df(
            client,
            _df().head(1),
            applet_id="new-genesis16",
            user_type="respondent",
            verbose=True,
        )
    assert any("201" in r.message for r in caplog.records)
